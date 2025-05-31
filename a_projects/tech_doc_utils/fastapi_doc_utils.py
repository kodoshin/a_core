import ast
import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType


###########################################################################
# FastAPI FILE DOCUMENTATION UTILITIES – v2                               #
# ----------------------------------------------------------------------- #
#  * Detects and catalogues the main artefacts found in modern FastAPI    #
#    projects, covering code, specs, templates, tests, configs & assets.  #
#  * Creates (or updates) `Component` rows linked to the uploaded `File`,  #
#    using (and auto‑creating) `ComponentType` rows bound to the           #
#    Technology instance representing FastAPI.                            #
###########################################################################


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
@transaction.atomic
def fa_document_file(file_content: str, file_instance, file_name: str, technology):
    """High‑level router that dispatches to the right parser / categoriser.

    Args:
        file_content: Complete textual content of the file.
        file_instance: File ORM instance (ForeignKey for Component).
        file_name: Name or repository‑relative path (string).
        technology: Technology ORM instance representing *FastAPI*.
    """

    # Normalise helpers
    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_name = file_name.lower()

    # ------------------------- PYTHON SOURCE -----------------------------
    if ext == ".py":
        # Treat tests separately – store as *Tests* instead of generic parsing
        if _is_test_file(file_name):
            _create_component(
                comp_type_name="Tests",
                component_name=file_path.name,
                description="(pytest) Test File",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_python_file(file_content, file_instance, file_name, technology)
        return

    # --------------------- OPENAPI / JSON SCHEMA -------------------------
    if ext in {".yaml", ".yml", ".json"}:
        if any(tok in lower_name for tok in ("openapi", "swagger")):
            _create_component(
                comp_type_name="OpenAPI Spec",
                component_name=file_path.name,
                description="OpenAPI / Swagger Specification",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            return
        if ext == ".json" and (lower_name.endswith("schema.json") or "schema" in lower_name):
            _create_component(
                comp_type_name="JSON Schema",
                component_name=file_path.name,
                description="Schema JSON File",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            return

    # ------------------------- TEMPLATES ---------------------------------
    if ext in {".html", ".htm", ".jinja", ".jinja2"}:
        _create_component(
            comp_type_name="Templates",
            component_name=file_path.name,
            description="Jinja/HTML Template",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- STYLING ---------------------------------
    if ext in {".css", ".scss", ".sass"}:
        _create_component(
            comp_type_name="Styling",
            component_name=file_path.name,
            description="Styling File",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ----------------------- CONFIGURATION / ENV -------------------------
    if ext in {".env", ".ini", ".toml"} or file_path.name in {"pyproject.toml", "requirements.txt"}:  # noqa: W503
        _create_component(
            comp_type_name="Config",
            component_name=file_path.name,
            description="Config/Dependencies Files",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- STATIC / MEDIA --------------------------
    # Heuristics based on folder name (static/, media/, assets/)
    if any(seg in lower_name for seg in ("/static/", "\\static\\", "/assets/", "\\assets\\")):
        comp_type_name = "Static Files"
    elif any(seg in lower_name for seg in ("/media/", "\\media\\")):
        comp_type_name = "Media Files"
    else:
        comp_type_name = "Other"

    _create_component(
        comp_type_name=comp_type_name,
        component_name=file_path.name,
        description=f"Out of Principal Categories ({comp_type_name})",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    """Return *True* if the path seems to represent a pytest test file."""
    lower = path.lower()
    return (
        any(p in lower for p in ("/tests/", "\\tests\\"))
        or lower.endswith("_test.py")
        or lower.startswith("test_")
    )


def _create_component(
    *,
    comp_type_name: str,
    component_name: str,
    description: str,
    file_content: str,
    file_instance,
    technology,
):
    """Wrap `Component.objects.get_or_create` boilerplate with sane defaults."""
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)

    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type,
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
        component.description = description
        component.end_line = len(file_content.splitlines())
        component.save()


# ---------------------------------------------------------------------------
# Detailed Python (.py) parsing for FastAPI projects
# ---------------------------------------------------------------------------

def _document_python_file(file_content: str, file_instance, file_name: str, technology):
    """Parse a FastAPI Python source looking for:
      * Endpoint function definitions decorated with `@app.<method>` or `@router.<method>`
      * Pydantic models (classes subclassing `BaseModel`)
      * Other classes & utility functions (fallback)
    """
    try:
        tree = ast.parse(file_content)
    except SyntaxError as exc:
        # Store un‑parsable file as a generic *Python File*
        _create_component(
            comp_type_name="Python File",
            component_name=file_name,
            description=f"Python file not parsable: {exc}",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    lines = file_content.splitlines()

    # --- Endpoint extraction ------------------------------------------------
    _extract_endpoints(tree, lines, file_instance, technology)

    # --- Pydantic models ----------------------------------------------------
    _extract_pydantic_models(tree, lines, file_instance, technology)

    # --- Fallback – mark file as *Module* if nothing detected ---------------
    # Check if at least one Component linked to this file already exists
    if not Component.objects.filter(file=file_instance).exists():
        _create_component(
            comp_type_name="Module",
            component_name=file_name,
            description="Python File (no class/endpoint detected)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


# ------------------------- Endpoint detection ----------------------------

_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


def _extract_endpoints(tree: ast.AST, lines: list[str], file_instance, technology):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.decorator_list:
            for deco in node.decorator_list:
                endpoint_info = _parse_endpoint_decorator(deco)
                if endpoint_info:
                    http_method, route_path = endpoint_info
                    _store_endpoint(
                        func_node=node,
                        http_method=http_method,
                        route_path=route_path,
                        lines=lines,
                        file_instance=file_instance,
                        technology=technology,
                    )
                    break  # Stop after first matching decorator


def _parse_endpoint_decorator(deco: ast.AST):
    """Return (method, path) if *deco* looks like `@app.get('/path')`."""
    if isinstance(deco, ast.Call):
        # Handle dotted attribute like app.get or router.post
        if isinstance(deco.func, ast.Attribute) and deco.func.attr in _METHODS:
            method = deco.func.attr.upper()
            # Extract first arg if str literal
            if deco.args and isinstance(deco.args[0], (ast.Constant, ast.Str)):
                path_val = deco.args[0].s if isinstance(deco.args[0], ast.Constant) else deco.args[0].value
            else:
                path_val = "<dynamic>"
            return method, path_val
    return None


def _store_endpoint(*, func_node, http_method: str, route_path: str, lines: list[str], file_instance, technology):
    start_line = func_node.lineno
    end_line = getattr(func_node, "end_lineno", start_line)
    source = "\n".join(lines[start_line - 1 : end_line])
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)
    name = f"{http_method} {route_path}"
    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type,
        name=name,
        defaults={
            "content": source,
            "start_line": start_line,
            "end_line": end_line,
            "description": f"Endpoint {http_method} {route_path}",
        },
    )
    if not created:
        component.content = source
        component.description = f"Endpoint {http_method} {route_path}"
        component.start_line = start_line
        component.end_line = end_line
        component.save()


# --------------------- Pydantic model extraction -------------------------


def _extract_pydantic_models(tree: ast.AST, lines: list[str], file_instance, technology):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Simple heuristic: check for BaseModel in bases
            if any(
                (
                    isinstance(base, ast.Name) and base.id == "BaseModel"
                )
                or (
                    isinstance(base, ast.Attribute) and base.attr == "BaseModel"
                )
                for base in node.bases
            ):
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                source = "\n".join(lines[start_line - 1 : end_line])
                comp_type, _ = ComponentType.objects.get_or_create(name="Pydantic Models", technology=technology)
                component, created = Component.objects.get_or_create(
                    file=file_instance,
                    component_type=comp_type,
                    name=node.name,
                    defaults={
                        "content": source,
                        "start_line": start_line,
                        "end_line": end_line,
                        "description": "Pydantic model",
                    },
                )
                if not created:
                    component.content = source
                    component.start_line = start_line
                    component.end_line = end_line
                    component.save()
