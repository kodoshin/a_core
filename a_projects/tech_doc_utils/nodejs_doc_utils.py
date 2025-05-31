import json
import re
from pathlib import Path

from django.db import transaction
from a_projects.models import Component, ComponentType

############################################################################
# Node.js / TypeScript FILE DOCUMENTATION UTILITIES – v3                   #
# ---------------------------------------------------------------------- #
# * Detects common artefacts in modern JS/TS back‑ends: Express / Router,  #
#   NestJS decorators, Fastify, Koa‑Router, Hapi, routing‑controllers /     #
#   tsoa decorators, Serverless Framework configs & Cloud Functions.       #
# * Extracts REST endpoints & TS interfaces, classifies tests, configs,     #
#   GraphQL schemas, static assets, serverless.yml, *.function.ts files.    #
############################################################################

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

# ---------------------------------------------------------------------------
# Regex catalogue – single‑line patterns
# ---------------------------------------------------------------------------
EXPRESS_ENDPOINT_RE = re.compile(
    r"(?P<prefix>app|router)\.\s*(?P<method>get|post|put|delete|patch|options|head)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]",
    re.I,
)

FASTIFY_ENDPOINT_RE = re.compile(
    r"fastify\.\s*(?P<method>get|post|put|delete|patch|options|head)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]",
    re.I,
)

KOA_ROUTER_RE = re.compile(
    r"router\.\s*(?P<method>get|post|put|delete|patch|options|head)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]",
    re.I,
)

# NestJS + routing‑controllers + tsoa (decorator style)
DECORATOR_RE = re.compile(
    r"@(?P<method>Get|Post|Put|Delete|Patch|Options|Head)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]",
    re.I,
)

# ---------------------------------------------------------------------------
# Multi‑line patterns (DOTALL)
# ---------------------------------------------------------------------------
FASTIFY_ROUTE_BLOCK_RE = re.compile(
    r"fastify\.route\s*\(\s*\{[^}]*?method\s*:\s*['\"](?P<method>[A-Za-z]+)['\"]\s*,[^}]*?(?:url|path)\s*:\s*['\"](?P<path>[^'\"]+)['\"]",
    re.I | re.S,
)

HAPI_ROUTE_BLOCK_RE = re.compile(
    r"server\.route\s*\(\s*\{[^}]*?method\s*:\s*['\"]?(?P<method>[A-Za-z]+)['\"]?\s*,[^}]*?path\s*:\s*['\"](?P<path>[^'\"]+)['\"]",
    re.I | re.S,
)

# TypeScript interfaces
TS_INTERFACE_RE = re.compile(r"export\s+interface\s+(?P<iface>[A-Za-z0-9_]+)")

