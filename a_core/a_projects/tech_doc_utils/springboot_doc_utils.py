import re
from django.db import transaction
from a_projects.models import Component, ComponentType


@transaction.atomic
def springboot_document_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente le contenu d'un fichier d'un projet Spring Boot et enregistre les composants trouvés
    dans la table Component.

    Les composants documentés peuvent être :
        - Controllers (ex : @RestController, @Controller)
        - Services (ex : @Service)
        - Repositories (ex : @Repository)
        - Components (ex : @Component)
        - Configurations (ex : @Configuration)
        - Java Classes (si aucune annotation spécifique n'est trouvée)

    :param file_content: Le contenu textuel du fichier.
    :param file_instance: L'instance du modèle File auquel rattacher les composants.
    :param file_name: Le nom (ou chemin) du fichier (utile pour détecter le type).
    :param Technology: L'instance ou la référence à la technologie associée.
    """
    # Pour les fichiers Java, on documente les composants à l'aide d'une expression régulière
    if file_name.endswith('.java'):
        springboot_document_java_file(file_content, file_instance, file_name, Technology)
    # Pour les templates HTML (exemple pour Thymeleaf)
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
            description="Styling File",
            start_line=1,
            defaults={'content': file_content, 'end_line': len(file_content.splitlines())}
        )
        if not created:
            component.content = file_content
            component.save()
    else:
        # Pour d'autres types de fichiers, par exemple les configurations ou les fichiers statiques
        if "application.properties" in file_name.lower() or "application.yml" in file_name.lower():
            comp_type_name = "Configurations"
        elif "static" in file_name.lower():
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


def springboot_document_java_file(file_content: str, file_instance, file_name: str, Technology):
    """
    Documente un fichier Java d'un projet Spring Boot en extrayant les définitions de classes
    annotées et enregistre ces éléments dans la table Component.

    Les composants documentés peuvent inclure :
        - Controllers (@RestController, @Controller)
        - Services (@Service)
        - Repositories (@Repository)
        - Components (@Component)
        - Configurations (@Configuration)
        - Java Classes (si aucune annotation spécifique n'est trouvée)

    :param file_content: Le contenu du fichier Java.
    :param file_instance: L'instance du modèle File.
    :param file_name: Le nom (ou chemin) du fichier.
    :param Technology: L'instance ou la référence à la technologie associée.
    """
    # Expression régulière pour capturer (optionnellement) le commentaire JavaDoc, les annotations et la déclaration de classe ou interface
    pattern = r'(?P<javadoc>/\*\*(?:.|\n)*?\*/)?\s*(?P<annotations>(?:@\w+(?:\([^)]*\))?\s*)+)?\s*(public\s+)?(class|interface)\s+(?P<name>\w+)'
    matches = re.finditer(pattern, file_content, re.MULTILINE | re.DOTALL)

    for match in matches:
        javadoc = match.group('javadoc') or ""
        annotations = match.group('annotations') or ""
        class_name = match.group('name')

        # Déduire le type de composant en fonction des annotations Spring
        comp_type_name = "Java Classes"
        if '@RestController' in annotations or '@Controller' in annotations:
            comp_type_name = "Controllers"
        elif '@Service' in annotations:
            comp_type_name = "Services"
        elif '@Repository' in annotations:
            comp_type_name = "Repositories"
        elif '@Configuration' in annotations:
            comp_type_name = "Configurations"
        elif '@Component' in annotations:
            comp_type_name = "Components"

        comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=Technology)

        # Calculer le numéro de ligne de début et de fin pour le composant
        start_line = file_content.count('\n', 0, match.start()) + 1
        end_line = file_content.count('\n', 0, match.end()) + 1

        # Le code source extrait correspond à la partie matchée
        source = match.group(0)
        # Utiliser le JavaDoc comme description si présent, sinon les annotations
        description = javadoc.strip() if javadoc else annotations.strip()

        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=class_name,
            defaults={'content': source, 'start_line': start_line, 'end_line': end_line, 'description': description}
        )
        if not created:
            component.content = source
            component.description = description
            component.save()
