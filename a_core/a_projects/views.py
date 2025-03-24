from django.shortcuts import render, get_object_or_404, redirect
from .models import Project, Component, File
from git_auth.views import get_github_token
from a_users.models import Profile
import requests
import base64
from git_auth.models import AllowedFile
from django.contrib import messages
from urllib.parse import urlparse
from django.conf import settings

import re





def view_documentation(request, project_id):
    project = Project.objects.filter(id=project_id, user=request.user).first()
    project_files = File.objects.filter(project_id=project_id)
    project_components = Component.objects.filter(file_id__project_id=project_id)

    context = {
        'project_id' : project_id,
        'project': project,
        'project_components': project_components,
        'project_files': project_files,
    }

    return render(request, 'a_projects/view_documentation.html', context)


def sync_with_github(request, project_id):
    print('creating webhook')
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
    webhook_url = getattr(settings, "GITHUB_WEBHOOK_URL", "https://yourdomain.com/github/webhook")
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
    print('calling webhook request')
    response = requests.post(api_url, json=payload, headers=headers)
    print(response.text)
    if response.status_code in (200, 201):
        messages.success(request, "Webhook created successfully.")
    else:
        messages.error(request, f"Failed to create webhook: {response.text}")

    return redirect('view_documentation', project_id=project_id)



def has_equivalent(user, git_repo_id, path,file_content):
    project = Project.objects.filter(git_repo_id=git_repo_id, user=user).first()
    file = File.objects.filter(project=project, path=path).first()
    if file and file.content == file_content:
        return True
    else:
        return False


def view_modified_repo_files(request, git_repo_id, repo_name, project_id):
    #print('view repo files')
    allowed_extensions = tuple(AllowedFile.objects.values_list('extension', flat=True))
    token = get_github_token(request.user)
    headers = {'Authorization': f'token {token}',
               "Accept": "application/vnd.github.v3+json"}
    def fetch_directory_contents(path=''):
        url = f'https://api.github.com/repos/{request.user.username}/{repo_name}/contents/{path}'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    def fetch_file_content(path):
        url = f'https://api.github.com/repos/{request.user.username}/{repo_name}/contents/{path}'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            content_data = response.json()
            # Le contenu du fichier est encodé en base64, il faut donc le décoder
            file_content = base64.b64decode(content_data['content']).decode('utf-8')
            return file_content
        return None
    def build_paths(path=''):
        contents = fetch_directory_contents(path)
        dirs = []
        files = []
        #rendre les extensions autorisées dynamique à partir de la console
        for content in contents:
            if not(('__pycache__' in content['path']) or ('.idea' in content['path'])):
                if content['type'] == 'file':
                    if content['path'].endswith(allowed_extensions):
                        ##########################################################################################################################################################################################################
                        file_content = fetch_file_content(content['path'])

                        if has_equivalent(request.user, git_repo_id, content['path'],file_content) or file_content.replace(" ","") == "":
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
        project = Project.objects.filter(git_repo_id=git_repo_id, user=request.user).first()
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
    existing_project = Project.objects.filter(user=user, git_repo_id=git_repo_id).first()

    # mettre le projet à jour
    existing_project.name = name
    existing_project.git_repo_name = git_repo_name
    existing_project.git_repo_url = git_repo_url
    existing_project.save()  # Sauvegarder les changements
    project = existing_project

    return render(request, 'a_projects/update_repo_files.html', {'file_tree': file_tree, 'deleted_files':deleted_files, 'project':project})


def delete_project(request, project_id):
    profile = Profile.objects.get(user=request.user)
    profile.default_project = None
    profile.save()
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return redirect('/')
