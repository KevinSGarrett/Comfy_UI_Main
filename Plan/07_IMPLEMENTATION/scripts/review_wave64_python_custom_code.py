from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


RISK_IMPORT_ROOTS = {"requests", "urllib", "socket", "subprocess", "pickle", "cloudpickle", "dill"}
RISK_CALLS = {"exec", "eval", "compile", "open", "os.system", "os.popen", "torch.load", "torch.jit.load"}


def _name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assignment_has_effect(node: ast.Assign | ast.AnnAssign) -> bool:
    value = node.value
    if value is None:
        return False
    return any(isinstance(child, (ast.Call, ast.Await, ast.Yield, ast.YieldFrom)) for child in ast.walk(value))


def _resolve_target(root: Path, filename: str) -> Path:
    candidate = root / filename
    if candidate.is_symlink():
        raise ValueError(f"symlink target forbidden: {filename}")
    target = candidate.resolve(strict=True)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ValueError(f"target escapes review root: {filename}") from error
    if not target.is_file():
        raise ValueError(f"target is not a regular file: {filename}")
    return target


def review_file(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    calls: list[dict[str, Any]] = []
    definitions: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Call):
            name = _name(node.func)
            calls.append({"name": name, "line": node.lineno})
            if name in RISK_CALLS:
                findings.append({"kind": "risk_call", "name": name, "line": node.lineno})
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append({"kind": type(node).__name__, "name": node.name, "line": node.lineno})
    for name in imports:
        if name.split(".", 1)[0] in RISK_IMPORT_ROOTS:
            findings.append({"kind": "risk_import", "name": name})
    top_level_executable: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef)):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and not _assignment_has_effect(node):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        top_level_executable.append({"kind": type(node).__name__, "line": node.lineno})
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "imports": sorted(imports),
        "calls": calls,
        "definitions": definitions,
        "risk_findings": findings,
        "top_level_executable": top_level_executable,
    }


def review(root: Path, filenames: list[str]) -> dict[str, Any]:
    root = root.resolve()
    files = [review_file(_resolve_target(root, name)) for name in filenames]
    return {
        "schema_version": "wave64.python_custom_code_review.v1",
        "root": str(root),
        "files": files,
        "risk_findings": [dict(file=item["file"], **finding) for item in files for finding in item["risk_findings"]],
        "top_level_executable": [dict(file=item["file"], **finding) for item in files for finding in item["top_level_executable"]],
        "authority": {"static_ast_review": True, "import": False, "execution": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--file", action="append", required=True)
    args = parser.parse_args()
    print(json.dumps(review(args.root, args.file), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
