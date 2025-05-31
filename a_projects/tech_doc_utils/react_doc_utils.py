import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

############################################################################
# React FILE DOCUMENTATION UTILITIES – v2                                 #
# ---------------------------------------------------------------------- #
#  * Detects React components (functional, arrow, class) & hooks          #
#  * Identifies Storybook stories, tests, styling modules, configs, assets#
############################################################################


# ----------------------------------------------------------------------------
# Regex patterns
# ----------------------------------------------------------------------------

FUNC_COMPONENT_RE = re.compile(r"(?:export\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(")
ARROW_COMPONENT_RE = re.compile(r"(?:export\s+)?(?:const|let|var)\s+([A-Z][A-Za-z0-9_]*)\s*=\s*\(?.*?=>")
CLASS_COMPONENT_RE = re.compile(r"class\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+React\.(?:PureComponent|Component)")
HOOK_RE = re.compile(r"(?:export\s+)?function\s+(use[A-Z][A-Za-z0-9_]*)\s*\(")


@transaction.atomic
def react_document_file(file_content: str, file_instance, file_name: str, technology):
    """Main router for React project files."""
    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_name = file_name.lower()

    # -------------------------------- CODE ----------------------------------
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        if _is_test_file(lower_name):
            _mark_generic(
                comp_type="Tests",
                component_name=file_path.name,
                description="Testing File (Jest / Vitest)",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        elif _is_story_file(lower_name):
            _mark_generic(
                comp_type="Stories",
                component_name=file_path.name,
                description="Storybook story",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_react_code(file_content, file_instance, file_name, technology)
        return

    # ----------------------------- STYLES -----------------------------------
    if ext in {".css", ".scss", ".sass", ".less"} or lower_name.endswith(".module.css") or lower_name.endswith(".module.scss"):
        _mark_generic(
            comp_type="Styling Module" if ".module." in lower_name else "Styling",
            component_name=file_path.name,
            description="Styling File",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ------------------------------ CONFIG ----------------------------------
    if file_path.name in {"vite.config.js", "vite.config.ts", "webpack.config.js", ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".prettierrc", ".prettierrc.js"}:
        _mark_generic(
            comp_type="Build Config",
            component_name=file_path.name,
            description="Config tooling file (Vite/Webpack/ESLint/Prettier)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- MARKDOWN / MDX -----------------------------
    if ext in {".md", ".mdx"}:
        _mark_generic(
            comp_type="Docs",
            component_name=file_path.name,
            description="Markdown/MDX Documentation",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ----------------------- STATIC / ASSETS -------------------------------
    if any(seg in lower_name for seg in ("/static/", "/public/", "\\static\\", "\\public\\")):
        comp_type = "Static Files"
    elif any(lower_name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp")):
        comp_type = "Assets"
    else:
        comp_type = "Other"

    _mark_generic(
        comp_type=comp_type,
        component_name=file_path.name,
        description=f"Out of Principal Categories ({comp_type})",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    return any(
        path.endswith(suffix)
        for suffix in (
            ".test.js",
            ".test.jsx",
            ".test.ts",
            ".test.tsx",
            ".spec.js",
            ".spec.jsx",
            ".spec.ts",
            ".spec.tsx",
        )
    ) or "/__tests__/" in path or "\\__tests__\\" in path


def _is_story_file(path: str) -> bool:
    return ".stories." in path or path.endswith(".story.tsx") or path.endswith(".story.jsx")


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


# ----------------------------------------------------------------------------
# React code parsing
# ----------------------------------------------------------------------------

def _document_react_code(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()
    detected = False

    # Functional components
    detected |= _extract_pattern(lines, FUNC_COMPONENT_RE, "Components", file_instance, technology, desc="Functional component")

    # Arrow components
    detected |= _extract_pattern(lines, ARROW_COMPONENT_RE, "Components", file_instance, technology, desc="Arrow component")

    # Class components
    detected |= _extract_pattern(lines, CLASS_COMPONENT_RE, "Components", file_instance, technology, desc="Class component")

    # Custom hooks
    _extract_pattern(lines, HOOK_RE, "Hooks", file_instance, technology, desc="Custom hook")

    if not detected:
        _mark_generic(
            comp_type="Module",
            component_name=file_name,
            description="JS/TS File (no components detected)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


def _extract_pattern(lines, regex, comp_type_name, file_instance, technology, *, desc):
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    found_any = False
    for idx, line in enumerate(lines, start=1):
        for match in regex.finditer(line):
            name = match.group(1)
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": desc,
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.description = desc
                component.save()
            found_any = True
    return found_any
