import ast
import re
from django.db import transaction
from a_projects.models import Component, ComponentType

@transaction.atomic
def fl_document_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente le contenu d'un fichier d'un projet Flask et enregistre les composants trouvés
    dans la table Component.

    Les composants documentés sont :
        - Routes
        - Models
        - Templates
        - Static Files
        - Blueprints
        - Functions
        - Python Classes

    :param file_content: Le contenu textuel du fichier.
    :param file_instance: L'instance du modèle File auquel rattacher les composants.
    :param file_name: Le nom (ou chemin) du fichier (utile pour détecter le type).
    :param Technology: L'instance de la technologie (ici Flask).
    """
    # Si le fichier est un fichier Python, on le parse avec ast
    if file_name.endswith('.py'):
        fl_document_python_file(file_content, file_instance, file_name, Technology)
    # Si c'est un template (fichier HTML)
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
    # Pour les fichiers de style CSS
    elif file_name.endswith('.css'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Styling", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            description="Fichier CSS",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()
    else:
        # Pour d'autres fichiers, distinguer les fichiers statiques et médias
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


def fl_document_python_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier Python d'un projet Flask en extrayant :
        - Les définitions de classes (avec détection des modèles)
        - Les définitions de fonctions (en distinguant les routes via le décorateur @route)
        - Les blueprints (via des assignations à un appel à Blueprint)
    et enregistre ces éléments dans la table Component.

    :param file_content: Le contenu du fichier Python.
    :param file_instance: L'instance du modèle File.
    :param file_name: Le nom (ou chemin) du fichier.
    :param Technology: L'instance de la technologie (ici Flask).
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

    # Recherche des blueprints (assignations qui appellent Blueprint)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                call_node = node.value
                func = call_node.func
                blueprint_called = False
                if isinstance(func, ast.Name) and func.id == "Blueprint":
                    blueprint_called = True
                elif isinstance(func, ast.Attribute) and func.attr == "Blueprint":
                    blueprint_called = True
                if blueprint_called:
                    # On récupère le nom du blueprint depuis l'assignation
                    blueprint_name = None
                    if node.targets and isinstance(node.targets[0], ast.Name):
                        blueprint_name = node.targets[0].id
                    else:
                        blueprint_name = "Unnamed Blueprint"
                    comp_type, _ = ComponentType.objects.get_or_create(name="Blueprints", technology=Technology)
                    try:
                        source = ast.unparse(node)
                    except Exception:
                        lines = file_content.splitlines()
                        source = "\n".join(lines[node.lineno - 1: node.lineno])
                    component, created = Component.objects.get_or_create(
                        file=file_instance,
                        component_type=comp_type,
                        name=blueprint_name,
                        defaults={'content': source, 'start_line': node.lineno, 'end_line': node.lineno}
                    )
                    if not created:
                        component.content = source
                        component.save()

    # Parcours de l'AST pour extraire classes et fonctions
    for node in ast.walk(tree):
        # --- Traitement des classes ---
        if isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node) or ""
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)

            # Déduire le type de composant : si le fichier s'appelle models.py ou si la classe hérite de Model
            comp_type_name = None
            if "models.py" in file_name:
                comp_type_name = "Models"
            else:
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Attribute):
                        base_name = base.attr
                    elif isinstance(base, ast.Name):
                        base_name = base.id
                    if base_name in ["Model", "db.Model"]:
                        comp_type_name = "Models"
                        break
            if not comp_type_name:
                comp_type_name = "Python Classes"

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
                defaults={'content': source, 'start_line': start_line, 'end_line': end_line, 'description': docstring}
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

            # Vérifier si la fonction possède un décorateur route (@app.route ou @blueprint.route)
            is_route = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Attribute) and func.attr == "route":
                        is_route = True
                        break
            comp_type_name = "Routes" if is_route else "Functions"
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
                defaults={'content': source, 'start_line': start_line, 'end_line': end_line, 'description': docstring}
            )
            if not created:
                component.content = source
                component.description = docstring
                component.save()