# Cloud Function filename heuristic
CLOUD_FN_EXTS = {".ts", ".js"}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
@transaction.atomic
def node_document_file(file_content: str, file_instance, file_name: str, technology):  # noqa: C901
    """Classify and document *file_name* belonging to a Node.js / TS project."""

    file_path = Path(file_name)
    ext = file_path.suffix.lower()
    lower_name = file_name.lower()

    # ---------------------------- SERVERLESS CONFIG ------------------------
    if file_path.name in {"serverless.yml", "serverless.yaml"}:
        _handle_serverless_yaml(file_content, file_instance, technology)
        return

    # ---------------------------- CODE FILES ------------------------------
    if ext in {".js", ".ts", ".mjs", ".cjs"}:
        # Cloud Function (*.function.ts / *.function.js)
        if file_path.name.endswith(".function.ts") or file_path.name.endswith(".function.js"):
            _create_component(
                comp_type_name="Cloud Functions",
                component_name=file_path.name,
                description="Serverless Cloud Function source",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            # Still parse for endpoints / interfaces in case the function exposes one
            _document_js_file(file_content, file_instance, file_name, technology)
            return

        # Unit / integration tests
        if _is_test_file(lower_name):
            _create_component(
                comp_type_name="Tests",
                component_name=file_path.name,
                description="Testing file (Jest / Mocha / Vitest)",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
        else:
            _document_js_file(file_content, file_instance, file_name, technology)
        return

    # --------------------------- JSON CONFIG ------------------------------
    if ext == ".json":
        if file_path.name == "package.json":
            _handle_package_json(file_content, file_instance, technology)
            return
        if file_path.name in {"tsconfig.json", "jsconfig.json"}:
            _create_component(
                comp_type_name="Build Config",
                component_name=file_path.name,
                description="TypeScript / JavaScript config",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            return
        if file_path.name.endswith("schema.json") or "schema" in lower_name:
            _create_component(
                comp_type_name="JSON Schema",
                component_name=file_path.name,
                description="JSON Schema",
                file_content=file_content,
                file_instance=file_instance,
                technology=technology,
            )
            return

    # -------------------------- YAML / ENV --------------------------------
    if ext in {".yaml", ".yml"} and "docker-compose" in lower_name:
        _create_component(
            comp_type_name="Container Config",
            component_name=file_path.name,
            description="docker-compose file",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    if ext in {".env", ".ini", ".toml"} or file_path.name == ".env":
        _create_component(
            comp_type_name="Env Config",
            component_name=file_path.name,
            description="Environment variables / configuration",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ---------------------------- GRAPHQL ---------------------------------
    if ext in {".graphql", ".gql"}:
        _create_component(
            comp_type_name="GraphQL Schema",
            component_name=file_path.name,
            description="GraphQL schema definition",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ----------------------------- STYLING --------------------------------
    if ext in {".css", ".scss", ".sass"}:
        _create_component(
            comp_type_name="Styling",
            component_name=file_path.name,
            description="Styling file",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )
        return

    # ------------------------ STATIC / MEDIA / OTHER ----------------------
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
# JS / TS SOURCE ANALYSIS
# ---------------------------------------------------------------------------

def _document_js_file(file_content: str, file_instance, file_name: str, technology):
    """Scan a JS/TS source for REST endpoints & TS interfaces."""

    lines = file_content.splitlines()

    # --- line‑based endpoint patterns -------------------------------------
    for regex in (EXPRESS_ENDPOINT_RE, FASTIFY_ENDPOINT_RE, KOA_ROUTER_RE):
        _extract_endpoints_lines(lines, regex, file_instance, technology)

    # --- decorator pattern (NestJS / routing‑controllers / tsoa) ----------
    _extract_endpoints_lines(lines, DECORATOR_RE, file_instance, technology, decorator=True)

    # --- multi‑line blocks (Fastify route & Hapi server.route) ------------
    for regex in (FASTIFY_ROUTE_BLOCK_RE, HAPI_ROUTE_BLOCK_RE):
        _extract_endpoints_block(file_content, regex, file_instance, technology)

    # --- TS interfaces ----------------------------------------------------
    _extract_ts_interfaces(lines, TS_INTERFACE_RE, file_instance, technology)

    # Fallback: if nothing captured yet
    if not Component.objects.filter(file=file_instance).exists():
        _create_component(
            comp_type_name="Module",
            component_name=file_name,
            description="JS / TS File (no endpoint / interface detected)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


# ---------------------------------------------------------------------------
# Endpoint extraction helpers
# ---------------------------------------------------------------------------

def _extract_endpoints_lines(lines, regex, file_instance, technology, decorator: bool = False):
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)

    for idx, line in enumerate(lines, start=1):
        match = regex.search(line)
        if match:
            method = match.group("method").upper()
            path = match.group("path")
            name = f"{method} {path}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": f"Endpoint {method} {path}",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.description = f"Endpoint {method} {path}"
                component.save()


def _extract_endpoints_block(text: str, regex, file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)

    for match in regex.finditer(text):
        method = match.group("method").upper()
        path = match.group("path")
        start_line = text[: match.start()].count("\n") + 1
        end_line = start_line + match.group(0).count("\n")
        name = f"{method} {path}"
        component, created = Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
            defaults={
                "content": match.group(0)[:4000],
                "start_line": start_line,
                "end_line": end_line,
                "description": f"Endpoint {method} {path}",
            },
        )
        if not created:
            component.content = match.group(0)[:4000]
            component.start_line = start_line
            component.end_line = end_line
            component.description = f"Endpoint {method} {path}"
            component.save()





# ---------------------------------------------------------------------------
# serverless.yml parsing (very light‑weight heuristic)
# ---------------------------------------------------------------------------

def _handle_serverless_yaml(content: str, file_instance, technology):
    """Store a *Serverless Config* component and try to extract HTTP events."""
    _create_component(
        comp_type_name="Serverless Config",
        component_name="serverless.yml",
        description="Serverless Framework configuration",
        file_content=content,
        file_instance=file_instance,
        technology=technology,
    )

    # Attempt to capture 'path' & 'method' under http events
    http_event_re = re.compile(
        r"method:\s*(?P<method>\w+)\s*\n[^\n]*path:\s*(?P<path>[A-Za-z0-9_/\-{}]+)", re.I,
    )
    for match in http_event_re.finditer(content):
        method = match.group("method").upper()
        path = match.group("path")
        start_line = content[: match.start()].count("\n") + 1
        end_line = start_line + match.group(0).count("\n")
        comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)
        name = f"{method} {path} (serverless)"
        Component.objects.get_or_create(
            file=file_instance,
            component_type=comp_type,
            name=name,
            defaults={
                "content": match.group(0),
                "start_line": start_line,
                "end_line": end_line,
                "description": f"Serverless endpoint {method} {path}",
            },
        )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    return (
        "/tests/" in path
        or "\\tests\\" in path
        or path.endswith((".spec.js", ".spec.ts", ".test.js", ".test.ts"))
    )


def _create_component(*, comp_type_name: str, component_name: str, description: str, file_content: str, file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name=comp_type_name, technology=technology)

    component, created = Component.objects.get_or_create(
        file=file_instance,
        component_type=comp_type,
        name=component_name,
        defaults={
            "content": file_content if len(file_content) < 4000 else file_content[:4000] + "…",
            "start_line": 1,
            "end_line": len(file_content.splitlines()),
            "description": description,
        },
    )
    if not created:
        component.content = file_content if len(file_content) < 4000 else file_content[:4000] + "…"
        component.end_line = len(file_content.splitlines())
        component.description = description
        component.save()


# ---------------------------------------------------------------------------
# Specific handlers                                                         #
# ---------------------------------------------------------------------------

def _handle_package_json(file_content: str, file_instance, technology):
    try:
        data = json.loads(file_content)
        pkg_name = data.get("name", "package.json")
        scripts = data.get("scripts", {})
        description = f"package.json – scripts: {', '.join(scripts.keys())}" if scripts else "package.json"
    except json.JSONDecodeError:
        pkg_name = "package.json (invalid)"
        description = "invalid package.json"

    _create_component(
        comp_type_name="Build Config",
        component_name=pkg_name,
        description=description,
        file_content=file_content,
        file_instance=file_instance,
        technology=technology,
    )


# ---------------------- JS / TS code analysis ----------------------------

def _document_js_file(file_content: str, file_instance, file_name: str, technology):
    lines = file_content.splitlines()

    # Endpoint extraction (Express / Router)
    endpoint_regex = re.compile(
        r"(?P<prefix>app|router)\.\s*(?P<method>get|post|put|delete|patch|options|head)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]",
        re.I,
    )
    _extract_endpoints(lines, endpoint_regex, file_instance, technology)

    # NestJS decorator style @Get('path')
    decorator_regex = re.compile(
        r"@(?P<method>Get|Post|Put|Delete|Patch|Options|Head)\s*\(\s*['\"](?P<path>[^'\"]+)['\"]",
        re.I,
    )
    _extract_endpoints(lines, decorator_regex, file_instance, technology, decorator=True)

    # TypeScript interfaces
    interface_regex = re.compile(r"export\s+interface\s+(?P<iface>[A-Za-z0-9_]+)")
    _extract_ts_interfaces(lines, interface_regex, file_instance, technology)

    # Fallback
    if not Component.objects.filter(file=file_instance).exists():
        _create_component(
            comp_type_name="Module",
            component_name=file_name,
            description="JS / TS File (no endpoint / interface detected)",
            file_content=file_content,
            file_instance=file_instance,
            technology=technology,
        )


def _extract_endpoints(lines, regex, file_instance, technology, decorator=False):
    comp_type, _ = ComponentType.objects.get_or_create(name="Endpoints", technology=technology)

    for idx, line in enumerate(lines, start=1):
        match = regex.search(line)
        if match:
            method = match.group("method").upper()
            path = match.group("path")
            name = f"{method} {path}"
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=name,
                defaults={
                    "content": line if decorator else "\n".join(lines[max(idx - 1, 0) : idx + 4]),
                    "start_line": idx,
                    "end_line": idx,
                    "description": f"Endpoint {method} {path}",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.save()


# ---------------------------------------------------------------------------
# TS interface extraction
# ---------------------------------------------------------------------------

def _extract_ts_interfaces(lines, regex, file_instance, technology):
    comp_type, _ = ComponentType.objects.get_or_create(name="TS Interfaces", technology=technology)

    for idx, line in enumerate(lines, start=1):
        match = regex.search(line)
        if match:
            iface_name = match.group("iface")
            component, created = Component.objects.get_or_create(
                file=file_instance,
                component_type=comp_type,
                name=iface_name,
                defaults={
                    "content": line,
                    "start_line": idx,
                    "end_line": idx,
                    "description": "TypeScript Interface",
                },
            )
            if not created:
                component.content = line
                component.start_line = idx
                component.end_line = idx
                component.save()