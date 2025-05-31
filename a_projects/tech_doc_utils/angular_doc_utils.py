import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# Angular FILE DOCUMENTATION UTILITIES – v1                                   #
# --------------------------------------------------------------------------- #
# * Detects the principal artefacts of an Angular (>= v2) project:            #
#     - Components               (@Component)
#     - Directives               (@Directive)
#     - Pipes                    (@Pipe)
#     - Services                 (@Injectable)
#     - Modules                  (@NgModule)
#     - Router configuration     (path: "…", component: FooComponent)
# * Classifies tests (*.spec.ts), templates (HTML), styling, config & assets.  #
###############################################################################

# ---------------------------------------------------------------------------
# Regex patterns (multi‑line, DOTALL aware where necessary)
# ---------------------------------------------------------------------------
COMPONENT_RE = re.compile(r"@Component\s*\([^)]*\)\s*(?:export\s+)?class\s+(?P<name>[A-Z][A-Za-z0-9_]*)", re.S)
DIRECTIVE_RE = re.compile(r"@Directive\s*\([^)]*\)\s*(?:export\s+)?class\s+(?P<name>[A-Z][A-Za-z0-9_]*)", re.S)
PIPE_RE = re.compile(r"@Pipe\s*\([^)]*\)\s*(?:export\s+)?class\s+(?P<name>[A-Z][A-Za-z0-9_]*)", re.S)
SERVICE_RE = re.compile(r"@Injectable\s*\([^)]*\)\s*(?:export\s+)?class\s+(?P<name>[A-Z][A-Za-z0-9_]*)", re.S)
MODULE_RE = re.compile(r"@NgModule\s*\([^)]*\)\s*(?:export\s+)?class\s+(?P<name>[A-Z][A-Za-z0-9_]*)", re.S)
# Router definitions inside *.routing.ts or module files
ROUTE_RE = re.compile(r"path\s*:\s*['\"](?P<path>[^'\"]+)['\"]\s*,\s*component\s*:\s*(?P<comp>[A-Za-z0-9_]+)")

TEST_SUFFIXES = (".spec.ts", ".spec.js", ".test.ts", ".test.js")

BUILD_CONFIGS = {"angular.json", "nx.json", "workspace.json", "tsconfig.json", "tsconfig.app.json", "tsconfig.base.json"}

###############################################################################
# Public entry point
###############################################################################


@transaction.atomic
def angular_document_file(file_content: str, file_instance, file_name: str, technology):
    """Route *file_content* to the adequate Angular parser / classifier."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ----------------------------- CODE (TS / JS) ---------------------------
    if ext in {".ts", ".js"}:  # Angular is TypeScript‑first but support JS projects
        # Ignore type definition stub files
        if ext == ".ts" and file_path.name.endswith(".d.ts"):
            _mark_generic("Stubs", file_path.name, "TypeScript declaration file", file_content, file_instance, technology)
            return

        if _is_test_file(lower_path):
            _mark_generic("Tests", file_path.name, "Jest / Karma test", file_content, file_instance, technology)
        else:
            _document_ts_file(file_content, file_instance, file_name, technology)
        return

    # ------------------------------ TEMPLATES ------------------------------
    if ext == ".html":
        _mark_generic("Templates", file_path.name, "Angular HTML template", file_content, file_instance, technology)
        return

    # ------------------------------- STYLES --------------------------------
    if ext in {".scss", ".sass", ".css", ".less"}:
        _mark_generic("Styling", file_path.name, "Stylesheet", file_content, file_instance, technology)
        return

    # --------------------------- BUILD / CONFIG ---------------------------
    if file_path.name in BUILD_CONFIGS:
        _mark_generic("Build Config", file_path.name, "Angular / workspace config file", file_content, file_instance, technology)
        return
    if file_path.name.startswith("environment.") and ext == ".ts":
        _mark_generic("Env Config", file_path.name, "Angular environment config", file_content, file_instance, technology)
        return
    if ext == ".json" and file_path.name == "package.json":
        _mark_generic("Build Config", file_path.name, "package.json", file_content, file_instance, technology)
        return

    # -------------------------- STATIC / ASSETS ---------------------------
    if any(seg in lower_path for seg in ("/assets/", "\\assets\\")) or ext in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
        comp_type = "Assets"
    else:
        comp_type = "Other"

    _mark_generic(comp_type, file_path.name, f"File categorised as {comp_type}", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Helpers – generic
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    return path.endswith(TEST_SUFFIXES) or "/__tests__/" in path or "\\__tests__\\" in path


def _mark_generic(comp_type: str, component_name: str, description: str, file_content: str, file_instance, technology):
    comp_type_obj, _ = ComponentType.objects.get_or_create(name=comp_type, technology=technology)
    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type_obj,
        name=component_name,
        defaults={
            "content": file_content,
            "start_line": 1,
            "end_line": len(file_content.splitlines()),
            "description": description,
        },
    )
    if not created:
        component.content = file_content
        component.end_line = len(file_content.splitlines())
        component.description = description
        component.save()


# ---------------------------------------------------------------------------
# TypeScript / JavaScript detailed parsing
# ---------------------------------------------------------------------------

def _document_ts_file(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()
    detected = False

    detected |= _extract_pattern(file_content, COMPONENT_RE, "Components", file_instance, technology, "Angular Component")
    detected |= _extract_pattern(file_content, DIRECTIVE_RE, "Directives", file_instance, technology, "Angular Directive")
    detected |= _extract_pattern(file_content, PIPE_RE, "Pipes", file_instance, technology, "Angular Pipe")
    detected |= _extract_pattern(file_content, SERVICE_RE, "Services", file_instance, technology, "Angular Service")
    detected |= _extract_pattern(file_content, MODULE_RE, "Modules", file_instance, technology, "Angular NgModule")

    _extract_routes(lines, file_instance, technology)

    # Fallback if nothing detected
    if not detected and not Component.objects.filter(file=file_instance).exists():
        _mark_generic("Module", file_name, "TS/JS File (no Angular artefact detected)", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_pattern(text: str, regex: re.Pattern, comp_type_name: str, file_instance, technology, description: str) -> bool:
    """Search *text* with *regex* (DOTALL patterns) and store matches."""
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    found = False
    for match in regex.finditer(text):
        name = match.group("name") if "name" in regex.groupindex else match.group(1)
        start_idx = text[: match.start()].count("\n") + 1
        end_idx = start_idx + match.group(0).count("\n")
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
            defaults={
                "content": match.group(0)[:4000],  # avoid huge blobs
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
        match = ROUTE_RE.search(line)
        if match:
            path = match.group("path")
            comp = match.group("comp")
            name = f"Route {path} -> {comp}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": f"Angular route {path} -> {comp}",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.save()
