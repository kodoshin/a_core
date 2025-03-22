import re
from a_projects.models import Component, ComponentType  # adaptez le chemin d'import selon votre projet


def react_document_file(file_content, file_instance, technology):
    """
    Analyse le contenu d’un fichier d’un projet React et crée des entrées dans la table Component.

    Pour chaque composant (défini par une classe étendant React.Component,
    une fonction ou une arrow function), la fonction :
      - Estime les numéros de lignes (début et fin)
      - Recherche certains mots-clés (props, state, hooks, context, etc.) afin de fournir une description
      - Crée une instance de Component en liant le fichier et un type de composant (ici, "Component")

    :param file_content: Le contenu complet du fichier (str)
    :param file_instance: L’instance File associée (pour le ForeignKey)
    :return: Une liste des instances Component créées
    """
    file_name = file_instance.name

    if file_name.endswith('.html'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Templates", technology=technology)
        Component.objects.create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            content=file_content,
            description="Template File",
            start_line=1,
            end_line=len(file_content.splitlines())
        )
    elif file_name.endswith('.css'):
        comp_type, _ = ComponentType.objects.get_or_create(name="Styling", technology=technology)
        Component.objects.create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            content=file_content,
            description="Styling File",
            start_line=1,
            end_line=len(file_content.splitlines())
        )
    else:
        # --- Détection des définitions de composants ---
        # Pattern pour un composant défini en classe
        pattern_class = re.compile(r'class\s+(\w+)\s+extends\s+React\.Component\s*{', re.MULTILINE)
        # Pattern pour une fonction (composant fonctionnel classique)
        pattern_function = re.compile(r'function\s+(\w+)\s*\(.*?\)\s*{', re.MULTILINE | re.DOTALL)
        # Pattern pour une arrow function (composant fonctionnel)
        pattern_arrow = re.compile(r'const\s+(\w+)\s*=\s*\(.*?\)\s*=>\s*{', re.MULTILINE | re.DOTALL)
        # Pattern pour un composant défini via React.forwardRef
        pattern_forwardref = re.compile(r'const\s+(\w+)\s*=\s*React\.forwardRef(?:<[^>]+>)?\s*\(', re.MULTILINE)

        # On collecte les matches sous la forme d'un tuple (position, nom_du_composant, type_détection)
        matches = []
        for m in pattern_class.finditer(file_content):
            matches.append((m.start(), m.group(1), 'ClassComponent'))
        for m in pattern_function.finditer(file_content):
            matches.append((m.start(), m.group(1), 'FunctionComponent'))
        for m in pattern_arrow.finditer(file_content):
            matches.append((m.start(), m.group(1), 'FunctionComponent'))
        for m in pattern_forwardref.finditer(file_content):
            matches.append((m.start(), m.group(1), 'ForwardRefComponent'))

        # Tri par position dans le fichier
        matches.sort(key=lambda x: x[0])

        # --- Définition des patterns d'analyse pour les aspects du composant ---
        analysis_patterns = {
            "Props": r'\bprops\b',
            "State": r'\bthis\.state\b|\buseState\b',
            "Hooks": r'\buse[A-Z]\w+\b',  # repère les hooks commençant par "use"
            "Context": r'\bReact\.createContext\b|\buseContext\b',
            "Routing": r'\b<Route\b|\breact-router\b|\bBrowserRouter\b|\bSwitch\b',
            "State Management": r'\bredux\b|\bcreateStore\b|\bdispatch\b|\bProvider\b',
            "Lifecycle": r'\bcomponentDidMount\b|\bcomponentDidUpdate\b|\bcomponentWillUnmount\b|\bgetDerivedStateFromProps\b',
            "Events": r'\bonClick\b|\bonChange\b|\bonSubmit\b',
            "Styling": r'\bclassName\b|\bstyled\(',
            "Forms": r'\b<form\b|\bonSubmit\b',
            "API Integration": r'\baxios\b|\bfetch\(',
            "Testing": r'\bjest\b|\btest\(',
            "Error Handling": r'\btry\s*{',
            "Optimization": r'\bReact\.memo\b|\buseMemo\b|\buseCallback\b',
            "Rendering": r'\brender\s*\(',
            "Configuration": r'\bconfig\b',
            "Build Tools": r'\bwebpack\b|\bBabel\b',
        }

        components_crees = []

        # Pour estimer la position (numéro de ligne), on compte les sauts de ligne avant une position donnée.
        def get_line_number(pos):
            return file_content[:pos].count('\n') + 1

        # --- Extraction de chaque bloc de composant ---
        for i, (start_idx, comp_name, comp_def_type) in enumerate(matches):
            # La fin du bloc est jusqu'au début du prochain composant ou à la fin du fichier
            end_idx = matches[i+1][0] if i+1 < len(matches) else len(file_content)
            bloc_contenu = file_content[start_idx:end_idx]

            start_line = get_line_number(start_idx)
            end_line = get_line_number(end_idx)

            # Analyse du bloc pour relever les aspects documentés
            aspects_trouves = []
            for aspect, pattern in analysis_patterns.items():
                if re.search(pattern, bloc_contenu):
                    aspects_trouves.append(aspect)
            description = "Utilise : " + ", ".join(aspects_trouves) if aspects_trouves else ""

            # Pour cet exemple, on considère le type de composant comme "Component"
            component_type_name = comp_def_type
            try:
                comp_type_obj = ComponentType.objects.get(name=component_type_name, technology=technology)
            except ComponentType.DoesNotExist:
                comp_type_obj = ComponentType.objects.create(name=component_type_name, technology=technology)

            # Création de l'instance Component en base de données
            Component.objects.create(
                file=file_instance,
                component_type=comp_type_obj,
                name=comp_name,
                content=bloc_contenu,
                description=description,
                start_line=start_line,
                end_line=end_line
            )




