import ast
from django.db import transaction
from a_projects.models import Component, ComponentType


@transaction.atomic
def py_document_python_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier Python normal en extrayant les définitions de classes et de fonctions.

    Pour chaque classe ou fonction détectée, un composant est créé dans la base de données,
    avec les informations suivantes :
      - name: le nom de la classe ou de la fonction,
      - content: le code source extrait (utilisation de ast.unparse si disponible),
      - description: le docstring associé (s'il existe),
      - start_line et end_line : le numéro de la première et de la dernière ligne.

    Si aucune définition n'est détectée, le fichier entier est enregistré comme composant de type "Python File".

    :param file_content: Contenu textuel du fichier Python.
    :param file_instance: Instance du modèle File auquel rattacher le composant.
    :param file_name: Nom (ou chemin) du fichier.
    """
    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        # En cas d'erreur de parsing, on enregistre le fichier entier comme composant "Python File"
        comp_type, _ = ComponentType.objects.get_or_create(name="Python File", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,

            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines()), 'description':"Python file is not parsable : " + str(e)}
        )
        if not created:
            component.content = file_content
            component.description = "Python file is not parsable : " + str(e)
            component.save()
        return

    # Variable permettant de savoir si on a trouvé au moins une définition de classe ou de fonction
    extracted = False

    # Parcours de l'arbre AST pour extraire les définitions de classes et de fonctions
    for node in ast.walk(tree):
        # --- Traitement des classes ---
        if isinstance(node, ast.ClassDef):
            extracted = True
            docstring = ast.get_docstring(node) or ""
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)
            comp_type, _ = ComponentType.objects.get_or_create(name="Python Classes", technology=Technology)
            try:
                source = ast.unparse(node)  # Disponible à partir de Python 3.9
            except Exception:
                # En cas d'échec, on extrait le code à partir des lignes du fichier
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
            extracted = True
            docstring = ast.get_docstring(node) or ""
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)
            comp_type, _ = ComponentType.objects.get_or_create(name="Python Functions", technology=Technology)
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

    # Si aucune définition de classe ou de fonction n'est détectée, enregistre le fichier entier
    if not extracted:
        comp_type, _ = ComponentType.objects.get_or_create(name="Python File", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            content=file_content,

            defaults={'content': file_content, 'end_line': len(file_content.splitlines()), 'description':"No Classes or Functions detected in this file." }
        )
        if not created:
            component.content = file_content
            component.description = "No Classes or Functions detected in this file."
            component.save()
