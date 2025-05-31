import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###########################################################################
# Java (generic) FILE DOCUMENTATION UTILITIES – v2                         #
# ----------------------------------------------------------------------- #
#  * Detects Java classes, interfaces, enums, tests.                      #
#  * Handles Maven/Gradle build files, resources, configs, assets.        #
#  * Picks up JAX‑RS (@Path) or Spring‑like @RequestMapping endpoints.    #
###########################################################################

# ---------------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------------
CLASS_RE = re.compile(r"\bclass\s+(?P<name>[A-Z][A-Za-z0-9_]*)")
INTERFACE_RE = re.compile(r"\binterface\s+(?P<name>[A-Z][A-Za-z0-9_]*)")
ENUM_RE = re.compile(r"\benum\s+(?P<name>[A-Z][A-Za-z0-9_]*)")

# JAX‑RS style endpoints: @Path("/resource")
JAX_PATH_RE = re.compile(r"@Path\(\s*\"(?P<path>[^\"]+)\"\s*\)")
# Spring style @RequestMapping / @GetMapping("/foo") etc.
SPRING_MAPPING_RE = re.compile(
    r'@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping)\s*'  # annotation
    r'\(\s*"'                                                             # literal ("
    r'(?P<path>[^"]+)'                                                    # capture path
    r'"\)'                                                                # literal ")
)


@transaction.atomic
def java_document_file(file_content: str, file_instance, file_name: str, technology):
    """Entry point to classify and document Java‑ecosystem files."""
    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ------------------------- BUILD CONFIGS -----------------------------
    if file_path.name in {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}:
        _mark_generic(
            comp_type="Build Config",
            component_name=file_path.name,
            description="Fichier de configuration Maven / Gradle",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ---------------------------- JAVA SOURCE ---------------------------
    if ext == ".java":
        if _is_test(lower_path):
            _mark_generic(
                comp_type="Tests",
                component_name=file_path.name,
                description="Test JUnit / TestNG",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_java_source(file_content, file_instance, file_name, technology)
        return

    # ---------------------- KOTLIN / GROOVY SOURCE ----------------------
    if ext in {".kt", ".kts"}:
        _mark_generic(
            comp_type="Kotlin Source",
            component_name=file_path.name,
            description="Fichier Kotlin",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return
    if ext == ".groovy":
        _mark_generic(
            comp_type="Groovy Source",
            component_name=file_path.name,
            description="Fichier Groovy",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- RESOURCES ------------------------------
    if ext in {".properties", ".yaml", ".yml", ".xml"}:
        comp = "Config" if any(k in file_path.name for k in ("application", "config", "settings")) else "Resources"
        _mark_generic(
            comp_type=comp,
            component_name=file_path.name,
            description="Fichier de configuration / ressource",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- STATIC / OTHER -------------------------
    if any(seg in lower_path for seg in ("/static/", "\\static\\", "/public/", "\\public\\")):
        comp_type = "Static Files"
    else:
        comp_type = "Other"
    _mark_generic(
        comp_type=comp_type,
        component_name=file_path.name,
        description=f"Fichier catégorisé {comp_type}",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return (
        "/src/test/" in path
        or "\\src\\test\\" in path
        or path.endswith("Test.java")
        or path.endswith("Tests.java")
    )


def _mark_generic(*, comp_type: str, component_name: str, description: str, file_content: str, file_instance, technology):
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
# Java source detailed parsing
# ---------------------------------------------------------------------------

def _document_java_source(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()
    any_found = False

    # Classes, interfaces, enums
    any_found |= _extract_pattern(lines, CLASS_RE, "Classes", file_instance, technology, "Class definition")
    any_found |= _extract_pattern(lines, INTERFACE_RE, "Interfaces", file_instance, technology, "Interface definition")
    any_found |= _extract_pattern(lines, ENUM_RE, "Enums", file_instance, technology, "Enum definition")

    # Endpoints (JAX‑RS / Spring)
    _extract_endpoints(lines, file_instance, technology)

    if not any_found:
        _mark_generic(
            comp_type="Module",
            component_name=file_name,
            description="Fichier Java (aucune entité détectée)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


def _extract_pattern(lines, regex, comp_type_name, file_instance, technology, description):
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    found = False
    for idx, line in enumerate(lines, start=1):
        match = regex.search(line)
        if match:
            name = match.group("name")
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


def _extract_endpoints(lines, file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)
    for idx, line in enumerate(lines, start=1):
        path_match = JAX_PATH_RE.search(line) or SPRING_MAPPING_RE.search(line)
        if path_match:
            path = path_match.group("path")
            name = f"Endpoint {path}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": f"Route {path}",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.description = f"Route {path}"
                component.save()
