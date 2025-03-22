from .models import *
from django.shortcuts import get_object_or_404
from management.ai_bases import get_gpt_output





def document_tech(git_repo_id) :
    file_paths = get_project_file_paths(git_repo_id)
    #print(file_paths)
    prompt = "Here are my files paths in my git_repo_id of my project : /n"
    for path in file_paths:
        prompt = prompt + str(path) + "/n"
    technos = Technology.objects.all()
    tech_text = "; ".join([f"{tech.name}" for tech in technos if tech.description])
    #print(tech_text)

    prompt = prompt + """I want you to analyse the structure and give me the used techno from this list [{0}]. 
    This is a crucial step in my process, please make sure to select the right technology according to the files paths, any mistake can create big damage.
    I want the answer to be the short name inside <techno></techno> balise, example: <techno>Django</techno>""".format(tech_text)
    gpt_output = get_gpt_output(prompt)
    #print(gpt_output)
    project_tech = gpt_output.split("<techno>")[-1].split("</techno>")[0]
    #print("TECH !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11")
    #print(project_tech)

    tech = get_object_or_404(Technology, name=project_tech)
    project = get_object_or_404(Project, git_repo_id=git_repo_id)
    try:
        project.technology = tech
        project.save()
    except:
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
