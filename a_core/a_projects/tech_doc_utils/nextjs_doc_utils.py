import re
from a_projects.models import Component, ComponentType  # Adaptez l'import selon votre projet Django


def nextjs_document_file(file_content, file_instance, technology):
    """
    Analyse le contenu d’un fichier d’un projet Next.js et crée des entrées dans la table Component.

    La fonction détecte différents types d’éléments :
      - Composants React (classes, fonctions, arrow functions, React.forwardRef)
      - Pages Next.js (export default)
      - Fonctions de data fetching Next.js (getStaticProps, getServerSideProps, getStaticPaths)
      - API Routes Next.js
      - Fichier de configuration Next.js (next.config.js)

    Pour chaque élément, la fonction :
      - Calcule le numéro de ligne de début et de fin du bloc
      - Analyse le bloc de code pour relever certains aspects (props, state, hooks, etc.)
      - Crée une instance de Component dans la base, en liant le fichier et le type d’élément détecté

    :param file_content: Contenu complet du fichier (str)
    :param file_instance: Instance File associée (ForeignKey)
    :return: Liste des instances Component créées
    """

    # --- Cas particulier : fichier de configuration Next.js ---

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
        if file_instance.name.lower() == "next.config.js":
            try:
                comp_type_obj = ComponentType.objects.get(name="NextConfig", technology=technology)
            except ComponentType.DoesNotExist:
                comp_type_obj = ComponentType.objects.create(name="NextConfig", technology=technology)
            component = Component.objects.create(
                file=file_instance,
                component_type=comp_type_obj,
                name="NextConfig",
                content=file_content,
                description="Fichier de configuration Next.js",
                start_line=1,
                end_line=file_content.count("\n") + 1
            )
            return [component]

        # --- Définition des patterns pour les éléments React et Next.js ---
        # Composants React classiques
        pattern_class = re.compile(r'class\s+(\w+)\s+extends\s+React\.Component\s*{', re.MULTILINE)
        pattern_function = re.compile(r'function\s+(\w+)\s*\(.*?\)\s*{', re.MULTILINE | re.DOTALL)
        pattern_arrow = re.compile(r'const\s+(\w+)\s*=\s*\(.*?\)\s*=>\s*{', re.MULTILINE | re.DOTALL)
        pattern_forwardref = re.compile(r'const\s+(\w+)\s*=\s*React\.forwardRef(?:<[^>]+>)?\s*\(', re.MULTILINE)

        # Pages Next.js
        pattern_page_default = re.compile(r'export\s+default\s+function\s+(\w+)\s*\(', re.MULTILINE)
        pattern_page_default_arrow = re.compile(r'export\s+default\s+\(?\s*(\w+)?\s*\)?\s*=>\s*{', re.MULTILINE)

        # Fonctions de data fetching Next.js
        pattern_getStaticProps = re.compile(r'export\s+async\s+function\s+getStaticProps\s*\(', re.MULTILINE)
        pattern_getStaticProps_arrow = re.compile(r'export\s+const\s+getStaticProps\s*=\s*async\s*\(', re.MULTILINE)
        pattern_getServerSideProps = re.compile(r'export\s+async\s+function\s+getServerSideProps\s*\(', re.MULTILINE)
        pattern_getServerSideProps_arrow = re.compile(r'export\s+const\s+getServerSideProps\s*=\s*async\s*\(', re.MULTILINE)
        pattern_getStaticPaths = re.compile(r'export\s+async\s+function\s+getStaticPaths\s*\(', re.MULTILINE)
        pattern_getStaticPaths_arrow = re.compile(r'export\s+const\s+getStaticPaths\s*=\s*async\s*\(', re.MULTILINE)

        # API Routes Next.js
        pattern_api_route = re.compile(r'export\s+default\s+function\s+handler\s*\(', re.MULTILINE)
        pattern_api_route_arrow = re.compile(r'export\s+default\s+\(.*?req.*?res.*?\)\s*=>\s*{', re.MULTILINE | re.DOTALL)

        # Construction d'une liste de tuples :
        # (pattern, type d’élément, indice du groupe pour extraire le nom ou None)
        patterns = [
            (pattern_class, 'ClassComponent', 1),
            (pattern_function, 'FunctionComponent', 1),
            (pattern_arrow, 'FunctionComponent', 1),
            (pattern_forwardref, 'ForwardRefComponent', 1),
            (pattern_page_default, 'NextPage', 1),
            (pattern_page_default_arrow, 'NextPage', 1),
            (pattern_getStaticProps, 'GetStaticProps', None),
            (pattern_getStaticProps_arrow, 'GetStaticProps', None),
            (pattern_getServerSideProps, 'GetServerSideProps', None),
            (pattern_getServerSideProps_arrow, 'GetServerSideProps', None),
            (pattern_getStaticPaths, 'GetStaticPaths', None),
            (pattern_getStaticPaths_arrow, 'GetStaticPaths', None),
            (pattern_api_route, 'APIRoute', None),
            (pattern_api_route_arrow, 'APIRoute', None),
        ]

        # --- Détection des éléments dans le fichier ---
        matches = []
        for pat, comp_type, group_index in patterns:
            for m in pat.finditer(file_content):
                if group_index is not None:
                    # Si le groupe capturé est vide (cas d'une arrow function sans nom explicite), on utilise le type
                    comp_name = m.group(group_index) if m.group(group_index) else comp_type
                else:
                    comp_name = comp_type
                matches.append((m.start(), comp_name, comp_type))

        # Tri des éléments par leur position dans le fichier
        matches.sort(key=lambda x: x[0])

        # --- Analyse complémentaire du bloc de code (recherche d’aspects d’utilisation) ---
        analysis_patterns = {
            "Props": r'\bprops\b',
            "State": r'\bthis\.state\b|\buseState\b',
            "Hooks": r'\buse[A-Z]\w+\b',
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

        def get_line_number(pos):
            return file_content[:pos].count('\n') + 1

        # --- Extraction de chaque bloc d’élément détecté ---
        for i, (start_idx, comp_name, comp_def_type) in enumerate(matches):
            # Le bloc s'étend jusqu'au début du prochain élément ou à la fin du fichier
            end_idx = matches[i + 1][0] if i + 1 < len(matches) else len(file_content)
            bloc_contenu = file_content[start_idx:end_idx]

            start_line = get_line_number(start_idx)
            end_line = get_line_number(end_idx)

            # Recherche d’aspects (mot-clés) dans le bloc
            aspects_trouves = []
            for aspect, pat in analysis_patterns.items():
                if re.search(pat, bloc_contenu):
                    aspects_trouves.append(aspect)
            description = "Utilise : " + ", ".join(aspects_trouves) if aspects_trouves else ""

            # Récupération ou création du type d’élément dans la base
            try:
                comp_type_obj = ComponentType.objects.get(name=comp_def_type, technology=technology)
            except ComponentType.DoesNotExist:
                comp_type_obj = ComponentType.objects.create(name=comp_def_type, technology=technology)

            Component.objects.create(
                file=file_instance,
                component_type=comp_type_obj,
                name=comp_name,
                content=bloc_contenu,
                description=description,
                start_line=start_line,
                end_line=end_line
            )


