from django.shortcuts import render, redirect
from allauth.socialaccount.models import SocialToken
from django.http import HttpResponse, StreamingHttpResponse
from a_projects.ai_utils import document_tech
from django.shortcuts import get_object_or_404
from .document_components import document_components
import requests
import base64
from a_projects.models import Project, Status, File
from .models import AllowedFile
import re
import os
import json
from django.http import JsonResponse
import tiktoken



def get_github_token(user):
    try :
        profile = user.profile
        github_key = profile.github_access_key
        return github_key
    except :
        return None


def get_repo_branches(request, repo_name):
    token = get_github_token(request.user)
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
    url = f'https://api.github.com/repos/{request.user.username}/{repo_name}/branches'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        branches = response.json()
    else:
        branches = []

    print('BRANCHES :')
    print(branches)
    print(url)
    print(repo_name)
    return JsonResponse({'branches': branches})

def list_repos(request):
    try:
        token = get_github_token(request.user)
    except SocialToken.DoesNotExist:
        return redirect('error_page')  # Ou une autre page d'erreur, ou message indiquant de se reconnecter
    headers = {'Authorization': f'token {token}',
               "Accept": "application/vnd.github.v3+json"}
    #print(headers)
    repos = []
    page = 1
    while True:
        params = {'per_page': 100, 'page': page}
        resp = requests.get('https://api.github.com/user/repos', headers=headers, params=params)
        if resp.status_code != 200:
            # on arrête la boucle en cas d'erreur
            break

        page_repos = resp.json()
        if not page_repos:
            # plus de dépôts → fin de la pagination
            break

        repos.extend(page_repos)
        page += 1

    repos_status = 1 if repos else 0
    context = {'repos': repos, 'repos_status': repos_status}
    return render(request, 'git_auth/list_repos.html', context)


def view_repo_files(request, git_repo_id, repo_name):
    allowed_extensions = tuple(AllowedFile.objects.values_list('extension', flat=True))
    #print('view repo files')
    print('BRANCHES :')
    print(get_repo_branches(request, repo_name).content.decode("utf-8"))
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
                        file_content = fetch_file_content(content['path'])
                        files.append([content['path'], file_content])
                elif content['type'] == 'dir':
                    dirs.append(content['path'])
                    files.extend(build_paths(content['path']))
        return files
    paths_contents = build_paths()
    def build_file_tree(paths_contents):
        def add_to_tree(tree, parts, path=None , content=None):
            #print(path)
            #print(content)
            if len(parts) == 1 and parts[0].endswith(allowed_extensions) :  # Reached the file
                tree.append({
                    "name": parts[0],
                    "type": "file",
                    "path": path if path else "",
                    "content": content if content else ""
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

    def sort_tree(entries):
        # Trie d’abord les dossiers (type='folder'), puis les fichiers
        entries.sort(key=lambda item: (item['type'] != 'folder', item['name'].lower()))
        # Pour chaque dossier, on trie aussi ses enfants
        for item in entries:
            if item['type'] == 'folder':
                sort_tree(item['children'])
    sort_tree(file_tree['file_tree'])

    def add_token_counts(entries):
        encoding = tiktoken.get_encoding("cl100k_base")
        for entry in entries:
            if entry['type'] == 'file':
                tokens = encoding.encode(entry.get('content', ''))
                entry['token_count'] = len(tokens)
            else:
                add_token_counts(entry['children'])

    add_token_counts(file_tree['file_tree'])

    response_repo = requests.get(f'https://api.github.com/repos/{request.user.username}/{repo_name}', headers=headers)
    user = request.user
    name = repo_name
    git_repo_id = response_repo.json().get('id')
    git_repo_name = repo_name
    git_repo_url = f'https://github.com/{request.user.username}/{repo_name}'
    existing_project = Project.objects.filter(user=user, git_repo_id=git_repo_id).first()
    if existing_project:
        # Si un projet existe, le mettre à jour
        existing_project.name = name
        existing_project.git_repo_name = git_repo_name
        existing_project.git_repo_url = git_repo_url
        existing_project.save()  # Sauvegarder les changements
        project = existing_project
    else:
        status = Status.objects.get(code=0)
        # Sinon, créer un nouveau projet
        new_project = Project.objects.create(
            name=name,
            user=user,
            git_repo_id=git_repo_id,
            git_repo_name=git_repo_name,
            git_repo_url=git_repo_url,
            status = status
        )
        new_project.save()
        project = new_project
    return render(request, 'git_auth/view_repo_files.html', {'file_tree': file_tree, 'project':project})


def process_selected_files(request, git_repo_id, repo_name):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')

        selected_files = request.POST.getlist('file-checkbox')
        total = len(selected_files)
        deleted_files = request.POST.getlist('deleted_file')
        status = Status.objects.get(code=1)

        def stream():
            project = Project.objects.get(id=project_id)
            count = 0
            yield json.dumps({"count": count, "total": total}) + "\n"
            for file_str in selected_files:
                file_dict = eval(file_str)
                file_name = file_dict["name"]
                file_path = file_dict.get("path", "")
                file_content = file_dict.get("content", "")
                file_extension = os.path.splitext(file_name)[1].lower()
                file_type = re.search(r"(\.[^.]+)$", file_name)
                file_type = file_type.group(1) if file_type else None

                if file_extension and file_content.replace(" ", ""):
                    File.objects.update_or_create(
                        project=project,
                        name=file_name,
                        path=file_path,
                        extension=file_extension,
                        type=file_type,
                        defaults={"content": file_content}
                    )
                count += 1
                yield json.dumps({"count": count, "total": total}) + "\n"

            if deleted_files:
                for path in deleted_files:
                    File.objects.filter(project=project, path=path).delete()

            if project.technology is None:
                document_tech(git_repo_id)

            project = get_object_or_404(Project, git_repo_id=git_repo_id)
            #document_components(project, project.technology)
            for progress in document_components(project, project.technology):
                yield json.dumps(progress) + "\n"
            project.status = status
            project.save()
            profile = request.user.profile
            profile.default_project = project
            profile.save()

        return StreamingHttpResponse(stream(), content_type="text/plain")

    return HttpResponse("No files are selected")


def token_tutorial(request):
    """
    Affiche la page de tutoriel qui ne contient
    que des captures d’écran d’exemples de tokens.
    """
    return render(request, 'token_tutorial.html')



