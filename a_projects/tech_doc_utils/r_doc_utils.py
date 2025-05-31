import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# R FILE DOCUMENTATION UTILITIES – v2                                         #
# --------------------------------------------------------------------------- #
#  * Detects R scripts, functions, R6 classes, Shiny apps, tests.             #
#  * Handles DESCRIPTION / renv.lock / packrat.lock build‑config files.        #
#  * Classifies RMarkdown, data files, assets.                                #
###############################################################################

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
FUNCTION_RE = re.compile(r"^(?P<name>[A-Za-z0-9_\.]+)\s*<-\s*function\s*\(")
R6_RE = re.compile(r"R6Class\s*\(\s*['\"](?P<name>[A-Za-z0-9_]+)['\"]")

@transaction.atomic
def r_document_file(file_content: str, file_instance, file_name: str, technology):
    """Main router for R ecosystem files."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # -------------------------- BUILD / DEP ---------------------------------
    if file_path.name == "description":
        _mark_generic(
            comp_type="Build Config",
            component_name=file_path.name,
            description="DESCRIPTION (metadata package R)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    if file_path.name in {"renv.lock", "packrat.lock"}:
        _mark_generic(
            comp_type="Dependencies",
            component_name=file_path.name,
            description="Lockfile renv / packrat",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    if ext == ".rproj":
        _mark_generic(
            comp_type="Project Config",
            component_name=file_path.name,
            description="RStudio project file",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- R MARKDOWN ---------------------------------
    if ext in {".rmd", ".qmd"}:
        _mark_generic(
            comp_type="RMarkdown",
            component_name=file_path.name,
            description="R Markdown / Quarto document",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- R SCRIPTS ----------------------------------
    if ext == ".r":
        # Tests (testthat)
        if _is_test(lower_path):
            _mark_generic(
                comp_type="Tests",
                component_name=file_path.name,
                description="Test file (testthat)",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_r_script(file_content, file_instance, file_name, technology)
        return

    # ----------------------------- DATA ------------------------------------
    if ext in {".csv", ".tsv", ".rds", ".rdata"}:
        _mark_generic(
            comp_type="Data",
            component_name=file_path.name,
            description="Data file",
            file_content="",
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- STATIC / OTHER ----------------------------
    if any(seg in lower_path for seg in ("/www/", "\\www\\", "/static/", "\\static\\")):
        comp_type = "Assets"
    else:
        comp_type = "Other"
    _mark_generic(
        comp_type=comp_type,
        component_name=file_path.name,
        description=f"Fichier classé {comp_type}",
        file_content=file_content if len(file_content) < 2000 else file_content[:2000] + "...",
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return (
        "/tests/" in path or "\\tests\\" in path or path.startswith("test_") or path.endswith("_test.r")
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
# R script parsing
# ---------------------------------------------------------------------------

def _document_r_script(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()
    detected = False

    detected |= _extract_pattern(lines, FUNCTION_RE, "Functions", file_instance, technology, "Function definition")
    detected |= _extract_pattern(lines, R6_RE, "R6 Classes", file_instance, technology, "R6 class")

    # Shiny app detection (app.R, ui.R, server.R)
    if file_name.lower() in {"app.r", "ui.r", "server.r"}:
        _mark_generic(
            comp_type="Shiny App",
            component_name=file_name,
            description="Shiny app component",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        detected = True

    if not detected:
        _mark_generic(
            comp_type="Module",
            component_name=file_name,
            description="R script (aucune fonction/classe détectée)",
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
