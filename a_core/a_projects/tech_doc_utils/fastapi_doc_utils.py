import ast
import re
from django.db import transaction
from a_projects.models import Component, ComponentType


@transaction.atomic
def fa_document_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente le contenu d'un fichier d'un projet FastAPI et enregistre les composants trouvés
    dans la table Component.

    Les composants documentés peuvent inclure :
        - Endpoints
        - Pydantic Models
        - Templates
        - Static Files
        - Media Files
        - Autres fichiers

    :param file_content: Le contenu textuel du fichier.
    :param file_instance: L'instance du modèle File auquel rattacher les composants.
    :param file_name: Le nom (ou chemin) du fichier (utile pour détecter le type).
    :param Technology: L'instance de la technologie à associer.
    """
    if file_name.endswith('.py'):
        fa_document_python_file(file_content, file_instance, file_name, Technology)
    elif file_name.endswith('.html'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Templates", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            description="Template File",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
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
            description="Fichier de styling",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()
    else:
        # Pour d'autres types de fichiers, on différencie les fichiers statiques et médias
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
            description=f"Fichier de type {comp_type_name}",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()


def fa_document_python_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier Python d'un projet FastAPI en extrayant les définitions de classes et de fonctions.
    Il identifie notamment :
        - Les endpoints (fonctions décorées avec @app.get, @app.post, …)
        - Les Pydantic Models (classes héritant de BaseModel)
        - Les autres classes et fonctions

    :param file_content: Le contenu du fichier Python.
    :param file_instance: L'instance du modèle File.
    :param file_name: Le nom (ou chemin) du fichier.
    :param Technology: L'instance de la technologie à associer.
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
            defaults={
                'content': file_content,
                'end_line': len(file_content.splitlines()),
                'description': "Fichier Python non parsable : " + str(e)
            }
        )
        if not created:
            component.content = file_content
            component.description = "Fichier Python non parsable : " + str(e)
            component.save()
        return

    # Optionnel : Si le fichier est main.py, détecter l'instance de FastAPI
    if "main.py" in file_name:
        pattern = r'app\s*=\s*FastAPI\('
        match = re.search(pattern, file_content)
        if match:
            app_content = match.group(0)
            comp_type, _ = ComponentType.objects.get_or_create(name="FastAPI App", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name="app",
                description="Instance de l'application FastAPI",
                start_line=None,
                end_line=None,
                defaults={'content': app_content}
            )
            if not created:
                component.content = app_content
                component.save()

    # Parcours de l'AST pour extraire les définitions de classes et de fonctions
    for node in ast.walk(tree):
        # --- Traitement des classes ---
        if isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node) or ""
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)

            # Si la classe hérite de BaseModel, on la considère comme un Pydantic Model
            if any((isinstance(base, ast.Name) and base.id == "BaseModel") or
                   (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
                   for base in node.bases):
                comp_type_name = "Pydantic Models"
            else:
                comp_type_name = "FastAPI Classes"

            comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)
            try:
                source = ast.unparse(node)
            except Exception:
                lines = file_content.splitlines()
                source = "\n".join(lines[start_line - 1: end_line])
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=node.name,
                defaults={
                    'content': source,
                    'start_line': start_line,
                    'end_line': end_line,
                    'description': docstring
                }
            )
            if not created:
                component.content = source
                component.description = docstring
                component.save()

        # --- Traitement des fonctions ---
        elif isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node) or ""
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)

            # Vérifier si la fonction est un endpoint FastAPI en examinant ses décorateurs
            is_endpoint = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute) and decorator.func.attr.lower() in ["get", "post", "put", "patch", "delete"]:
                        is_endpoint = True
                        break

            comp_type_name = "Endpoints" if is_endpoint else "Functions"
            comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)
            try:
                source = ast.unparse(node)
            except Exception:
                lines = file_content.splitlines()
                source = "\n".join(lines[start_line - 1: end_line])
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=node.name,
                defaults={
                    'content': source,
                    'start_line': start_line,
                    'end_line': end_line,
                    'description': docstring
                }
            )
            if not created:
                component.content = source
                component.description = docstring
                component.save()
