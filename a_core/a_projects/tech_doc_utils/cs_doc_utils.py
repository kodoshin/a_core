import re
from django.db import transaction
from a_projects.models import Component, ComponentType


def get_csharp_docstring(lines, def_line_index):
    """
    Extrait les commentaires XML (///) contigus situés juste au-dessus de la ligne de définition.
    :param lines: Liste des lignes du fichier.
    :param def_line_index: Index (0-based) de la ligne de définition.
    :return: Chaîne de caractères formée des commentaires extraits.
    """
    doc_lines = []
    i = def_line_index - 1
    while i >= 0:
        line = lines[i].strip()
        if line.startswith("///"):
            # On retire le préfixe '///'
            doc_lines.insert(0, line[3:].strip())
            i -= 1
        else:
            break
    return "\n".join(doc_lines)


def find_end_line(lines, start_index):
    """
    Détermine de manière naïve la dernière ligne d'une définition en comptabilisant les accolades.
    L'index start_index est en base 0.

    :param lines: Liste des lignes du fichier.
    :param start_index: Ligne de départ (0-based) où la définition commence.
    :return: Le numéro de ligne de fin (1-based).
    """
    count = 0
    started = False
    for i in range(start_index, len(lines)):
        line = lines[i]
        # Démarrage dès qu'on trouve une accolade ouvrante
        if not started and "{" in line:
            started = True
        if started:
            count += line.count("{")
            count -= line.count("}")
            if count <= 0:
                return i + 1  # Converti en base 1
    return len(lines)


@transaction.atomic
def py_document_csharp_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier C# en extrayant les définitions de classes et de méthodes.

    Pour chaque classe ou méthode détectée, un composant est créé dans la base de données,
    avec les informations suivantes :
      - name: le nom de la classe ou de la méthode,
      - content: le code source extrait,
      - description: le commentaire XML associé (s'il existe),
      - start_line et end_line : le numéro de la première et de la dernière ligne.

    Si aucune définition n'est détectée, le fichier entier est enregistré comme composant de type "C# File".

    :param file_content: Contenu textuel du fichier C#.
    :param file_instance: Instance du modèle File auquel rattacher le composant.
    :param file_name: Nom (ou chemin) du fichier.
    :param Technology: Technologie associée pour la création des types de composants.
    """
    lines = file_content.splitlines()
    extracted = False

    # Pattern pour détecter une définition de classe.
    class_pattern = re.compile(
        r'^\s*(public|private|internal|protected)?\s*(abstract\s+|static\s+|sealed\s+)?class\s+(?P<name>\w+)',
        re.MULTILINE
    )

    # Pattern pour détecter une définition de méthode (très simplifié)
    method_pattern = re.compile(
        r'^\s*(public|private|internal|protected)?\s*(static\s+)?\s*([\w<>,\s]+)\s+(?P<name>\w+)\s*\([^)]*\)\s*{',
        re.MULTILINE
    )

    # Traitement des définitions de classes
    for match in class_pattern.finditer(file_content):
        extracted = True
        name = match.group("name")
        # Détermination de la ligne de départ
        start_line = file_content.count("\n", 0, match.start()) + 1
        end_line = find_end_line(lines, start_line - 1)
        source = "\n".join(lines[start_line - 1: end_line])
        docstring = get_csharp_docstring(lines, start_line)
        comp_type, _ = ComponentType.objects.get_or_create(name="C# Classes", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
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

    # Traitement des définitions de méthodes
    for match in method_pattern.finditer(file_content):
        extracted = True
        name = match.group("name")
        start_line = file_content.count("\n", 0, match.start()) + 1
        end_line = find_end_line(lines, start_line - 1)
        source = "\n".join(lines[start_line - 1: end_line])
        docstring = get_csharp_docstring(lines, start_line)
        comp_type, _ = ComponentType.objects.get_or_create(name="C# Methods", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
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

    # Si aucune définition de classe ou de méthode n'est détectée, enregistre le fichier entier.
    if not extracted:
        comp_type, _ = ComponentType.objects.get_or_create(name="C# File", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            defaults={
                'content': file_content,
                'start_line': 1,
                'end_line': len(lines),
                'description': "No Classes or Methods detected in this file."
            }
        )
        if not created:
            component.content = file_content
            component.description = "No Classes or Methods detected in this file."
            component.save()
