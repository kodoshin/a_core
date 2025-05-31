import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# Remix FILE DOCUMENTATION UTILITIES – v1                                     #
# --------------------------------------------------------------------------- #
#  * Detects Remix routes (app/routes/*) and their artefacts:                 #
#      - Default React component export                                        #
#      - loader() & action() back‑end funcs                                    #
#      - meta(), links(), headers(), handle                                    #
#  * Identifies tests, storybook stories, styles, configs, assets.            #
###############################################################################

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
FUNC_COMPONENT_RE = re.compile(r"(?:export\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(")
ARROW_COMPONENT_RE = re.compile(r"(?:export\s+)?(?:const|let|var)\s+([A-Z][A-Za-z0-9_]*)\s*=\s*\(?.*?=>")
DEFAULT_EXPORT_COMPONENT_RE = re.compile(r"export\s+default\s+function\s+([A-Z][A-Za-z0-9_]*)\s*\(")
LOADER_RE = re.compile(r"(?:export\s+)?(?:async\s+)?(?:const|function)\s+loader\b")
ACTION_RE = re.compile(r"(?:export\s+)?(?:async\s+)?(?:const|function)\s+action\b")
META_RE = re.compile(r"export\s+function\s+meta\b")
LINKS_RE = re.compile(r"export\s+function\s+links\b")
HEADERS_RE = re.compile(r"export\s+function\s+headers\b")
HANDLE_RE = re.compile(r"export\s+const\s+handle\b")

TEST_SUFFIXES = (".test.js", ".test.jsx", ".test.ts", ".test.tsx", ".spec.js", ".spec.jsx", ".spec.ts", ".spec.tsx")

CONFIG_FILES = {"remix.config.js", "remix.config.mjs", "tailwind.config.js", "vitest.config.ts", "jest.config.js"}

###############################################################################
# Public entry point
###############################################################################


@transaction.atomic
def remix_document_file(file_content: str, file_instance, file_name: str, technology):
    """Main router that classifies *file_content* belonging to a Remix project."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # -------------------------- CODE: JS / TS / JSX / TSX ------------------
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        if _is_test(lower_path):
            _mark_generic("Tests", file_path.name, "Test file (Vitest/Jest)", file_content, file_instance, technology)
        elif _is_story(lower_path):
            _mark_generic("Stories", file_path.name, "Storybook story", file_content, file_instance, technology)
        else:
            _document_remix_code(file_content, file_instance, file_name, technology, route_file=_is_route(lower_path))
        return

    # ------------------------- STYLES -------------------------------------
    if ext in {".css", ".scss", ".sass", ".less"}:
        _mark_generic("Styling", file_path.name, "Stylesheet", file_content, file_instance, technology)
        return

    # ------------------------- CONFIG / ENV -------------------------------
    if file_path.name in CONFIG_FILES or file_path.name.startswith(".env"):
        _mark_generic("Config", file_path.name, "Config / Env file", file_content, file_instance, technology)
        return

    # ------------------------- ASSETS ------------------------------------
    if any(seg in lower_path for seg in ("/public/", "\\public\\")) or ext in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".avif"}:
        comp_type = "Assets"
    else:
        comp_type = "Other"
    _mark_generic(comp_type, file_path.name, f"File categorised as {comp_type}", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Helpers – generic
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return any(path.endswith(suffix) for suffix in TEST_SUFFIXES) or "/__tests__/" in path or "\\__tests__\\" in path


def _is_story(path: str) -> bool:
    return ".stories." in path or path.endswith((".story.tsx", ".story.jsx"))


def _is_route(path: str) -> bool:
    return "/routes/" in path or "\\routes\\" in path


def _mark_generic(comp_type: str, component_name: str, description: str, file_content: str, file_instance, technology):
    comp_type_obj, _ = ComponentType.objects.get_or_create(name=comp_type, technology=technology)
    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type_obj,
        name=component_name,
        defaults={
            "content": file_content if len(file_content) < 4000 else file_content[:4000] + "…",
            "start_line": 1,
            "end_line": len(file_content.splitlines()),
            "description": description,
        },
    )
    if not created:
        component.content = file_content if len(file_content) < 4000 else file_content[:4000] + "…"
        component.end_line = len(file_content.splitlines())
        component.description = description
        component.save()


# ---------------------------------------------------------------------------
# Detailed parsing for Remix route / component files
# ---------------------------------------------------------------------------

def _document_remix_code(file_content: str, file_instance, file_name: str, technology, *, route_file: bool):
    lines = file_content.splitlines()
    detected = False

    # React component exports (named or default)
    detected |= _extract_pattern(lines, DEFAULT_EXPORT_COMPONENT_RE, "Components", file_instance, technology, "Default export component")
    detected |= _extract_pattern(lines, FUNC_COMPONENT_RE, "Components", file_instance, technology, "Functional component")
    detected |= _extract_pattern(lines, ARROW_COMPONENT_RE, "Components", file_instance, technology, "Arrow component")

    # Remix data loaders & actions
    _extract_pattern(lines, LOADER_RE, "Loaders", file_instance, technology, "Remix loader()")
    _extract_pattern(lines, ACTION_RE, "Actions", file_instance, technology, "Remix action()")

    # Meta / Links / Headers / Handle
    _extract_pattern(lines, META_RE, "Meta", file_instance, technology, "meta() function")
    _extract_pattern(lines, LINKS_RE, "Links", file_instance, technology, "links() function")
    _extract_pattern(lines, HEADERS_RE, "Headers", file_instance, technology, "headers() function")
    _extract_pattern(lines, HANDLE_RE, "Handle", file_instance, technology, "handle const")

    # If file lives under routes/ directory, also mark it explicitly as Route
    if route_file:
        _mark_generic("Routes", file_name, "Remix route file", file_content, file_instance, technology)

    # Fallback: if nothing stored yet
    if not Component.objects.filter(file=file_instance).exists():
        _mark_generic("Module", file_name, "JS/TS file (no Remix artefact detected)", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Generic line‑wise extraction helper
# ---------------------------------------------------------------------------

def _extract_pattern(lines: list[str], regex: re.Pattern, comp_type_name: str, file_instance, technology, description: str) -> bool:
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    found = False
    for idx, line in enumerate(lines, start=1):
        match = regex.search(line)
        if match:
            name = match.group(1) if match.groups() else regex.pattern.split("\\s+")[0]
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": description,
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.description = description
                component.save()
            found = True
    return found
