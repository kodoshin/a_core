import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# Vue FILE DOCUMENTATION UTILITIES – v1                                       #
# --------------------------------------------------------------------------- #
#  * Handles Single-File Components (*.vue) and plain JS/TS Vue modules.      #
#  * Detects:                                                                 #
#      - Component name (option API / Composition API / <script setup>)       #
#      - Router records (path ➜ component / name)                             #
#      - Tests, stories, styles, configs, assets.                             #
###############################################################################

# ---------------------------------------------------------------------------
# Regex patterns (DOTALL where needed)                                        #
# ---------------------------------------------------------------------------

# ----- SFC (.vue) -----------------------------------------------------------
SFC_OPT_API_RE = re.compile(
    r"<script[^>]*>.*?export\s+default\s+{[^}]*?name\s*:\s*[\'\"](?P<name>[A-Za-z0-9_\-]+)[\'\"]",
    re.S,
)
SFC_DEFINE_COMP_RE = re.compile(
    r"<script[^>]*>.*?export\s+default\s+defineComponent\s*\([^)]*?name\s*:\s*[\'\"](?P<name>[A-Za-z0-9_\-]+)[\'\"]",
    re.S,
)
# script setup – use filename as component name if none provided

# ----- Plain JS/TS Vue modules ---------------------------------------------
JS_OPT_API_RE = re.compile(
    r"export\s+default\s+{[^}]*?name\s*:\s*[\'\"](?P<name>[A-Za-z0-9_\-]+)[\'\"]",
    re.S,
)
JS_DEFINE_COMP_RE = re.compile(
    r"export\s+default\s+defineComponent\s*\([^)]*?name\s*:\s*[\'\"](?P<name>[A-Za-z0-9_\-]+)[\'\"]",
    re.S,
)

# ----- Router record -------------------------------------------------------
ROUTE_RE = re.compile(
    r"path\s*:\s*[\'\"](?P<path>[^\'\"]+)[\'\"]\s*,\s*(?:component|name)\s*:\s*(?P<comp>[A-Za-z0-9_]+)",
    re.S,
)

TEST_SUFFIXES = (
    ".spec.js",
    ".spec.ts",
    ".spec.jsx",
    ".spec.tsx",
    ".test.js",
    ".test.ts",
    ".test.jsx",
    ".test.tsx",
)

CONFIG_FILES = {
    "vue.config.js",
    "vite.config.js",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "package.json",
}

STYLE_EXTS = {".css", ".scss", ".sass", ".less", ".styl"}
ASSET_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".avif", ".gif"}

###############################################################################
# Public entry point                                                         #
###############################################################################


@transaction.atomic
def vue_document_file(file_content: str, file_instance, file_name: str, technology):
    """Classify/parse *file_content* as part of a Vue.js project."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ------------------------------ SFC -----------------------------------
    if ext == ".vue":
        _document_sfc(file_content, file_instance, file_name, technology)
        return

    # ------------------------------ CODE ----------------------------------
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        if _is_test(lower_path):
            _mark_generic("Tests", file_path.name, "Jest/Vitest test", file_content, file_instance, technology)
        elif _is_story(lower_path):
            _mark_generic("Stories", file_path.name, "Storybook story", file_content, file_instance, technology)
        else:
            _document_js_ts(file_content, file_instance, file_name, technology)
        return

    # ------------------------------ STYLES --------------------------------
    if ext in STYLE_EXTS:
        _mark_generic("Styling", file_path.name, "Stylesheet", file_content, file_instance, technology)
        return

    # ------------------------------ CONFIG --------------------------------
    if file_path.name in CONFIG_FILES or file_path.name.startswith(".env"):
        _mark_generic("Config", file_path.name, "Configuration / env file", file_content, file_instance, technology)
        return

    # ------------------------------ ASSETS --------------------------------
    if ext in ASSET_EXTS or any(seg in lower_path for seg in ("/assets/", "\\assets\\")):
        _mark_generic("Assets", file_path.name, "Static asset", file_content, file_instance, technology)
        return

    # ------------------------------ OTHER ---------------------------------
    _mark_generic("Other", file_path.name, "Unclassified file", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Helpers – generic                                                          #
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return any(path.endswith(suf) for suf in TEST_SUFFIXES) or "/__tests__/" in path or "\\__tests__\\" in path


def _is_story(path: str) -> bool:
    return ".stories." in path or path.endswith((".story.js", ".story.tsx"))


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
# Parsing specifics                                                          #
# ---------------------------------------------------------------------------

def _document_sfc(file_content: str, file_instance, file_name: str, technology):
    """Analyse a .vue Single-File Component."""
    name = None
    for regex in (SFC_OPT_API_RE, SFC_DEFINE_COMP_RE):
        m = regex.search(file_content)
        if m:
            name = m.group("name")
            break
    if not name:
        name = Path(file_name).stem.capitalize()

    _mark_generic("Components", name, "Vue SFC", file_content, file_instance, technology)

    # Extract routes inside <script> if present
    _extract_routes(file_content.splitlines(), file_instance, technology)



def _document_js_ts(file_content: str, file_instance, file_name: str, technology):
    detected = False
    detected |= _extract_pattern(file_content, JS_OPT_API_RE, "Components", file_instance, technology, "Vue component (Options API)")
    detected |= _extract_pattern(file_content, JS_DEFINE_COMP_RE, "Components", file_instance, technology, "Vue component (defineComponent)")

    _extract_routes(file_content.splitlines(), file_instance, technology)

    if not detected and not Component.objects.filter(file=file_instance).exists():
        _mark_generic("Module", file_name, "JS/TS module (no Vue artefact detected)", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Extraction helpers                                                         #
# ---------------------------------------------------------------------------

def _extract_pattern(text: str, regex: re.Pattern, comp_type_name: str, file_instance, technology, description: str) -> bool:
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    found = False
    for match in regex.finditer(text):
        name = match.group("name")
        start_idx = text[: match.start()].count("\n") + 1
        end_idx = start_idx + match.group(0).count("\n")
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
            defaults={
                "content": match.group(0)[:4000],
                "start_line": start_idx,
                "end_line": end_idx,
                "description": description,
            },
        )
        if not created:
            component.content = match.group(0)[:4000]
            component.start_line = start_idx
            component.end_line = end_idx
            component.description = description
            component.save()
        found = True
    return found


def _extract_routes(lines: list[str], file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="Routes", technology=technology)
    for idx, line in enumerate(lines, start=1):
        m = ROUTE_RE.search(line)
        if m:
            path = m.group("path")
            comp = m.group("comp")
            name = f"Route {path} -> {comp}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": f"Vue Router record {path} -> {comp}",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.save()