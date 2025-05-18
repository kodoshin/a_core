from .models import *
from django.shortcuts import get_object_or_404
from management.ai_bases import get_gpt_output
import concurrent.futures



def predict_tech(git_repo_id):
    file_paths = get_project_file_paths(git_repo_id)
    prompt = 'Here are my files paths in my git_repo_id of my project : /n'
    for path in file_paths:
        prompt += f"{path}/n"
    technos = Technology.objects.all()
    tech_text = '; '.join([tech.name for tech in technos if tech.description])
    prompt += (
        f"I want you to analyse the structure and give me the used techno from this list [{tech_text}]. "
        "This is a crucial step in my process, please make sure to select the right technology "
        "according to the files paths, any mistake can create big damage. "
        "I want the answer to be the short name inside <techno></techno> balise, example: <techno>Django</techno>"
    )
    gpt_output = get_gpt_output(prompt)
    return gpt_output.split('<techno>')[-1].split('</techno>')[0]

def get_consensus_tech(git_repo_id):
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(predict_tech, git_repo_id) for _ in range(2)]
            results = [f.result() for f in futures]
        if len(results) == 2 and results[0] == results[1]:
            return results[0]


def document_tech(git_repo_id) :
    # Run two parallel predictions until they match
    project_tech_name = get_consensus_tech(git_repo_id)
    tech = get_object_or_404(Technology, name=project_tech_name)
    project = get_object_or_404(Project, git_repo_id=git_repo_id)
    try:
        project.technology = tech
        project.save()
    except Exception:
        pass

def get_project_file_paths(git_repo_id):
    # Récupérer le projet ayant le même git_repo_id
    project = get_object_or_404(Project, git_repo_id=git_repo_id)
    # Filtrer les fichiers liés à ce projet
    files = File.objects.filter(project=project)
    # Récupérer les chemins des fichiers
    file_paths = [file.path for file in files]
    # Retourner la liste des chemins en tant que JSON
    return file_paths
