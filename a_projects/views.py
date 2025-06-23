from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from .models import Project, Component, File
from git_auth.views import get_github_token
from a_users.models import Profile
import requests
import base64
from git_auth.models import AllowedFile
from django.contrib import messages
from urllib.parse import urlparse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
import tiktoken





def view_documentation(request, project_id):
    project = Project.objects.filter(id=project_id, user=request.user).first()
    if project :
        project_files = File.objects.filter(project_id=project_id)
        project_components = Component.objects.filter(file_id__project_id=project_id)

        token_expired = False
        token = get_github_token(request.user)
        if not token:
            token_expired = True
        else:
            try:
                gh_response = requests.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10,
                )
                if gh_response.status_code == 401:
                    token_expired = True
            except requests.RequestException:
                token_expired = True

        context = {
            'project_id' : project_id,
            'project': project,
            'project_components': project_components,
            'project_files': project_files,
            'token_expired': token_expired,
        }
        return render(request, 'a_projects/view_documentation.html', context)
    else :
        return HttpResponse("Project not found")


def view_components(request, project_id):
    project = Project.objects.filter(id=project_id, user=request.user).first()
    if project :
        project_files = File.objects.filter(project_id=project_id)
        project_components = Component.objects.filter(file_id__project_id=project_id)
        context = {
            'project_id' : project_id,
            'project': project,
            'project_components': project_components,
            'project_files': project_files,
        }
        return render(request, 'a_projects/view_components.html', context)
    else :
        return HttpResponse("Project not found")

@csrf_exempt
def github_webhook(request):
    print('starting webhook update')
    if request.method != 'POST':
        return HttpResponse(status=405)
    event = request.META.get('HTTP_X_GITHUB_EVENT', '')
    if event == 'ping':
        return HttpResponse('pong', status=200)
    if event != 'push':
        return HttpResponse(status=204)
    payload = json.loads(request.body.decode('utf-8'))
    repo_data = payload.get('repository', {})
    repo_id = repo_data.get('id')

    ref = payload.get('ref', '')
    branch = ref.split('/')[-1] if ref else 'main'
    print('BRANCH :::', branch)

    owner = repo_data.get('owner', {}).get('login')
    name = repo_data.get('name')
    try:
        project = Project.objects.get(git_repo_id=repo_id, git_branch = branch )
    except Project.DoesNotExist:
        return HttpResponse(status=404)
    except Project.MultipleObjectsReturned:
        # Sécurité : on prend le premier correspondant
        project = Project.objects.filter(git_repo_id=repo_id, git_branch=branch).first()

    user = project.user
    token = get_github_token(user)
    if not token:
        return HttpResponse('No GitHub token', status=403)
    allowed_exts = tuple(AllowedFile.objects.values_list('extension', flat=True))
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    current_files = {}
    def fetch_dir(path=''):
        url = f'https://api.github.com/repos/{owner}/{name}/contents/{path}?ref={branch}'
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.status_code == 200 else []
    def recurse(path=''):
        for item in fetch_dir(path):
            if item.get('type') == 'file' and any(item.get('path','').endswith(ext) for ext in allowed_exts):
                file_resp = requests.get(item.get('url'), headers=headers).json()
                content = base64.b64decode(file_resp.get('content','')).decode('utf-8')
                current_files[item['path']] = content
            elif item.get('type') == 'dir':
                recurse(item['path'])
    recurse()
    # Create or update files
    for path, content in current_files.items():
        filename = path.split('/')[-1]
        ext = filename.split('.')[-1] if '.' in filename else ''
        File.objects.update_or_create(
            project=project,
            path=path,
            defaults={'name': filename, 'extension': ext, 'content': content}
        )
    # Delete removed files
    existing_paths = set(File.objects.filter(project=project).values_list('path', flat=True))
    removed = existing_paths - set(current_files.keys())
    if removed:
        File.objects.filter(project=project, path__in=removed).delete()
    project.github_sync = True
    project.save()
    return HttpResponse('OK', status=200)


