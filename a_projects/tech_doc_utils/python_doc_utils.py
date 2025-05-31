import ast
import json
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

############################################################################
# Generic Python FILE DOCUMENTATION UTILITIES – v2                          #
# ------------------------------------------------------------------------ #
#  * Covers pure‑Python projects (scripts, libs, CLI, data science).        #
#  * Detects classes, functions, dataclasses, Pydantic models, tests.       #
#  * Recognises build/config files (pyproject.toml, requirements.txt, etc.) #
#  * Classifies Jupyter notebooks, stubs, env files, static assets.         #
############################################################################

# ---------------------------------------------------------------------------
# Helper regex / constants
# ---------------------------------------------------------------------------

PY_BUILD_FILES = {
    "setup.py",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "Pipfile.lock",
}

TEST_SUFFIXES = ("_test.py", "test_", "tests/")


@transaction.atomic
def python_document_file(file_content: str, file_instance, file_name: str, technology):
    """Routes a file to the right parser / classifier for generic Python projects."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ------------------------------ NOTEBOOKS -----------------------------
    if ext == ".ipynb":
        _mark_generic(
            comp_type="Notebook",
            component_name=file_path.name,
            description="Jupyter notebook",
            file_content=file_content[:1000] + "..." if len(file_content) > 1000 else file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ---------------------------- BUILD / DEP ----------------------------
    if file_path.name in PY_BUILD_FILES:
        _mark_generic(
            comp_type="Build Config",
            component_name=file_path.name,
            description="Fichier de dépendances / configuration",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ---------------------------- ENV / CFG ------------------------------
    if ext in {".env", ".ini", ".toml"} or file_path.name.startswith(".env"):
        _mark_generic(
            comp_type="Config",
            component_name=file_path.name,
            description="Fichier de configuration / variables d'environnement",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- STUB FILES ------------------------------
    if ext == ".pyi":
        _mark_generic(
            comp_type="Stubs",
            component_name=file_path.name,
            description="Type stub (.pyi)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ------------------------------ PYTHON -------------------------------
    if ext == ".py":
        if _is_test(lower_path):
            _mark_generic(
                comp_type="Tests",
                component_name=file_path.name,
                description="Fichier de tests (pytest/unittest)",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_python_source(file_content, file_instance, file_name, technology)
        return

    # --------------------------- OTHER FILES -----------------------------
    if any(seg in lower_path for seg in ("/static/", "\\static\\", "/assets/", "\\assets\\")):
        comp_type = "Static Files"
    else:
        comp_type = "Other"
    _mark_generic(
        comp_type=comp_type,
        component_name=file_path.name,
        description=f"Fichier classé {comp_type}",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return (
        "/tests/" in path or "\\tests\\" in path or path.endswith("_test.py") or path.startswith("test_")
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
# Python source parsing
# ---------------------------------------------------------------------------

def _document_python_source(file_content: str, file_instance, file_name: str, technology):
    try:
        tree = ast.parse(file_content)
    except SyntaxError as exc:
        _mark_generic(
            comp_type="Python File",
            component_name=file_name,
            description=f"Fichier Python non analysable: {exc}",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    lines = file_content.splitlines()
    found = False

    # Classes (including dataclass & pydantic)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            _store_class(node, lines, file_instance, technology)
            found = True
        elif isinstance(node, ast.FunctionDef):
            # Top‑level function (exclude methods by checking parent via lineno)
            if node.col_offset == 0:
                _store_function(node, lines, file_instance, technology)
                found = True

    if not found:
        _mark_generic(
            comp_type="Module",
            component_name=file_name,
            description="Module Python (aucune classe/fonction détectée)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


def _store_class(node: ast.ClassDef, lines, file_instance, technology):
    # Determine specific class type
    if any(
        (isinstance(dec, ast.Name) and dec.id == "dataclass") or (isinstance(dec, ast.Attribute) and dec.attr == "dataclass")
        for dec in node.decorator_list
    ):
        comp_name = "Data Classes"
        desc = "Dataclass"
    elif any(
        (isinstance(base, ast.Name) and base.id == "BaseModel") or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
        for base in node.bases
    ):
        comp_name = "Pydantic Models"
        desc = "Pydantic model"
    else:
        comp_name = "Classes"
        desc = "Class"

    comp_type, _ = ComponentType.objects.get_or_create(name=comp_name, technology=technology)
    start_line = node.lineno
    end_line = getattr(node, "end_lineno", start_line)
    source = "\n".join(lines[start_line - 1 : end_line])
    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type,
        name=node.name,
        defaults={
            "content": source,
            "start_line": start_line,
            "end_line": end_line,
            "description": desc,
        },
    )
    if not created:
        component.content = source
        component.start_line = start_line
        component.end_line = end_line
        component.description = desc
        component.save()


def _store_function(node: ast.FunctionDef, lines, file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="Functions", technology=technology)
    start_line = node.lineno
    end_line = getattr(node, "end_lineno", start_line)
    source = "\n".join(lines[start_line - 1 : end_line])
    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type,
        name=node.name,
        defaults={
            "content": source,
            "start_line": start_line,
            "end_line": end_line,
            "description": "Function",
        },
    )
    if not created:
        component.content = source
        component.start_line = start_line
        component.end_line = end_line
        component.save()
