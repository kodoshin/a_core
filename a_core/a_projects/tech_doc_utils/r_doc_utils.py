import re
from django.db import transaction
from a_projects.models import Component, ComponentType


def _extract_docstring(lines, current_line):
    """
    Extrait le docstring en remontant les lignes précédentes si elles commencent par "#'"
    """
    doc_lines = []
    j = current_line - 1
    while j >= 1:
        line = lines[j - 1].strip()
        if line.startswith("#'"):
            # On enlève le préfixe "#'" et les espaces éventuels
            doc_lines.insert(0, line[2:].strip())
            j -= 1
        else:
            break
    return "\n".join(doc_lines)


def _extract_block(lines, start_index):
    """
    À partir d'un indice de départ (1-indexé), extrait un bloc de code en comptant les accolades.
    Si aucun bloc n’est détecté, retourne le contenu à partir de start_index jusqu’à la fin.
    """
    block_lines = []
    brace_count = 0
    found_brace = False
    total_lines = len(lines)
    for k in range(start_index, total_lines + 1):
        line = lines[k - 1]
        block_lines.append(line)
        # On incrémente/décrémente en fonction des accolades trouvées sur la ligne
        brace_count += line.count("{")
        brace_count -= line.count("}")
        if "{" in line:
            found_brace = True
        # Lorsque l'on a ouvert un bloc et que les accolades sont équilibrées, on arrête
        if found_brace and brace_count == 0:
            return "\n".join(block_lines), k
    # Si aucune accolade n'est trouvée ou que le bloc n'est pas terminé, on renvoie jusqu'à la fin du fichier
    return "\n".join(block_lines), total_lines


@transaction.atomic
def r_document_r_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier R en extrayant les définitions de fonctions et de classes.

    Pour chaque fonction ou classe détectée, un composant est créé dans la base de données,
    avec les informations suivantes :
      - name: le nom de la fonction ou de la classe,
      - content: le bloc de code extrait (en utilisant un comptage naïf des accolades),
      - description: le docstring (documentation roxygen) associé (s'il existe),
      - start_line et end_line: le numéro de la première et de la dernière ligne du bloc.

    Si aucune définition n'est détectée, le fichier entier est enregistré comme composant de type "R File".

    :param file_content: Contenu textuel du fichier R.
    :param file_instance: Instance du modèle File auquel rattacher le composant.
    :param file_name: Nom (ou chemin) du fichier.
    :param Technology: Technologie associée (pour filtrer/associer les ComponentType).
    """
    lines = file_content.splitlines()
    extracted = False

    # --- Traitement des définitions de fonctions ---
    # Recherche les lignes commençant par "nom <- function(" ou "nom = function("
    func_pattern = re.compile(r'^(\w+)\s*(?:<-|=)\s*function\s*\(', re.MULTILINE)
    for i, line in enumerate(lines, start=1):
        m = func_pattern.match(line)
        if m:
            extracted = True
            func_name = m.group(1)
            start_line = i
            # Extraction de la documentation (docstring) à partir des commentaires roxygen précédents
            docstring = _extract_docstring(lines, i)
            # Extraction du bloc de la fonction (en comptant les accolades)
            source, end_line = _extract_block(lines, i)
            comp_type, _ = ComponentType.objects.get_or_create(name="R Functions", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=func_name,
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

    # --- Traitement des définitions de classes S4 via setClass ---
    class_pattern_s4 = re.compile(r'setClass\s*\(\s*["\'](\w+)["\']')
    for i, line in enumerate(lines, start=1):
        m = class_pattern_s4.search(line)
        if m:
            extracted = True
            class_name = m.group(1)
            start_line = i
            docstring = _extract_docstring(lines, i)
            source, end_line = _extract_block(lines, i)
            comp_type, _ = ComponentType.objects.get_or_create(name="R Classes", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=class_name,
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

    # --- Traitement des définitions de classes R6 via R6Class ---
    class_pattern_r6 = re.compile(r'R6Class\s*\(\s*["\'](\w+)["\']')
    for i, line in enumerate(lines, start=1):
        m = class_pattern_r6.search(line)
        if m:
            extracted = True
            class_name = m.group(1)
            start_line = i
            docstring = _extract_docstring(lines, i)
            source, end_line = _extract_block(lines, i)
            comp_type, _ = ComponentType.objects.get_or_create(name="R Classes", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=class_name,
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

    # --- Si aucune définition n'a été détectée, enregistre le fichier entier ---
    if not extracted:
        comp_type, _ = ComponentType.objects.get_or_create(name="R File", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            defaults={
                'content': file_content,
                'end_line': len(lines),
                'description': "Aucune fonction ou classe détectée dans ce fichier."
            }
        )
        if not created:
            component.content = file_content
            component.description = "Aucune fonction ou classe détectée dans ce fichier."
            component.save()
