import re
from pathlib import Path
from typing import List

from a_projects.models import Component, ComponentType  # Ajustez l'import selon votre projet


def react_document_file(file_content: str, file_instance, technology) -> List[Component]:
    """Analyse un fichier React/TSX et crée des entrées *Component* en base.

    - Prend en charge les extensions .js, .jsx, .ts, .tsx, .html, .css/.scss
    - Détecte : classes, fonctions, arrow-functions, composant via forwardRef, annotations React.FC & generics.
    - Estime les numéros de ligne pour chaque composant.

    Args:
        file_content: Contenu complet du fichier.
        file_instance: Instance File (clé étrangère vers le modèle Component).
        technology: Objet *Technology* (clé étrangère vers ComponentType).

    Returns:
        Liste des instances *Component* créées.
    """
    file_name = file_instance.name
    extension = Path(file_name).suffix.lower()

    # --- Gestion des fichiers non-JS/TS -------------------------------------------------------
    if extension in {".html", ".htm"}:
        comp_type, _ = ComponentType.objects.get_or_create(name="Template", technology=technology)
        return [Component.objects.create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            content=file_content,
            description="HTML/Template file",
            start_line=1,
            end_line=len(file_content.splitlines()),
        )]

    if extension in {".css", ".scss", ".sass", ".less"}:
        comp_type, _ = ComponentType.objects.get_or_create(name="Styling", technology=technology)
        return [Component.objects.create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            content=file_content,
            description="Stylesheet",
            start_line=1,
            end_line=len(file_content.splitlines()),
        )]

    # --- Détection des composants JS / TS -----------------------------------------------------
    # Pré-compilation des motifs (écrits pour couvrir la plupart des syntaxes courantes)
    regex_flags = re.MULTILINE | re.DOTALL

    PATTERNS = [
        # 1. Classe (avec éventuels exports, alias React, génériques <P,S>)
        (re.compile(r"(?:export\s+(?:default\s+)?)?class\s+(?P<name>\w+)\s+extends\s+[A-Za-z0-9_.]*Component(?:<[^>{]+>)?\s*{", regex_flags),
         "ClassComponent"),

        # 2. Fonction nommée (générique possible)
        (re.compile(r"(?:export\s+(?:default\s+)?)?function\s+(?P<name>\w+)(?:<[^>{]+>)?\s*\(.*?\)\s*{", regex_flags),
         "FunctionComponent"),

        # 3. Arrow function stockée dans une const (React.FC | FunctionComponent | VFC, ou aucune annotation)
        (re.compile(r"(?:export\s+)?const\s+(?P<name>\w+)(?:\s*:\s*React\.[A-Za-z]*\s*<[^>]*>)?\s*=\s*\(.*?\)\s*=>\s*(?:{|<)", regex_flags),
         "FunctionComponent"),

        # 4. React.forwardRef
        (re.compile(r"(?:export\s+)?const\s+(?P<name>\w+)\s*=\s*(?:React\.)?forwardRef(?:<[^>]+>)?\s*\(", regex_flags),
         "ForwardRefComponent"),
    ]

    # Recherche de tous les composants et tri par position dans le fichier
    matches = []
    for pattern, comp_type in PATTERNS:
        for m in pattern.finditer(file_content):
            matches.append((m.start(), m.group("name"), comp_type))

    matches.sort(key=lambda x: x[0])

    # Si aucun composant détecté, on enregistre tout le fichier comme "Module"
    if not matches:
        comp_type, _ = ComponentType.objects.get_or_create(name="Module", technology=technology)
        return [Component.objects.create(
            file=file_instance,
            component_type=comp_type,
            name=file_name,
            content=file_content,
            description="Fichier sans composants React explicites",
            start_line=1,
            end_line=len(file_content.splitlines()),
        )]

    # --- Patterns d'analyse pour enrichir la description --------------------------------------
    analysis_patterns = {
        "Props": r"\bprops\b",
        "State": r"\bthis\.state\b|\buseState\b",
        "Hooks": r"\buse[A-Z]\w+\b",
        "Context": r"\bReact\.createContext\b|\buseContext\b",
        "Routing": r"\b<Route\b|\breact-router\b|\bBrowserRouter\b|\bSwitch\b",
        "State Management": r"\bredux\b|\bcreateStore\b|\bdispatch\b|\bProvider\b",
        "Lifecycle": r"\bcomponentDid(Mount|Update|Unmount)\b|\bgetDerivedStateFromProps\b",
        "Events": r"\bon(?:Click|Change|Submit)\b",
        "Styling": r"\bclassName\b|\bstyled\(",
        "Forms": r"\b<form\b|\bonSubmit\b",
        "API Integration": r"\baxios\b|\bfetch\(",
        "Testing": r"\b(jest|vitest)\b|\btest\(",
        "Error Handling": r"\btry\s*{",
        "Optimization": r"\bReact\.memo\b|\buse(Memo|Callback)\b",
        "Rendering": r"\brender\s*\(",
        "Build Tools": r"\bwebpack\b|\bBabel\b",
    }

    # Méthode utilitaire pour obtenir le numéro de ligne d'un index
    newline_positions = [pos for pos, ch in enumerate(file_content) if ch == "\n"]
    def get_line_number(pos: int) -> int:
        """Retourne la ligne (1-indexed) correspondant à l'index *pos*."""
        # recherche binaire approximative
        low, high = 0, len(newline_positions)
        while low < high:
            mid = (low + high) // 2
            if newline_positions[mid] < pos:
                low = mid + 1
            else:
                high = mid
        return low + 1  # +1 car lignes commencent à 1

    created_components: List[Component] = []

    for i, (start_idx, comp_name, comp_type_name) in enumerate(matches):
        end_idx = matches[i + 1][0] if i + 1 < len(matches) else len(file_content)
        bloc = file_content[start_idx:end_idx]

        start_line = get_line_number(start_idx)
        end_line = get_line_number(end_idx)

        aspects = [name for name, pat in analysis_patterns.items() if re.search(pat, bloc)]
        description = f"Utilise : {', '.join(aspects)}" if aspects else ""

        comp_type_obj, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)

        created_components.append(Component.objects.create(
            file=file_instance,
            component_type=comp_type_obj,
            name=comp_name,
            content=bloc,
            description=description,
            start_line=start_line,
            end_line=end_line,
        ))

    return created_components
