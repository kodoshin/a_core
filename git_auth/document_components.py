from a_projects.models import File, Component
from a_projects.tech_doc_utils.django_doc_utils import dj_document_file
from a_projects.tech_doc_utils.python_doc_utils import py_document_python_file
from a_projects.tech_doc_utils.react_doc_utils import react_document_file
from a_projects.tech_doc_utils.nextjs_doc_utils import nextjs_document_file
from a_projects.tech_doc_utils.flask_doc_utils import fl_document_file
from a_projects.tech_doc_utils.fastapi_doc_utils import fa_document_file
from a_projects.tech_doc_utils.r_doc_utils import r_document_r_file
from a_projects.tech_doc_utils.nodejs_doc_utils import node_document_file
from a_projects.tech_doc_utils.springboot_doc_utils import springboot_document_file
from a_projects.tech_doc_utils.java_doc_utils import java_document_java_file
from a_projects.tech_doc_utils.odoo_doc_utils import odoo_document_file
from a_projects.tech_doc_utils.cs_doc_utils import get_csharp_docstring


def document_components (project, technology):
    files = File.objects.filter(project=project)
    for file in files :
        Component.objects.filter(file=file).delete()
        if technology.name == 'Django':
            dj_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Odoo' :
            odoo_document_file(file.content, file, file.name, technology)
        elif technology.name == 'Python' and file.name.endswith('.py') :
            py_document_python_file(file.content, file, file.name, technology)
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
        elif technology.name == 'Springboot':
            springboot_document_file(file.content, file, file.name, technology)
        elif technology.name == 'R':
            r_document_r_file(file.content, file, file.name, technology)
        elif technology.name == 'Java':
            java_document_java_file(file.content, file, file.name, technology)


