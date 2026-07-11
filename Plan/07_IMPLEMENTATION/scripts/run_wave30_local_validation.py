#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_FILES = (
    "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json",
    "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json",
    "Plan/08_SCHEMAS/wave30_audio_qa_report.schema.json",
)
SCRIPT_FILES = (
    "Plan/07_IMPLEMENTATION/scripts/compile_wave30_audio_event_manifest.py",
    "Plan/07_IMPLEMENTATION/scripts/score_wave30_audio_qa.py",
    "Plan/07_IMPLEMENTATION/scripts/run_wave30_local_validation.py",
)
WRAPPER_FILE = "Plan/07_IMPLEMENTATION/templates/powershell/Run-Wave30-AudioGenerationValidation.ps1"
STRICT_TEST_FILE = "Plan/Instructions/QA/Scripts/test_wave30_audio_pipeline_strict.py"


def _resolve_repo_root(root_arg: str) -> Path:
    root = Path(root_arg).resolve()
    if (root / "Plan").is_dir():
        return root
    if root.name == "Plan" and root.is_dir():
        return root.parent
    raise ValueError(f"unable to resolve repository root from --root={root}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    try:
        repo_root = _resolve_repo_root(args.root)
    except Exception as exc:
        print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2, sort_keys=True))
        return 1

    errors: list[str] = []
    checks: dict[str, Any] = {"schemas": [], "scripts": [], "wrapper": {}, "focused_test": {}}

    for rel in SCHEMA_FILES:
        path = repo_root / rel
        result: dict[str, Any] = {"path": str(path), "exists": path.exists()}
        if not path.exists():
            errors.append(f"missing schema: {rel}")
            checks["schemas"].append(result)
            continue
        try:
            schema = _load_json(path)
            Draft202012Validator.check_schema(schema)
            result["draft202012_valid"] = True
        except Exception as exc:
            result["draft202012_valid"] = False
            result["error"] = str(exc)
            errors.append(f"schema invalid: {rel}: {exc}")
        checks["schemas"].append(result)

    for rel in SCRIPT_FILES:
        path = repo_root / rel
        result = {"path": str(path), "exists": path.exists()}
        if not path.exists():
            errors.append(f"missing script: {rel}")
            checks["scripts"].append(result)
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            result["python_compile"] = "pass"
        except Exception as exc:
            result["python_compile"] = f"fail: {exc}"
            errors.append(f"script compile failed: {rel}: {exc}")
        checks["scripts"].append(result)

    wrapper_path = repo_root / WRAPPER_FILE
    checks["wrapper"] = {"path": str(wrapper_path), "exists": wrapper_path.exists()}
    if not wrapper_path.exists():
        errors.append(f"missing wrapper: {WRAPPER_FILE}")
    else:
        wrapper_text = wrapper_path.read_text(encoding="utf-8")
        if "run_wave30_local_validation.py" not in wrapper_text:
            errors.append("wrapper does not reference run_wave30_local_validation.py")
            checks["wrapper"]["references_validator"] = False
        else:
            checks["wrapper"]["references_validator"] = True

    test_path = repo_root / STRICT_TEST_FILE
    checks["focused_test"] = {"path": str(test_path), "exists": test_path.exists()}
    if not test_path.exists():
        errors.append(f"missing focused strict test: {STRICT_TEST_FILE}")
    else:
        try:
            py_compile.compile(str(test_path), doraise=True)
            checks["focused_test"]["python_compile"] = "pass"
        except Exception as exc:
            checks["focused_test"]["python_compile"] = f"fail: {exc}"
            errors.append(f"focused strict test compile failed: {STRICT_TEST_FILE}: {exc}")

    report = {
        "status": "pass" if not errors else "fail",
        "mode": "offline_local_validation",
        "checked_root": str(repo_root),
        "checks": checks,
        "error_count": len(errors),
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
