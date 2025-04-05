import javalang
from django.db import transaction
from a_projects.models import Component, ComponentType

@transaction.atomic
def java_document_java_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier Java en extrayant les définitions de classes et de méthodes.

    Pour chaque classe, interface ou enum détectée, un composant est créé dans la base de données,
    avec les informations suivantes :
      - name: le nom de la classe (ou interface, ou enum),
      - content: une partie du code source extrait (basé sur la ligne de déclaration),
      - description: le commentaire associé (non extrait ici, mais potentiellement récupérable en
                     analysant les commentaires préalables),
      - start_line et end_line : le numéro de la première (et ici approximativement de la dernière) ligne.

    Pour chaque méthode détectée au sein d'une classe/interface/enum, un composant est créé de même.

    Si aucune définition n'est détectée, le fichier entier est enregistré comme composant de type "Java File".

    :param file_content: Contenu textuel du fichier Java.
    :param file_instance: Instance du modèle File auquel rattacher le composant.
    :param file_name: Nom (ou chemin) du fichier.
    :param Technology: Technologie associée au composant.
    """
    try:
        tree = javalang.parse.parse(file_content)
    except javalang.parser.JavaSyntaxError as e:
        comp_type, _ = ComponentType.objects.get_or_create(name="Java File", technology=Technology)
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            defaults={
                'content': file_content,
                'start_line': 1,
                'end_line': len(file_content.splitlines()),
                'description': "Java file is not parsable : " + str(e)
            }
        )
        if not created:
            component.content = file_content
            component.description = "Java file is not parsable : " + str(e)
            component.save()
        return

    extracted = False
    lines = file_content.splitlines()

    # Parcours des types (classes, interfaces, enums) définis dans le fichier
    for type_decl in tree.types:
        if isinstance(type_decl, (javalang.tree.ClassDeclaration,
                                  javalang.tree.InterfaceDeclaration,
                                  javalang.tree.EnumDeclaration)):
            extracted = True
            # Pour l'instant, on ne traite pas les javadoc – on peut imaginer les extraire en analysant les commentaires.
            docstring = ""
            start_line = type_decl.position.line if type_decl.position else 1
            # Ici, nous estimons la fin à la même ligne (améliorable avec une logique dédiée)
            end_line = start_line
            # Extraction simple : on prend la ligne de déclaration
            source = lines[start_line - 1] if start_line - 1 < len(lines) else ""
            comp_type, _ = ComponentType.objects.get_or_create(name="Java Classes", technology=Technology)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=type_decl.name,
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

            # Extraction des méthodes au sein du type (si disponible)
            if hasattr(type_decl, 'methods'):
                for method in type_decl.methods:
                    extracted = True
                    docstring = ""
                    start_line = method.position.line if method.position else 1
                    end_line = start_line
                    comp_type_method, _ = ComponentType.objects.get_or_create(name="Java Methods", technology=Technology)
                    source = lines[start_line - 1] if start_line - 1 < len(lines) else ""
                    component, created = Component.objects.get_or_create(
                        file=file_instance,
                        component_type=comp_type_method,
                        name=method.name,
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

    # Si aucune classe ou méthode n'est détectée, on enregistre le fichier entier
    if not extracted:
        comp_type, _ = ComponentType.objects.get_or_create(name="Java File", technology=Technology)
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
