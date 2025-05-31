from a_projects.models import File, Component
from a_projects.tech_doc_utils.django_doc_utils import dj_document_file
from a_projects.tech_doc_utils.python_doc_utils import python_document_file
from a_projects.tech_doc_utils.react_doc_utils import react_document_file
from a_projects.tech_doc_utils.nextjs_doc_utils import nextjs_document_file
from a_projects.tech_doc_utils.flask_doc_utils import fl_document_file
from a_projects.tech_doc_utils.fastapi_doc_utils import fa_document_file
from a_projects.tech_doc_utils.r_doc_utils import r_document_file
from a_projects.tech_doc_utils.nodejs_doc_utils import node_document_file
from a_projects.tech_doc_utils.springboot_doc_utils import springboot_document_file
from a_projects.tech_doc_utils.java_doc_utils import java_document_file
from a_projects.tech_doc_utils.odoo_doc_utils import odoo_document_file
from a_projects.tech_doc_utils.angular_doc_utils import angular_document_file
from a_projects.tech_doc_utils.remix_doc_utils import remix_document_file
from a_projects.tech_doc_utils.vuejs_doc_utils import vue_document_file
from a_projects.tech_doc_utils.sveltekit_doc_utils import sveltekit_document_file
from a_projects.tech_doc_utils.cs_doc_utils import get_csharp_docstring


def document_components (project, technology):
    print('documenting project components')
    files = File.objects.filter(project=project)
    for file in files :
        print(file.name)
        Component.objects.filter(file=file).delete()
        if technology.name == 'Django':
            dj_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Odoo' :
            odoo_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Python' :
            python_document_file(file.content, file, file.name, technology)
        elif technology.name == 'React':
            react_document_file(file.content, file, technology)
        elif technology.name == 'Next JS':
            nextjs_document_file(file.content, file, technology)
        elif technology.name == 'Node JS':
            node_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Flask':
            fl_document_file(file.content, file, file.name, technology)
        elif technology.name == 'FastAPI':
            fa_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Spring Boot':
            springboot_document_file(file.content, file, file.name, technology)
        elif technology.name == 'R':
            r_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Java':
            java_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Angular':
            angular_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Remix':
            remix_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Vue JS':
            vue_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Svelte':
            sveltekit_document_file(file.content, file, file.name, technology)

