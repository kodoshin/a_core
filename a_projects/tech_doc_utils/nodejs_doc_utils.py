import re
from django.db import transaction
from a_projects.models import Component, ComponentType

@transaction.atomic
def node_document_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente le contenu d'un fichier d'un projet Node.js et enregistre les composants trouvés
    dans la table Component.

    Les composants documentés peuvent être :
        - Models (ex : Mongoose models)
        - Controllers
        - Routes
        - Middlewares
        - Views (templates)
        - Static Files
        - Functions / JavaScript Classes
        - Other

    :param file_content: Le contenu textuel du fichier.
    :param file_instance: L'instance du modèle File auquel rattacher les composants.
    :param file_name: Le nom (ou chemin) du fichier (utile pour détecter le type).
    :param Technology: L'instance représentant la technologie (ici Node.js).
    """
    #print('DOCUMENTING NODE JS')
    if file_name.endswith(('.js', '.ts')):
        node_document_js_file(file_content, file_instance, file_name, Technology)
    elif file_name.endswith('.html'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Views", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            description="Template HTML",
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
            description="Fichier CSS",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()
    else:
        # Pour d'autres types de fichiers (ex: images, assets divers)
        if "static" in file_name.lower():
            comp_type_name = "Static Files"
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


def node_document_js_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier JavaScript/TypeScript d'un projet Node.js en extrayant
    les définitions de classes, fonctions et routes, puis enregistre ces éléments
    dans la table Component.

    :param file_content: Le contenu du fichier JavaScript/TypeScript.
    :param file_instance: L'instance du modèle File.
    :param file_name: Le nom (ou chemin) du fichier.
    :param Technology: L'instance représentant la technologie (ici Node.js).
    """
    lines = file_content.splitlines()

    # --- Extraction des routes ---
    if "routes" in file_name.lower():
        route_pattern = r'(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']'
        matches = re.finditer(route_pattern, file_content)
        comp_type, _ = ComponentType.objects.get_or_create(name="Routes", technology=Technology)
        for match in matches:
            method = match.group(1).upper()
            route = match.group(2)
            start_line = file_content[:match.start()].count('\n') + 1
            component_name = f"{method} {route}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=component_name,
                defaults={'content': match.group(0),
                          'start_line': start_line,
                          'end_line': start_line,
                          'description': f"Route {method} pour {route}"}
            )
            if not created:
                component.content = match.group(0)
                component.save()

    # --- Extraction des classes ---
    class_pattern = r'class\s+(\w+)\s*(?:extends\s+\w+)?\s*{'
    for match in re.finditer(class_pattern, file_content):
        class_name = match.group(1)
        start_line = file_content[:match.start()].count('\n') + 1
        # Ici, pour simplifier, on récupère quelques lignes après le début de la classe
        source = "\n".join(lines[start_line - 1 : start_line + 9])
        # Déduction du type en fonction du chemin
        if "models" in file_name.lower():
            comp_type_name = "Models"
        elif "controller" in file_name.lower():
            comp_type_name = "Controllers"
        elif "middleware" in file_name.lower():
            comp_type_name = "Middlewares"
        else:
            comp_type_name = "JavaScript Classes"
        comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=class_name,
            defaults={'content': source,
                      'start_line': start_line,
                      'end_line': start_line + 9,
                      'description': f"Classe {class_name}"}
        )
        if not created:
            component.content = source
            component.save()

    # --- Extraction des fonctions ---
    function_pattern = r'function\s+(\w+)\s*\('
    for match in re.finditer(function_pattern, file_content):
        func_name = match.group(1)
        start_line = file_content[:match.start()].count('\n') + 1
        source = "\n".join(lines[start_line - 1 : start_line + 9])
        # Choix du type en fonction du contexte (ex : controllers ou fonctions génériques)
        if "controller" in file_name.lower():
            comp_type_name = "Controllers"
        else:
            comp_type_name = "Functions"
        comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=func_name,
            defaults={'content': source,
                      'start_line': start_line,
                      'end_line': start_line + 9,
                      'description': f"Fonction {func_name}"}
        )
        if not created:
            component.content = source
            component.save()
