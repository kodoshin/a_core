import ast
import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

##########################################################################################
#Django FILE DOCUMENTATION UTILITIES – v3                                             #
#--------------------------------------                                                  #
#* Adds support for:                                                                     #
#  • **Nested `urlpatterns`** using `include()` (captures prefix + module)               #
#  • **Class‑based views* in any app/module (detects subclasses of `django.views.*`)     #
#  • **Django Rest Framework** serializers & viewsets                              #
#  • **Jinja2 templates**, management commands, and data **fixtures**                    #
#The parser is conservative – it never imports modules, it only uses AST &               #
#regex heuristics so it is safe against untrusted code.                                  #
##########################################################################################

###############################################################################
# Regex patterns                                                              #
###############################################################################
#   path("api/", include("myapp.api_urls"))
NESTED_INCLUDE_RE = re.compile(
    r"path\(\s*[\'\"](?P<route>[^\'\"]+)[\'\"]\s*,\s*include\(\s*[\'\"](?P<module>[^\'\"]+)[\'\"]",
)
# Catch bare include("foo.urls") in *urlpatterns* lists that use url() or re_path()
INCLUDE_ONLY_RE = re.compile(r"include\(\s*[\'\"](?P<module>[^\'\"]+)[\'\"]")

###############################################################################
# Public entry point                                                       #
###############################################################################


