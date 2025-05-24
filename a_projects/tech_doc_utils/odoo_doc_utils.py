import ast
import re
from django.db import transaction
from a_projects.models import Component, ComponentType


@transaction.atomic
def odoo_document_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente le contenu d'un fichier d'un projet Odoo et enregistre les composants trouvés
    dans la table Component.

    Les composants documentés sont :
        - Models
        - Views
        - Templates
        - URLs
        - Forms
        - Admin
        - Serializers
        - Middlewares
        - Static Files
        - Media Files
        - Management Commands
        - Signals

    :param file_content: Le contenu textuel du fichier.
    :param file_instance: L'instance du modèle File auquel rattacher les composants.
    :param file_name: Le nom (ou chemin) du fichier (utile pour détecter le type).
    """
    # Si le fichier est un fichier Python, on le parse avec ast
    if file_name.endswith('.py'):
        if file_name == 'settings.py':
            comp_type, _ = ComponentType.objects.get_or_create(name="Settings", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=file_name,
                description="Styling File",
                start_line=1,

                defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
            )
            if not created:
                component.content = file_content
                component.save()
        else :
            dj_document_python_file(file_content, file_instance, file_name, Technology)
    # Si c'est un template (fichier HTML)
    elif file_name.endswith('.html'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Templates", technology=Technology)

        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            description="Template File",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}  # Ce contenu est inséré si l'objet est créé
        )

        if not created:
            component.content = file_content
            component.save()

    elif file_name.endswith('.css'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Styling", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            description="Styling File",
            start_line=1,

            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()
    else:
        # Pour d'autres fichiers, on essaie de distinguer les fichiers statiques et médias
        if "static" in file_name.lower():
            comp_type_name = "Static Files"
        elif "media" in file_name.lower():
            comp_type_name = "Media Files"
        else:
            comp_type_name = "Other"
        comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            description=f"File of type : {comp_type_name}",
            start_line=1,

            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()


def dj_document_python_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier Python en extrayant les définitions de classes et de fonctions
    (ainsi que d'autres éléments spécifiques comme les urlpatterns dans urls.py)
    et enregistre ces éléments dans la table Component.

    :param file_content: Le contenu du fichier Python.
    :param file_instance: L'instance du modèle File.
    :param file_name: Le nom (ou chemin) du fichier.
    """
    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        # En cas d'erreur de parsing, on enregistre l'ensemble du fichier comme composant
        comp_type, _ = ComponentType.objects.get_or_create(name="Python", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,

            start_line=1,

            defaults={'content': file_content, 'end_line': len(file_content.splitlines()), 'description': "Python File is not parsable : " + str(e)}
        )
        if not created:
            component.content = file_content
            component.description = "Python file is not parsable : " + str(e)
            component.save()
        return

    # Si le fichier est urls.py, on cherche la variable urlpatterns
    if "urls.py" in file_name:
        pattern = r'urlpatterns\s*=\s*(\[[\s\S]*?\])'
        match = re.search(pattern, file_content, re.MULTILINE)
        if match:
            url_content = match.group(1)
            comp_type, _ = ComponentType.objects.get_or_create(name="URLs", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name="urlpatterns",
                description="URL patterns list",
                start_line=None,
                end_line=None,
                defaults={'content': url_content}
            )
            if not created:
                component.content = url_content
                component.save()

    # Parcours de l'AST pour extraire les définitions de classes et de fonctions
    for node in ast.walk(tree):
        # --- Traitement des classes ---
        if isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node) or ""
            start_line = node.lineno
            # À partir de Python 3.8, end_lineno est disponible sinon on le calcule sommairement
            end_line = getattr(node, "end_lineno", start_line)

            # Déduire le type de composant en fonction du nom du fichier et/ou des bases de la classe
            comp_type_name = None
            if "models.py" in file_name:
                comp_type_name = "Models"
            elif "views.py" in file_name:
                comp_type_name = "Views"
            elif "forms.py" in file_name:
                comp_type_name = "Forms"
            elif "admin.py" in file_name:
                comp_type_name = "Admin"
            elif "serializers.py" in file_name:
                comp_type_name = "Serializers"
            elif "signals.py" in file_name:
                comp_type_name = "Signals"
            elif "middleware" in file_name.lower():
                comp_type_name = "Middlewares"
            elif "management/commands" in file_name.replace("\\", "/"):
                comp_type_name = "Management Commands"
            else:
                # Sinon, on tente de déduire à partir des classes parentes
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Attribute):
                        base_name = base.attr
                    elif isinstance(base, ast.Name):
                        base_name = base.id
                    if base_name == "Model":
                        comp_type_name = "Models"
                        break
                    elif base_name in ["View", "TemplateView", "ListView", "DetailView"]:
                        comp_type_name = "Views"
                        break
                    elif base_name in ["Form", "ModelForm"]:
                        comp_type_name = "Forms"
                        break
                    elif base_name in ["Serializer", "ModelSerializer"]:
                        comp_type_name = "Serializers"
                        break
            if not comp_type_name:
                # En dernier recours, on classe la définition comme une classe Python générique
                comp_type_name = "Python Classes"

            comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)
            # Récupération du code source de la classe (si ast.unparse est disponible, Python ≥ 3.9)
            try:
                source = ast.unparse(node)
            except Exception:
                lines = file_content.splitlines()
                source = "\n".join(lines[start_line - 1: end_line])
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=node.name,

                defaults={'content': source, 'start_line': start_line, 'end_line': end_line, 'description': docstring}
            )
            if not created:
                component.content = source
                component.description = docstring
                component.save()
        # --- Traitement des fonctions ---
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Pour cet exemple, nous ne sauvegardons les fonctions que si le fichier est views.py
            if "views.py" in file_name:
                docstring = ast.get_docstring(node) or ""
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                comp_type, _ = ComponentType.objects.get_or_create(name="Views", technology=Technology)
                try:
                    source = ast.unparse(node)
                except Exception:
                    lines = file_content.splitlines()
                    source = "\n".join(lines[start_line - 1: end_line])
                component, created = Component.objects.get_or_create(
                    file=file_instance,
                    component_type=comp_type,
                    name=node.name,
                    defaults={'content': source, 'start_line': start_line, 'end_line': end_line, 'description': docstring}
                )
                if not created:
                    component.content = source
                    component.description = docstring
                    component.save()
            else:
                docstring = ast.get_docstring(node) or ""
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                comp_type, _ = ComponentType.objects.get_or_create(name="Functions", technology=Technology)
                try:
                    source = ast.unparse(node)
                except Exception:
                    lines = file_content.splitlines()
                    source = "\n".join(lines[start_line - 1: end_line])
                component, created = Component.objects.get_or_create(
                    file=file_instance,
                    component_type=comp_type,
                    name=node.name,
                    defaults={'content': source, 'start_line': start_line, 'end_line': end_line, 'description': docstring}
                )
                if not created:
                    component.content = source
                    component.description = docstring
                    component.save()
