import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

##############################################################################
# Spring Boot FILE DOCUMENTATION UTILITIES – v2                              #
# -------------------------------------------------------------------------- #
# * Detects Java/Kotlin/Groovy sources specific to Spring Boot.              #
# * Extracts @RestController endpoints, @Entity JPA classes, Services,       #
#   Repositories.                                                            #
# * Classifies build configs (Maven/Gradle), application configs, templates, #
#   static assets, tests.                                                    #
##############################################################################

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
SPRING_MAPPING_RE = re.compile(
    r'@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*'  # annotation
    r'\(\s*"(?P<path>[^"]+)"\)'                                                            # littéraux ("…")
)
JPA_ENTITY_RE = re.compile(r"@Entity\b")
REPO_RE = re.compile(r"interface\s+(?P<name>[A-Z][A-Za-z0-9_]*)\s+extends\s+.*Repository")
SERVICE_RE = re.compile(r"@Service\b")
CONTROLLER_RE = re.compile(r"@RestController\b|@Controller\b")
CLASS_RE = re.compile(r"class\s+(?P<name>[A-Z][A-Za-z0-9_]*)")

BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}

@transaction.atomic
def springboot_document_file(file_content: str, file_instance, file_name: str, technology):
    """Entry point to classify Spring Boot project files."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ----------------------- BUILD / PROJECT CONFIG -----------------------
    if file_path.name in BUILD_FILES:
        _mark_generic("Build Config", file_path.name, "Maven / Gradle File", file_content, file_instance, technology)
        return

    # -------------------------- APPLICATION CONFIG -----------------------
    if file_path.name in {"application.properties", "application.yml", "application.yaml"}:
        _mark_generic("Config", file_path.name, "Spring Boot Config", file_content, file_instance, technology)
        return

    # ------------------------- TEMPLATES ---------------------------------
    if ext in {".html", ".jsp", ".ftl", ".mustache"} and (
        "/templates/" in lower_path or "\\templates\\" in lower_path
    ):
        _mark_generic("Templates", file_path.name, "Template view", file_content, file_instance, technology)
        return

    # -------------------------- STATIC FILES -----------------------------
    if any(seg in lower_path for seg in ("/static/", "\\static\\", "/public/", "\\public\\")):
        _mark_generic("Static Files", file_path.name, "Static Resource", file_content, file_instance, technology)
        return

    # --------------------------- JAVA SOURCE -----------------------------
    if ext == ".java":
        _handle_java(file_content, file_instance, file_name, technology)
        return

    # ---------------------- KOTLIN / GROOVY SOURCE -----------------------
    if ext in {".kt", ".kts"}:
        _mark_generic("Kotlin Source", file_path.name, "Kotlin File", file_content, file_instance, technology)
        return
    if ext == ".groovy":
        _mark_generic("Groovy Source", file_path.name, "Groovy File", file_content, file_instance, technology)
        return

    # ------------------------------ TESTS --------------------------------
    if _is_test(lower_path):
        _mark_generic("Tests", file_path.name, "Testing File", file_content, file_instance, technology)
        return

    # --------------------------- OTHER ----------------------------------
    _mark_generic("Other", file_path.name, "Non categorized file", file_content, file_instance, technology)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return (
        "/src/test/" in path or "\\src\\test\\" in path or path.endswith("Test.java") or path.endswith("Tests.java")
    )


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
# Java source detailed parsing
# ---------------------------------------------------------------------------

def _handle_java(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()
    found_any = False

    # Detect controller endpoints
    found_any |= _extract_endpoints(lines, file_instance, technology)

    # Detect entity classes
    found_any |= _extract_entity(lines, file_instance, technology)

    # Detect repositories & services
    found_any |= _extract_repositories(lines, file_instance, technology)
    found_any |= _extract_services(lines, file_instance, technology)

    if not found_any:
        _mark_generic("Module", file_name, "Java File (no specific Spring artefact)", file_content, file_instance, technology)


def _extract_endpoints(lines, file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)
    found = False
    for idx, line in enumerate(lines, start=1):
        match = SPRING_MAPPING_RE.search(line)
        if match:
            path = match.group("path")
            name = f"Endpoint {path}"
            _create_or_update(component_type=comp_type, name=name, line=line, idx=idx, file_instance=file_instance, description=f"Route {path}")
            found = True
    return found


def _extract_entity(lines, file_instance, technology):
    comp_type_entity, _ = ComponentType.objects.get_or_create(name="Entities", technology=technology)
    found = False
    for idx, line in enumerate(lines, start=1):
        if JPA_ENTITY_RE.search(line):
            # Next class line contains the class name
            for j in range(idx, min(idx + 5, len(lines))):
                cl_match = CLASS_RE.search(lines[j])
                if cl_match:
                    name = cl_match.group("name")
                    _create_or_update(comp_type_entity, name, lines[j], j + 1, file_instance, "JPA Entity")
                    found = True
                    break
    return found


def _extract_repositories(lines, file_instance, technology):
    comp_type_repo, _ = ComponentType.objects.get_or_create(name="Repositories", technology=technology)
    found = False
    for idx, line in enumerate(lines, start=1):
        repo_match = REPO_RE.search(line)
        if repo_match:
            name = repo_match.group("name")
            _create_or_update(comp_type_repo, name, line, idx, file_instance, "Spring Data Repository")
            found = True
    return found


def _extract_services(lines, file_instance, technology):
    comp_type_service, _ = ComponentType.objects.get_or_create(name="Services", technology=technology)
    found = False
    class_name = None
    for idx, line in enumerate(lines, start=1):
        if SERVICE_RE.search(line):
            # find class declaration within next few lines
            for j in range(idx, min(idx + 5, len(lines))):
                cl_match = CLASS_RE.search(lines[j])
                if cl_match:
                    class_name = cl_match.group("name")
                    _create_or_update(comp_type_service, class_name, lines[j], j + 1, file_instance, "Service class")
                    found = True
                    break
    return found


def _create_or_update(component_type, name, line, idx, file_instance, description):
    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=component_type,
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