@transaction.atomic
def dj_document_file(file_content: str, file_instance, file_name: str, technology):
    """Classify **file_content** as part of a Django project and create `Component`s.
    The router covers Python sources, templates, static assets, fixtures, etc.
    """

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower().replace("\\", "/")  # normalise slashes

    # --------------------------- Jinja2 / HTML templates --------------------
    if ext in {".html", ".jinja", ".jinja2"}:
        _mark_generic(
            comp_type="Templates",
            component_name=file_path.name,
            description="Django / Jinja2 template",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- CSS Styling  --------------------
    if ext in {".css", ".scss", ".less", ".sass", ".stylus", ".styl"}:
        _mark_generic(
            comp_type="Style",
            component_name=file_path.name,
            description="Styling File",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- Data fixtures -----------------------------
    if ext in {".json", ".yaml", ".yml", ".csv"} and "/fixtures/" in lower_path:
        _mark_generic(
            comp_type="Fixtures",
            component_name=file_path.name,
            description="Django data fixture",
            file_content=file_content if len(file_content) < 4000 else file_content[:4000] + "…",
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- Static / media -----------------------------
    if any(seg in lower_path for seg in ("/static/", "/assets/")):
        comp_type = "Static Files"
        _mark_generic(comp_type, file_path.name, comp_type, file_content, file_instance, technology)
        return
    if "/media/" in lower_path:
        comp_type = "Media Files"
        _mark_generic(comp_type, file_path.name, comp_type, file_content, file_instance, technology)
        return

    # ----------------------------- PYTHON -----------------------------------
    if ext == ".py":
        if "/management/commands/" in lower_path:
            # Always tag the file itself as a Management Command artefact – details parsed below
            _mark_generic(
                comp_type="Management Commands",
                component_name=file_path.name,
                description="Django management command module",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        _document_python_source(file_content, file_instance, file_name, technology)
        return

    # -------------------------- OTHER / fallback ----------------------------
    _mark_generic(
        comp_type="Other",
        component_name=file_path.name,
        description="Unclassified file",
        file_content=file_content if len(file_content) < 4000 else file_content[:4000] + "…",
        file_instance=file_instance,
        technology=technology,
    )


###############################################################################
# Helper functions                                                             #
###############################################################################

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


###############################################################################
# Detailed Python (.py) parsing                                                #
###############################################################################

def _document_python_source(text: str, file_instance, file_name: str, technology):
    """Parse a Python module looking for Django artefacts."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        _mark_generic(
            comp_type="Python File",
            component_name=file_name,
            description=f"Python file not parsable: {exc}",
            file_content=text,
            file_instance=file_instance,
            technology=technology,
        )
        return

    lines = text.splitlines()

    # ---------------------------------------------------------------------
    # 1. URL patterns – collect path()/re_path()/url() & include()
    # ---------------------------------------------------------------------
    if file_name.endswith("urls.py"):
        _extract_urlpatterns(lines, file_instance, technology)

    # ---------------------------------------------------------------------
    # 2. Class & function discovery
    # ---------------------------------------------------------------------
    _extract_classes_and_funcs(tree, lines, file_instance, technology, file_name)

    # If nothing stored yet, fallback
    if not Component.objects.filter(file=file_instance).exists():
        _mark_generic(
            comp_type="Module",
            component_name=file_name,
            description="Python module (no Django artefact detected)",
            file_content=text,
            file_instance=file_instance,
            technology=technology,
        )


# ---------------------------------------------------------------------------
# URL extraction helpers                                                      #
# ---------------------------------------------------------------------------

def _extract_urlpatterns(lines: list[str], file_instance, technology):
    comp_url, _ = ComponentType.objects.get_or_create(name="URLs", technology=technology)
    comp_include, _ = ComponentType.objects.get_or_create(name="URL Includes", technology=technology)

    for idx, line in enumerate(lines, start=1):
        m = NESTED_INCLUDE_RE.search(line)
        if m:
            route = m.group("route")
            mod = m.group("module")
            name = f"Include {route} → {mod}"
            _store_component(comp_include, name, line, idx, file_instance, f"includes {mod} under {route}")
            continue
        inc_only = INCLUDE_ONLY_RE.search(line)
        if inc_only:
            mod = inc_only.group("module")
            name = f"Include {mod}"
            _store_component(comp_include, name, line, idx, file_instance, f"includes {mod}")
            continue
        # direct path('api/', views.api)
        path_match = re.search(r"path\(\s*[\'\"](?P<route>[^\'\"]+)[\'\"]", line)
        if path_match:
            route = path_match.group("route")
            name = f"Path {route}"
            _store_component(comp_url, name, line, idx, file_instance, f"Route {route}")


def _store_component(comp_type, name, line, idx, file_instance, description):
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


# ---------------------------------------------------------------------------
# Class & function extraction                                                 #
# ---------------------------------------------------------------------------

_VIEW_BASES = {
    "View",
    "TemplateView",
    "ListView",
    "DetailView",
    "CreateView",
    "UpdateView",
    "DeleteView",
}
_DRF_SERIALIZER_BASES = {"Serializer", "ModelSerializer"}
_DRF_VIEWSET_BASES = {"ViewSet", "ModelViewSet", "ReadOnlyModelViewSet"}


def _extract_classes_and_funcs(tree: ast.AST, lines: list[str], file_instance, technology, file_name: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            _handle_class(node, lines, file_instance, technology, file_name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _handle_function(node, lines, file_instance, technology, file_name)


def _handle_class(node: ast.ClassDef, lines: list[str], file_instance, technology, file_name: str):
    bases = {base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "") for base in node.bases}

    # Determine component type
    if bases & _VIEW_BASES:
        comp = "Views"
        desc = "Class‑based view"
    elif bases & _DRF_SERIALIZER_BASES:
        comp = "Serializers"
        desc = "DRF serializer"
    elif bases & _DRF_VIEWSET_BASES:
        comp = "Viewsets"
        desc = "DRF viewset"
    elif "Model" in bases or file_name.endswith("models.py"):
        comp = "Models"
        desc = "Model"
    elif "/management/commands/" in file_name.replace("\\", "/") and "BaseCommand" in bases:
        comp = "Management Commands"
        desc = "Management command"
    else:
        comp = "Python Classes"
        desc = "Class definition"

    _store_ast_component(node, lines, file_instance, technology, comp, desc)


def _handle_function(node: ast.FunctionDef, lines: list[str], file_instance, technology, file_name: str):
    # Only store module‑level functions (skip methods)
    if node.col_offset != 0:
        return

    if file_name.endswith("views.py"):
        comp = "Views"
        desc = "Function‑based view"
    else:
        comp = "Functions"
        desc = "Function"

    _store_ast_component(node, lines, file_instance, technology, comp, desc)


def _store_ast_component(node, lines, file_instance, technology, comp_type_name: str, description: str):
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
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
            "description": description,
        },
    )
    if not created:
        component.content = source
        component.start_line = start_line
        component.end_line = end_line
        component.description = description
        component.save()
