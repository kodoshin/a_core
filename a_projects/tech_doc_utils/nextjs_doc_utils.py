import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

###############################################################################
# Next.js FILE DOCUMENTATION UTILITIES – v2                                   #
# --------------------------------------------------------------------------- #
#  * Detects pages & routes (Pages Router / App Router API / server actions)   #
#  * Parses React components, server components (.server.tsx) & client ones    #
#  * Handles MD/MDX content, config files, env, tests, stories, styles, assets #
###############################################################################

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
FUNC_COMPONENT_RE = re.compile(r"(?:export\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(")
ARROW_COMPONENT_RE = re.compile(r"(?:export\s+)?(?:const|let|var)\s+([A-Z][A-Za-z0-9_]*)\s*=\s*\(?.*?=>")
SERVER_ACTION_RE = re.compile(r"export\s+async\s+function\s+(?P<name>[A-Za-z0-9_]+)\s*\(")

# Next.js API route signature (Pages router)
API_ROUTE_RE = re.compile(r"export\s+default\s+async\s+function\s+handler|export\s+async\s+function\s+handler")

@transaction.atomic
def nextjs_document_file(file_content: str, file_instance, file_name: str, technology):
    """Main router for Next.js files."""
    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_path = file_name.lower()

    # ---------------------- CODE: JS / TS / TSX / JSX ---------------------
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        if _is_test(lower_path):
            _mark_generic(
                comp_type="Tests",
                component_name=file_path.name,
                description="Testing file (Jest / Vitest / Playwright)",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        elif _is_story(lower_path):
            _mark_generic(
                comp_type="Stories",
                component_name=file_path.name,
                description="Storybook story",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        elif _is_api_route(lower_path, file_content):
            _mark_generic(
                comp_type="API Route",
                component_name=file_path.name,
                description="Next.js API route",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_next_code(file_content, file_instance, file_name, technology)
        return

    # ------------------------------ MD / MDX ------------------------------
    if ext in {".md", ".mdx"}:
        _mark_generic(
            comp_type="MDX Page" if "pages" in lower_path or "app" in lower_path else "Docs",
            component_name=file_path.name,
            description="MD/MDX content",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- STYLES ----------------------------------
    if ext in {".css", ".scss", ".sass", ".less"} or ".module." in lower_path:
        _mark_generic(
            comp_type="Styling Module" if ".module." in lower_path else "Styling",
            component_name=file_path.name,
            description="Style sheet",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # --------------------------- CONFIG ----------------------------------
    if file_path.name in {"next.config.js", "next.config.mjs", "next.config.ts"}:
        _mark_generic(
            comp_type="Build Config",
            component_name=file_path.name,
            description="Next.js configuration file",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return
    if file_path.name.startswith(".env"):
        _mark_generic(
            comp_type="Env Config",
            component_name=file_path.name,
            description="Environment variables",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ------------------------- STATIC / ASSETS ---------------------------
    if any(seg in lower_path for seg in ("/public/", "\\public\\")) or ext in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".avif"}:
        comp_type = "Assets"
    else:
        comp_type = "Other"

    _mark_generic(
        comp_type=comp_type,
        component_name=file_path.name,
        description=f"File categorised as {comp_type}",
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------------------------------------------------------------
# Helper classification functions
# ---------------------------------------------------------------------------

def _is_test(path: str) -> bool:
    return "/__tests__/" in path or path.endswith(tuple([f"{suffix}{ext}" for suffix in (".test", ".spec") for ext in (".js", ".ts", ".tsx", ".jsx")]))


def _is_story(path: str) -> bool:
    return ".stories." in path or path.endswith((".story.tsx", ".story.jsx"))


def _is_api_route(path: str, content: str) -> bool:
    if "/pages/api/" in path or "\\pages\\api\\" in path:
        return True
    if "/app/api/" in path or "\\app\\api\\" in path:
        return True
    return bool(API_ROUTE_RE.search(content))


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
# Detailed parsing for components & server actions
# ---------------------------------------------------------------------------

def _document_next_code(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()
    detected = False

    detected |= _extract_pattern(lines, FUNC_COMPONENT_RE, "Components", file_instance, technology, "Functional component")
    detected |= _extract_pattern(lines, ARROW_COMPONENT_RE, "Components", file_instance, technology, "Arrow component")

    # Server actions (app router)
    _extract_pattern(lines, SERVER_ACTION_RE, "Server Actions", file_instance, technology, "Server action (Edge/Lambda)")

    if not detected:
        _mark_generic(
            comp_type="Module",
            component_name=file_name,
            description="JS/TS module – no component detected",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


# Generic extraction helper

def _extract_pattern(lines, regex, comp_type_name, file_instance, technology, description):
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)
    found = False
    for idx, line in enumerate(lines, start=1):
        for match in regex.finditer(line):
            name = match.group(1) if match.groups() else line.strip()
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
