import ast
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# Flask FILE DOCUMENTATION UTILITIES – v3                                     #
# --------------------------------------------------------------------------- #
#  * Detects endpoints declared with:                                          #
#       - @app.route("/...")  (+ methods=[...])                               #
#       - @blueprint.route("/...")                                            #
#       - @app.<http-method>("/...") (get / post / put / delete / patch …)    #
#       - Multiple decorators on the same function                             #
#  * Supports Marshmallow schemas, templates, static files, configs, tests.    #
#  * Fixes previous bug where AST Constant / Str attributes were swapped.      #
###############################################################################

_HTTP_METHODS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "options",
    "head",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


@transaction.atomic
def fl_document_file(file_content: str, file_instance, file_name: str, technology):
    """Route *file_content* to the right Flask parser / classifier."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_name = file_name.lower()

    # ----------------------------- PYTHON SOURCE ----------------------------
    if ext == ".py":
        if _is_test_file(lower_name):
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

    # ---------------------------- TEMPLATES ---------------------------------
    if ext in {".html", ".htm", ".jinja", ".j2", ".jinja2"}:
        _create_component(
            comp_type_name="Templates",
            component_name=file_path.name,
            description="Jinja/HTML Template",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ---------------------- CONFIGURATION / DEPENDENCIES --------------------
    CONFIG_FILES = {"settings.py", "config.py", ".env", "requirements.txt", "pyproject.toml"}
    if ext in {".env", ".ini", ".toml"} or file_path.name in CONFIG_FILES:
        _create_component(
            comp_type_name="Config",
            component_name=file_path.name,
            description="Config / Dependencies File",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ---------------------------- STYLES ------------------------------------
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

    # ------------------------ STATIC / MEDIA / OTHER ------------------------
    if any(seg in lower_name for seg in ("/static/", "\\static\\", "/assets/", "\\assets\\")):
        comp_type = "Static Files"
    elif any(seg in lower_name for seg in ("/media/", "\\media\\")):
        comp_type = "Media Files"
    else:
        comp_type = "Other"

    _create_component(
        comp_type_name=comp_type,
        component_name=file_path.name,
        description=f"Classified as {comp_type}",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helpers – generic
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    return (
        "/tests/" in path
        or "\\tests\\" in path
        or path.endswith("_test.py")
        or path.startswith("test_")
    )


def _create_component(*, comp_type_name: str, component_name: str, description: str, file_content: str, file_instance, technology):
    """Create or update a Component entry, idempotently."""
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
        component.end_line = len(file_content.splitlines())
        component.description = description
        component.save()


# ---------------------------------------------------------------------------
# Python-specific parsing (Flask source)
# ---------------------------------------------------------------------------

def _document_python_file(file_content: str, file_instance, file_name: str, technology):
    """Parse a Flask Python source file for endpoints & Marshmallow schemas."""
    try:
        tree = ast.parse(file_content)
    except SyntaxError as exc:
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

    # --- Endpoints ---------------------------------------------------------
    _extract_flask_endpoints(tree, lines, file_instance, technology)

    # --- Marshmallow Schemas ----------------------------------------------
    _extract_marshmallow_schemas(tree, lines, file_instance, technology)

    # Fallback if nothing stored
    if not Component.objects.filter(file=file_instance).exists():
        _create_component(
            comp_type_name="Module",
            component_name=file_name,
            description="Python File (no class/endpoint detected)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


# ---------------------------------------------------------------------------
# Endpoint extraction utilities
# ---------------------------------------------------------------------------

def _literal_str(node: ast.AST):
    """Return Python str literal value if *node* is a literal string."""
    if isinstance(node, ast.Str):
        return node.s
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _first_str_arg(call: ast.Call):
    for arg in call.args:
        val = _literal_str(arg)
        if val is not None:
            return val
    # Some devs use named arg ``rule="/foo"`` or ``path="/foo"``
    for name in ("rule", "path"):
        kw = next((kw for kw in call.keywords if kw.arg == name), None)
        if kw:
            val = _literal_str(kw.value)
            if val is not None:
                return val
    return "<dynamic>"


def _extract_methods_kw(call: ast.Call):
    kw = next((kw for kw in call.keywords if kw.arg == "methods"), None)
    if kw and isinstance(kw.value, (ast.List, ast.Tuple)):
        methods: list[str] = []
        for elt in kw.value.elts:
            lit = _literal_str(elt)
            if lit:
                methods.append(lit.upper())
        return methods
    return []


def _parse_endpoint_decorator(deco: ast.AST):
    """Return (path, [methods]) if *deco* is a Flask route decorator."""
    if not isinstance(deco, ast.Call):
        return None

    # Dotted attribute like ``app.route`` or ``bp.get``
    if isinstance(deco.func, ast.Attribute):
        attr = deco.func.attr.lower()
        if attr == "route":
            path = _first_str_arg(deco)
            methods = _extract_methods_kw(deco) or ["GET"]
            return path, methods
        if attr in _HTTP_METHODS:
            path = _first_str_arg(deco)
            return path, [attr.upper()]
    return None


def _extract_flask_endpoints(tree: ast.AST, lines: list[str], file_instance, technology):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.decorator_list:
            for deco in node.decorator_list:
                result = _parse_endpoint_decorator(deco)
                if result:
                    route_path, http_methods = result
                    _store_endpoint(node, route_path, http_methods, lines, file_instance, technology)
                    # Do *not* break – a function can legitimately have several decorators


def _store_endpoint(func_node: ast.AST, route_path: str, http_methods: list[str], lines: list[str], file_instance, technology):
    start_line = func_node.lineno
    end_line = getattr(func_node, "end_lineno", start_line)
    source = "\n".join(lines[start_line - 1 : end_line])
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)

    for method in http_methods:
        name = f"{method} {route_path}"
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
            defaults={
                "content": source,
                "start_line": start_line,
                "end_line": end_line,
                "description": f"Endpoint {method} {route_path}",
            },
        )
        if not created:
            component.content = source
            component.start_line = start_line
            component.end_line = end_line
            component.description = f"Endpoint {method} {route_path}"
            component.save()


# ---------------------------------------------------------------------------
# Marshmallow schema extraction
# ---------------------------------------------------------------------------

def _extract_marshmallow_schemas(tree: ast.AST, lines: list[str], file_instance, technology):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if any(
                (isinstance(base, ast.Name) and base.id == "Schema")
                or (isinstance(base, ast.Attribute) and base.attr == "Schema")
                for base in node.bases
            ):
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                source = "\n".join(lines[start_line - 1 : end_line])
                comp_type, _ = ComponentType.objects.get_or_create(name="Marshmallow Schemas", technology=technology)
                component, created = Component.objects.get_or_create(
                    file=file_instance,
                    component_type=comp_type,
                    name=node.name,
                    defaults={
                        "content": source,
                        "start_line": start_line,
                        "end_line": end_line,
                        "description": "Marshmallow schema",
                    },
                )
                if not created:
                    component.content = source
                    component.start_line = start_line
                    component.end_line = end_line
                    component.description = "Marshmallow schema"
                    component.save()
