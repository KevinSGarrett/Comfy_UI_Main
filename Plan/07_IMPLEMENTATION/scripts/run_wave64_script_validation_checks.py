from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import tempfile
import tokenize
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Wave64"
OUT_FILE = OUT_DIR / f"SCRIPT_VALIDATION_CHECKS_{STAMP}.json"
PS_PARSE_OUT = OUT_DIR / f"SCRIPT_VALIDATION_POWERSHELL_PARSE_{STAMP}.json"

EXCLUDED_PARTS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def display_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def in_scope(path: Path) -> bool:
    return not any(part in EXCLUDED_PARTS for part in path.parts)


def list_files(extensions: set[str]) -> list[Path]:
    return sorted(
        path
        for path in PLAN_ROOT.rglob("*")
        if path.is_file() and in_scope(path) and path.suffix.lower() in extensions
    )


def bytecode_inventory(root: Path) -> dict[str, dict[str, int | str]]:
    inventory: dict[str, dict[str, int | str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".pyc", ".pyo"} and "__pycache__" not in path.parts:
            continue
        stat = path.stat()
        inventory[path.resolve().relative_to(root.resolve()).as_posix()] = {
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return inventory


def parse_python_file(path: Path) -> None:
    with tokenize.open(path) as handle:
        source = handle.read()
    compile(
        source,
        str(path),
        "exec",
        flags=ast.PyCF_ONLY_AST,
        dont_inherit=True,
    )


def validate_python(files: list[Path], bytecode_root: Path = PLAN_ROOT) -> dict[str, object]:
    bytecode_before = bytecode_inventory(bytecode_root)
    errors = []
    for path in files:
        try:
            parse_python_file(path)
        except Exception as exc:
            errors.append({"path": display_path(path), "error": f"{type(exc).__name__}: {exc}"})
    bytecode_after = bytecode_inventory(bytecode_root)
    bytecode_paths = sorted(set(bytecode_before) | set(bytecode_after))
    bytecode_changes = [
        path
        for path in bytecode_paths
        if bytecode_before.get(path) != bytecode_after.get(path)
    ]
    return {
        "file_count": len(files),
        "parse_error_count": len(errors),
        "errors": errors[:100],
        "parser_method": "compile_ast_only_with_tokenize_open",
        "bytecode_inventory": {
            "before_count": len(bytecode_before),
            "after_count": len(bytecode_after),
            "changed_count": len(bytecode_changes),
            "changed_paths": bytecode_changes[:100],
            "unchanged": not bytecode_changes,
        },
    }


def validate_powershell() -> dict[str, object]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ps_script = f"""
$ErrorActionPreference = "Stop"
$root = "{str(PLAN_ROOT)}"
$out = "{str(PS_PARSE_OUT)}"
$extensions = @(".ps1", ".psm1", ".psd1")
$files = Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction Stop | Where-Object {{ $extensions -contains $_.Extension.ToLowerInvariant() }}
$errors = @()
foreach ($file in $files) {{
  $tokens = $null
  $parseErrors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
  if ($parseErrors -and $parseErrors.Count -gt 0) {{
    foreach ($error in $parseErrors) {{
      $errors += [ordered]@{{
        path = $file.FullName
        message = $error.Message
        line = $error.Extent.StartLineNumber
        column = $error.Extent.StartColumnNumber
      }}
    }}
  }}
}}
$record = [ordered]@{{
  file_count = @($files).Count
  parse_error_count = @($errors).Count
  errors = @($errors | Select-Object -First 100)
}}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding UTF8
$record | ConvertTo-Json -Depth 8
"""
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as handle:
        handle.write(ps_script)
        temp_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(temp_path),
            ],
            text=True,
            capture_output=True,
            timeout=180,
        )
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass

    if PS_PARSE_OUT.exists():
        record = json.loads(PS_PARSE_OUT.read_text(encoding="utf-8-sig"))
    else:
        record = {
            "file_count": 0,
            "parse_error_count": 1,
            "errors": [{"path": str(PS_PARSE_OUT), "message": "PowerShell parser evidence was not written."}],
        }
    record["process"] = {
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
        "parser_evidence": rel(PS_PARSE_OUT) if PS_PARSE_OUT.exists() else str(PS_PARSE_OUT),
    }
    if completed.returncode != 0:
        record["parse_error_count"] = int(record.get("parse_error_count", 0)) + 1
        record.setdefault("errors", []).append({
            "path": str(temp_path),
            "message": f"PowerShell parser process exited {completed.returncode}",
        })
    return record


def main() -> int:
    py_files = list_files({".py"})
    ps_files = list_files({".ps1", ".psm1", ".psd1"})
    python_result = validate_python(py_files)
    powershell_result = validate_powershell()
    parser_pass = (
        python_result["parse_error_count"] == 0
        and python_result["bytecode_inventory"]["unchanged"] is True
        and powershell_result["parse_error_count"] == 0
    )

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"SCRIPT_VALIDATION_CHECKS_{STAMP}",
        "created_iso": ISO_TS,
        "project_root": str(PROJECT_ROOT),
        "plan_root": str(PLAN_ROOT),
        "python": sys.version,
        "scope": {
            "python_glob": "Plan/**/*.py",
            "powershell_glob": "Plan/**/*.{ps1,psm1,psd1}",
            "excluded_parts": sorted(EXCLUDED_PARTS),
            "helpers_executed": False,
            "parser_only": True,
            "python_parser_method": python_result["parser_method"],
            "python_bytecode_written": not python_result["bytecode_inventory"]["unchanged"],
            "ec2_contacted": False,
            "aws_contacted": False,
            "comfyui_contacted": False,
            "runtime_mutation": False,
        },
        "parser_check": {
            "pass": parser_pass,
            "python": python_result,
            "powershell": powershell_result,
        },
        "local_smoke": {
            "pass": parser_pass,
            "method": "Parser-only smoke: Python compile(..., PyCF_ONLY_AST) and PowerShell Language.Parser.ParseFile completed without executing project helper bodies or writing Python bytecode.",
        },
        "no_live_side_effect_default": {
            "pass": python_result["bytecode_inventory"]["unchanged"] is True,
            "no_ec2": True,
            "no_aws": True,
            "no_comfyui": True,
            "no_helper_execution": True,
            "no_python_bytecode_write": python_result["bytecode_inventory"]["unchanged"],
        },
        "evidence_output_json": {
            "pass": True,
            "path": rel(OUT_FILE),
        },
        "structured_report": {
            "pass": parser_pass,
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": rel(OUT_FILE),
        "pass": parser_pass,
        "python_files": python_result["file_count"],
        "python_parse_errors": python_result["parse_error_count"],
        "python_bytecode_changes": python_result["bytecode_inventory"]["changed_count"],
        "powershell_files": powershell_result["file_count"],
        "powershell_parse_errors": powershell_result["parse_error_count"],
    }, indent=2))
    return 0 if parser_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
