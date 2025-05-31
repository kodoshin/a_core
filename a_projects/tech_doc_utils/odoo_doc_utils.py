import ast
import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###########################################################################
# Odoo FILE DOCUMENTATION UTILITIES – v2                                  #
# ----------------------------------------------------------------------- #
#  * Detects Models, Controllers, Views (XML), QWeb templates, Manifests,  #
#    Access CSV, i18n .po, data fixtures, tests, assets & configs.         #
###########################################################################

_MODEL_BASES = {"Model", "TransientModel", "AbstractModel"}


@transaction.atomic
def odoo_document_file(file_content: str, file_instance, file_name: str, technology):
    """Route a file to the adequate Odoo parser / classifier."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_name = file_name.lower()

    # ------------------------- PYTHON SOURCE -----------------------------
    if ext == ".py":
        if _is_test_file(lower_name):
            _mark_generic(
                comp_type_name="Tests",
                component_name=file_path.name,
                description="Fichier de tests Odoo",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        elif file_path.name in {"__manifest__.py", "__openerp__.py"}:
            _mark_generic(
                comp_type_name="Manifest",
                component_name=file_path.name,
                description="Fichier manifeste du module Odoo",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_python_file(file_content, file_instance, file_name, technology)
        return

    # ---------------------------- XML FILES ------------------------------
    if ext == ".xml":
        if "views" in lower_name or _has_ir_ui_view(file_content):
            _mark_generic(
                comp_type_name="Views",
                component_name=file_path.name,
                description="Définition de vue (ir.ui.view)",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            return
        if "template" in lower_name or "qweb" in lower_name or "<template" in file_content:
            _mark_generic(
                comp_type_name="QWeb Templates",
                component_name=file_path.name,
                description="Template QWeb / website",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            return
        # Fallback as Data Fixture
        _mark_generic(
            comp_type_name="Data Fixtures",
            component_name=file_path.name,
            description="Fichier XML de données",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------- CSV (access / fixtures) -----------------------
    if ext == ".csv":
        if file_path.name == "ir.model.access.csv" or "access" in lower_name:
            comp_type = "Security"
            desc = "Droits d'accès (ir.model.access.csv)"
        else:
            comp_type = "Data Fixtures"
            desc = "Fichier CSV de données"
        _mark_generic(
            comp_type_name=comp_type,
            component_name=file_path.name,
            description=desc,
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ------------------------------ .PO ----------------------------------
    if ext == ".po":
        _mark_generic(
            comp_type_name="I18n",
            component_name=file_path.name,
            description="Fichier de traduction (.po)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # -------------------------- JS / SCSS -------------------------------
    if ext in {".js", ".ts", ".scss", ".css"}:
        _mark_generic(
            comp_type_name="Assets",
            component_name=file_path.name,
            description="Asset statique JS/CSS/TS",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # -------------------------- OTHER STATIC -----------------------------
    if any(seg in lower_name for seg in ("/static/", "\\static\\")):
        comp_type = "Static Files"
    else:
        comp_type = "Other"

    _mark_generic(
        comp_type_name=comp_type,
        component_name=file_path.name,
        description=f"Fichier hors catégorie principale ({comp_type})",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    return (
        "/tests/" in path or "\\tests\\" in path or path.endswith("_test.py") or path.startswith("test_")
    )


def _mark_generic(*, comp_type_name: str, component_name: str, description: str, file_content: str, file_instance, technology):
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
# PYTHON ANALYSIS                                                           #
# ---------------------------------------------------------------------------

def _document_python_file(file_content: str, file_instance, file_name: str, technology):
    try:
        tree = ast.parse(file_content)
    except SyntaxError as exc:
        _mark_generic(
            comp_type_name="Python File",
            component_name=file_name,
            description=f"Python file not parsable: {exc}",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    lines = file_content.splitlines()

    _extract_models(tree, lines, file_instance, technology)
    _extract_controllers(lines, file_instance, technology)

    if not Component.objects.filter(file=file_instance).exists():
        _mark_generic(
            comp_type_name="Module",
            component_name=file_name,
            description="Fichier Python (aucun modèle / contrôleur détecté)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


# -------------------------- Model extraction ----------------------------

def _extract_models(tree: ast.AST, lines: list[str], file_instance, technology):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if any(
                (
                    isinstance(base, ast.Attribute) and base.attr in _MODEL_BASES
                )
                or (
                    isinstance(base, ast.Name) and base.id in _MODEL_BASES
                )
                for base in node.bases
            ):
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                source = "\n".join(lines[start_line - 1 : end_line])
                comp_type, _ = ComponentType.objects.get_or_create(name="Models", technology=technology)
                component, created = Component.objects.get_or_create(
                    file=file_instance,
                    component_type=comp_type,
                    name=node.name,
                    defaults={
                        "content": source,
                        "start_line": start_line,
                        "end_line": end_line,
                        "description": "Modèle Odoo",
                    },
                )
                if not created:
                    component.content = source
                    component.start_line = start_line
                    component.end_line = end_line
                    component.save()


# ------------------------- Controller extraction ------------------------

_route_regex = re.compile(r"@.*?\.route\(\s*['\"](?P<path>[^'\"]+)['\"]", re.I)


def _extract_controllers(lines: list[str], file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="Controllers", technology=technology)
    for idx, line in enumerate(lines, start=1):
        match = _route_regex.search(line)
        if match:
            path = match.group("path")
            name = f"Route {path}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": f"Contrôleur route {path}",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.save()


# -------------------------- XML helper ----------------------------------

def _has_ir_ui_view(xml_text: str) -> bool:
    return "<record" in xml_text and "ir.ui.view" in xml_text
