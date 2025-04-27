import base64
import requests
from git_auth.views import get_github_token
from .models import File
from git_auth.models import AllowedFile

def update_project_files(project, owner, repo_name):
    token = get_github_token(project.user)
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    allowed_exts = tuple(AllowedFile.objects.values_list('extension', flat=True))
    remote_paths = []

    def fetch_directory(path=''):
        url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{path}'
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.status_code == 200 else []

    def fetch_file_content(path):
        url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{path}'
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return base64.b64decode(data['content']).decode('utf-8')
        return ''

    def traverse(path=''):
        for item in fetch_directory(path):
            if item['type'] == 'file' and item['path'].endswith(allowed_exts):
                content = fetch_file_content(item['path'])
                remote_paths.append(item['path'])
                File.objects.update_or_create(
                    project=project,
                    path=item['path'],
                    defaults={
                        'name': item['name'],
                        'extension': item['name'].split('.')[-1],
                        'content': content
                    }
                )
            elif item['type'] == 'dir':
                traverse(item['path'])

    traverse()
    # Supprime les fichiers supprimés sur GitHub
    File.objects.filter(project=project).exclude(path__in=remote_paths).delete()