def sync_with_github(request, project_id):
    print('creating webhook')
    if not request.user.profile.is_paid_user:
        messages.error(request, "This feature is reserved for premium plans..")
        return redirect('view_documentation', project_id=project_id)
    project = get_object_or_404(Project, id=project_id, user=request.user)
    token = get_github_token(request.user)
    if not token:
        messages.error(request, "GitHub access token not found. Please connect your GitHub account.")
        return redirect('view_documentation', project_id=project_id)

    parsed = urlparse(project.git_repo_url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) < 2:
        messages.error(request, "Invalid GitHub repository URL.")
        return redirect('view_documentation', project_id=project_id)
    owner = path_parts[0]
    repo = path_parts[1].replace('.git', '')

    api_url = f"https://api.github.com/repos/{owner}/{repo}/hooks"
    webhook_url = getattr(settings, "GITHUB_WEBHOOK_URL", "https://acore-production.up.railway.app/projects/github/webhook/")
    #webhook_url = request.build_absolute_uri(reverse('github_webhook'))
    print('webhook url:')
    print(webhook_url)
    payload = {
        "name": "web",
        "active": True,
        "events": ["push"],
        "config": {
            "url": webhook_url,
            "content_type": "json"
        }
    }
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    #print('calling webhook request')
    response = requests.post(api_url, json=payload, headers=headers)
    #print(response.text)
    if response.status_code in (200, 201):
        project.github_sync = True
        project.save()
        messages.success(request, "Webhook created successfully.")
    else:
        messages.error(request, f"Failed to create webhook: {response.text}")

    return redirect('view_documentation', project_id=project_id)


