import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# SvelteKit FILE DOCUMENTATION UTILITIES – v1                                 #
# --------------------------------------------------------------------------- #
#  * Covers file‑based routing in SvelteKit (>= v1.29):                       #
#      - +page.svelte / +page.ts / +page.js  » Components & page load()       #
#      - +layout.svelte / +layout.ts         » Layouts & layout load()        #
#      - +server.ts / +page.server.ts        » Server endpoints & actions     #
#      - +error.svelte, +layout.server.ts    » Error/Server layouts           #
#  * Detects load() / actions / handle hooks / endpoints.                     #
#  * Classifies tests, stories, styles, config, static assets.                #
###############################################################################

# ---------------------------------------------------------------------------
# Regex patterns                                                              #
# ---------------------------------------------------------------------------
LOAD_FUNC_RE = re.compile(r"(?:export\s+)?async\s+function\s+load\b")
ACTIONS_OBJ_RE = re.compile(r"export\s+const\s+actions\s*=\s*{", re.S)
HANDLE_FUNC_RE = re.compile(r"(?:export\s+)?async\s+function\s+handle\b")

# Inside .svelte <script context="module"> or plain JS/TS modules
MODULE_SCRIPT_RE = re.compile(r"<script[^>]*context=\"module\"[^>]*>(.*?)</script>", re.S)

TEST_SUFFIXES = (
    ".spec.ts",
    ".spec.js",
    ".spec.tsx",
    ".test.ts",
    ".test.js",
    ".test.tsx",
)

CONFIG_FILES = {
    "svelte.config.js",
    "svelte.config.cjs",
    "vite.config.js",
    "vite.config.ts",
    "tsconfig.json",
    "package.json",
}

STYLE_EXTS = {".css", ".scss", ".sass", ".less", ".styl"}
ASSET_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".avif", ".gif"}

###############################################################################
# Public entry point                                                         #
###############################################################################


@transaction.atomic
def sveltekit_document_file(file_content: str, file_instance, file_name: str, technology):
    """Route *file_content* to the appropriate SvelteKit parser."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ------------------------------ SFC (.svelte) --------------------------
    if ext == ".svelte":
        _document_svelte_file(file_content, file_instance, file_path, technology)
        return

    # ------------------------------ CODE ----------------------------------
    if ext in {".ts", ".js"}:
        if _is_test(lower_path):
            _mark_generic("Tests", file_path.name, "Vitest/Jest test", file_content, file_instance, technology)
        else:
            _document_ts_js_file(file_content, file_instance, file_path, technology)
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
    if ext in ASSET_EXTS or any(seg in lower_path for seg in ("/static/", "\\static\\")):
        _mark_generic("Assets", file_path.name, "Static asset", file_content, file_instance, technology)
        return

    # ------------------------------ OTHER ---------------------------------
    _mark_generic("Other", file_path.name, "Unclassified file", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Generic helpers                                                             #
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return any(path.endswith(suf) for suf in TEST_SUFFIXES) or "/__tests__/" in path or "\\__tests__\\" in path


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
# Parsing specifics                                                           #
# ---------------------------------------------------------------------------

def _document_svelte_file(content: str, file_instance, path: Path, technology):
    """Analyse a .svelte page / layout / component file."""
    name = path.stem  # +page, MyComponent, etc.

    # Distinguish by naming convention
    if name.startswith("+page"):
        comp_type = "Pages"
    elif name.startswith("+layout"):
        comp_type = "Layouts"
    elif name.startswith("+error"):
        comp_type = "Errors"
    else:
        comp_type = "Components"

    _mark_generic(comp_type, path.name, f"Svelte {comp_type[:-1]}", content, file_instance, technology)

    # Extract load/actions/handle inside <script context="module"> blocks
    for module_script in MODULE_SCRIPT_RE.findall(content):
        _scan_module_block(module_script, file_instance, technology)

    # Also scan inline script (no context="module") for load()
    _scan_module_block(content, file_instance, technology)



def _document_ts_js_file(content: str, file_instance, path: Path, technology):
    """Parse JS/TS files such as +page.ts, +server.ts, hooks.server.ts etc."""
    name = path.name

    # Determine type based on filename conventions
    if name.startswith("+page.server"):
        primary_type = "Page Servers"
    elif name.startswith("+page"):
        primary_type = "Page Scripts"
    elif name.startswith("+layout.server"):
        primary_type = "Layout Servers"
    elif name.startswith("+layout"):
        primary_type = "Layout Scripts"
    elif name.startswith("+server"):
        primary_type = "Endpoints"
    elif name in {"hooks.server.ts", "hooks.server.js"}:
        primary_type = "Hooks"
    else:
        primary_type = "Module"

    _mark_generic(primary_type, name, f"SvelteKit {primary_type}", content, file_instance, technology)

    _scan_module_block(content, file_instance, technology)


# ---------------------------------------------------------------------------
# Module‑level scan for load/actions/handle                                    #
# ---------------------------------------------------------------------------

def _scan_module_block(text: str, file_instance, technology):
    _extract_pattern(text, LOAD_FUNC_RE, "Loaders", file_instance, technology, "load() function")
    _extract_pattern(text, ACTIONS_OBJ_RE, "Actions", file_instance, technology, "actions object")
    _extract_pattern(text, HANDLE_FUNC_RE, "Handles", file_instance, technology, "handle() hook")


# ---------------------------------------------------------------------------
# Generic extraction helper                                                   #
# ---------------------------------------------------------------------------

def _extract_pattern(text: str, regex: re.Pattern, comp_type_name: str, file_instance, technology, description: str):
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    for match in regex.finditer(text):
        start_idx = text[: match.start()].count("\n") + 1
        end_idx = start_idx + match.group(0).count("\n")
        name = f"{comp_type_name[:-1]}@{start_idx}"  # e.g., Loader@23
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
