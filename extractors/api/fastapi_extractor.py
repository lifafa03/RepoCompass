"""FastAPI route extractor — parses Python files for FastAPI route definitions."""
import ast
import re
from pathlib import Path
from typing import Optional

from app.schemas import APIEndpoint, APIMap, EvidenceRef, HandlerLocation


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _find_decorator_routes(tree: ast.AST, source_lines: list[str], file_path: str) -> list[APIEndpoint]:
    endpoints = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            route_info = _parse_route_decorator(decorator)
            if route_info is None:
                continue
            method, route = route_info
            handler_name = node.name
            line_start = node.lineno
            line_end = getattr(node, "end_lineno", line_start)
            dec_line = decorator.lineno
            snippet_end = min(dec_line + 2, len(source_lines))
            endpoints.append(APIEndpoint(
                method=method.upper(),
                route=route,
                handler_name=handler_name,
                handler_location=HandlerLocation(
                    file_path=file_path,
                    line_start=line_start,
                    line_end=line_end,
                ),
                evidence=[EvidenceRef(
                    file_path=file_path,
                    line_start=dec_line,
                    line_end=snippet_end,
                    snippet_id=f"fastapi_route_{file_path}_{dec_line}",
                )],
                confidence="high",
                uncertainty_note=None,
            ))
    return endpoints


def _parse_route_decorator(decorator: ast.expr) -> Optional[tuple[str, str]]:
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if isinstance(func, ast.Attribute):
        method = func.attr.lower()
        if method not in HTTP_METHODS:
            return None
        if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
            return (method, decorator.args[0].value)
        for kw in decorator.keywords:
            if kw.arg == "path" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return (method, kw.value.value)
    return None


def _find_add_api_route(tree: ast.AST, source_lines: list[str], file_path: str) -> list[APIEndpoint]:
    endpoints = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_api_route"):
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        route = node.args[0].value
        handler_name = None
        if len(node.args) > 1 and isinstance(node.args[1], ast.Name):
            handler_name = node.args[1].id
        methods = ["GET"]
        for kw in node.keywords:
            if kw.arg == "methods" and isinstance(kw.value, ast.List):
                methods = [
                    elt.value.upper()
                    for elt in kw.value.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                ]
        line_no = node.lineno if hasattr(node, "lineno") else 0
        for method in methods:
            endpoints.append(APIEndpoint(
                method=method, route=route, handler_name=handler_name,
                handler_location=None,
                evidence=[EvidenceRef(file_path=file_path, line_start=line_no, line_end=line_no + 1, snippet_id=f"fastapi_route_{file_path}_{line_no}")],
                confidence="medium",
                uncertainty_note="Route added via add_api_route; handler location inferred",
            ))
    return endpoints


def extract_fastapi_routes(file_path: Path, repo_root: Path) -> list[APIEndpoint]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    rel_path = str(file_path.relative_to(repo_root))
    source_lines = source.split("\n")
    endpoints = []
    endpoints.extend(_find_decorator_routes(tree, source_lines, rel_path))
    endpoints.extend(_find_add_api_route(tree, source_lines, rel_path))
    return endpoints


def extract_api_map(repo_root: Path, source_files: list[Path]) -> APIMap:
    all_endpoints = []
    for fp in source_files:
        if fp.suffix == ".py":
            endpoints = extract_fastapi_routes(fp, repo_root)
            all_endpoints.extend(endpoints)
    return APIMap(framework="fastapi", endpoints=all_endpoints)