def delete_github_sync(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    token = get_github_token(request.user)
    if not token:
        messages.error(request, 'GitHub access token not found. Please connect your GitHub account.')
        return redirect('view_documentation', project_id=project_id)

    parsed = urlparse(project.git_repo_url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) < 2:
        messages.error(request, 'Invalid GitHub repository URL.')
        return redirect('view_documentation', project_id=project_id)

    owner = path_parts[0]
    repo = path_parts[1].replace('.git', '')
    webhook_url = getattr(settings, 'GITHUB_WEBHOOK_URL', 'https://acore-production.up.railway.app/github/webhook')
    api_url = f'https://api.github.com/repos/{owner}/{repo}/hooks'
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

    # Retrieve existing webhooks for the repository
    response = requests.get(api_url, headers=headers)
    print(response.text)
    if response.status_code != 200:
        messages.error(request, f'Failed to retrieve webhooks: {response.text}')
        return redirect('view_documentation', project_id=project_id)

    hooks = response.json()
    hook_id = None
    for hook in hooks:
        if hook.get("config", {}).get("url") == webhook_url:
            hook_id = hook.get("id")
            break

    if not hook_id:
        messages.error(request, 'Webhook not found.')
        return redirect('view_documentation', project_id=project_id)

    # Delete the identified webhook
    delete_url = f'https://api.github.com/repos/{owner}/{repo}/hooks/{hook_id}'
    delete_response = requests.delete(delete_url, headers=headers)
    if delete_response.status_code == 204:
        project.github_sync = False
        project.save()
        messages.success(request, 'Webhook deleted successfully.')
    else:
        messages.error(request, f'Failed to delete webhook: {delete_response.text}')

    return redirect('view_documentation', project_id=project_id)


def has_equivalent(project_id, path,file_content):
    project = Project.objects.get(id=project_id)
    file = File.objects.filter(project=project, path=path).first()
    if file and file.content == file_content:
        return True
    else:
        return False


def view_modified_repo_files(request, git_repo_id, repo_name, project_id):
    project = Project.objects.get(id=project_id)
    branch = project.git_branch
    if branch == 'main' :
        branch = ''
    #print('BRANCH :', branch)
    allowed_extensions = tuple(AllowedFile.objects.values_list('extension', flat=True))
    token = get_github_token(request.user)
    headers = {'Authorization': f'token {token}',
               "Accept": "application/vnd.github.v3+json"}

    def build_url(path=''):
        base = f'https://api.github.com/repos/{request.user.username}/{repo_name}/contents/{path}'
        return f'{base}?ref={branch}' if branch else base

    def fetch_directory_contents(path=''):
        response = requests.get(build_url(path), headers=headers)
        if response.status_code == 200:
            return response.json()
        return []

    def fetch_file_content(path):
        response = requests.get(build_url(path), headers=headers)
        if response.status_code == 200:
            content_data = response.json()
            file_content = base64.b64decode(content_data['content']).decode('utf-8')
            return file_content
        return None
    def build_paths(path=''):
        contents = fetch_directory_contents(path)
        print('CONTENTS:')
        print(contents)
        dirs = []
        files = []
        #rendre les extensions autorisées dynamique à partir de la console
        for content in contents:
            if not(('__pycache__' in content['path']) or ('.idea' in content['path'])):
                if content['type'] == 'file':
                    if content['path'].endswith(allowed_extensions):
                        ##########################################################################################################################################################################################################
                        file_content = fetch_file_content(content['path'])

                        if has_equivalent(project_id, content['path'],file_content) or file_content.replace(" ","") == "":
                            pass
                        else:
                            files.append([content['path'], file_content])
                elif content['type'] == 'dir':
                    dirs.append(content['path'])
                    files.extend(build_paths(content['path']))
        return files
    paths_contents = build_paths()
    def build_file_tree(paths_contents):
        def add_to_tree(tree, parts, path=None, content=None):
            if len(parts) == 1 and parts[0].endswith(allowed_extensions) :  # Reached the file
                tree.append({
                    "name": parts[0],
                    "type": "file",
                    "path": path if path else "",
                    "content":  content if content else ""
                })
            else:  # Still in folders
                folder_name = parts[0]
                # Find if folder already exists in tree
                for item in tree:
                    if item['type'] == 'folder' and item['name'] == folder_name:
                        add_to_tree(item['children'], parts[1:], path, content)
                        break
                else:
                    new_folder = {
                        "name": folder_name,
                        "type": "folder",
                        "children": []
                    }
                    tree.append(new_folder)
                    add_to_tree(new_folder['children'], parts[1:], path, content)
                    pass
        file_tree = []
        for path, content in paths_contents:
            parts = path.split('/')
            add_to_tree(file_tree, parts, path, content)
        return {
            "repo_name": repo_name,
            "git_repo_id":git_repo_id,
            "file_tree": file_tree
        }
    file_tree = build_file_tree(paths_contents)
    #print(file_tree)
    ### This section is to create a list of the deleted files

    def sort_tree(entries):
        # Trie d’abord les dossiers (type='folder'), puis les fichiers
        entries.sort(key=lambda item: (item['type'] != 'folder', item['name'].lower()))
        # Pour chaque dossier, on trie aussi ses enfants
        for item in entries:
            if item['type'] == 'folder':
                sort_tree(item['children'])
    sort_tree(file_tree['file_tree'])

    # Add token counts for each file node
    def add_token_counts(entries):
        encoding = tiktoken.get_encoding("cl100k_base")
        for entry in entries:
            if entry['type'] == 'file':
                tokens = encoding.encode(entry.get('content', ''))
                entry['token_count'] = len(tokens)
            else:
                add_token_counts(entry['children'])

    add_token_counts(file_tree['file_tree'])

    def build_all_paths(path=''):
        contents = fetch_directory_contents(path)
        files = []
        #rendre les extensions autorisées dynamique à partir de la console
        for content in contents:
            #print(content)
            if content['type'] == 'file':
                files.append(content['path'])
            elif content['type'] == 'dir':
                files.extend(build_all_paths(content['path']))
        return files


    def build_deleted_files(path=''):
        files = build_all_paths()
        #print('FILES PATHS :')
        #print(files)
        deleted_files = []
        project = Project.objects.get(id=project_id)
        project_files = File.objects.filter(project=project)
        for file in project_files:
            if file.path in files:
                pass
            else :
                deleted_files.append(file.path)
        return deleted_files
    deleted_files = build_deleted_files()
    #print('Deleted Files :')
    #print(deleted_files)


    response_repo = requests.get(f'https://api.github.com/repos/{request.user.username}/{repo_name}', headers=headers)
    user = request.user
    name = repo_name
    git_repo_id = response_repo.json().get('id')
    git_repo_name = repo_name
    git_repo_url = f'https://github.com/{request.user.username}/{repo_name}'
    existing_project = Project.objects.get(id=project_id)

    # mettre le projet à jour
    existing_project.name = name
    existing_project.git_repo_name = git_repo_name
    existing_project.git_repo_url = git_repo_url
    existing_project.save()  # Sauvegarder les changements
    project = existing_project

    return render(request, 'a_projects/update_repo_files.html', {'file_tree': file_tree, 'deleted_files':deleted_files, 'project':project, 'selected_branch': branch})


def delete_project(request, project_id) :
    delete_github_sync(request, project_id)
    profile = Profile.objects.get(user=request.user)
    #try:
    #    profile.default_project = Project.objects.get(user=request.user)
    #except Project.DoesNotExist:
    profile.default_project = None
    profile.save()
    #print('Profile Project')
    #print(profile.default_project.name)
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return redirect('/')
