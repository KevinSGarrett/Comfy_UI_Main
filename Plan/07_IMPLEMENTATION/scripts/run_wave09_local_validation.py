#!/usr/bin/env python3
"""Run local Wave09 static validation for environment registries and runtime-boundary records."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    "08_SCHEMAS/environment_bible.schema.json",
    "08_SCHEMAS/environment_registry.schema.json",
    "08_SCHEMAS/room_profile.schema.json",
    "08_SCHEMAS/lighting_rig.schema.json",
    "08_SCHEMAS/prop_registry.schema.json",
    "08_SCHEMAS/material_surface_profile.schema.json",
    "08_SCHEMAS/scale_reference.schema.json",
    "08_SCHEMAS/environment_continuity_report.schema.json",
    "08_SCHEMAS/video_audio_runtime_proof_boundary.schema.json",
    "09_EXAMPLES/wave09_environment_bible.example.json",
    "10_REGISTRIES/wave09_environment_registry.template.json",
    "10_REGISTRIES/wave09_video_audio_runtime_boundary_rules.json",
]

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def validate_python_syntax(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / "07_IMPLEMENTATION" / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()

    errors: list[str] = []
    json_checked = 0

    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            errors.append(f"missing required file: {rel}")
            continue
        if path.suffix == ".json":
            try:
                load_json(path)
                json_checked += 1
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON {rel}: {exc}")

    env_registry = load_json(root / "10_REGISTRIES" / "wave09_environment_registry.template.json")
    environments = env_registry.get("environments", [])
    if not environments:
        errors.append("environment registry template has no environments")

    boundary_rules = load_json(root / "10_REGISTRIES" / "wave09_video_audio_runtime_boundary_rules.json")
    if not boundary_rules.get("video", {}).get("in_scope"):
        errors.append("video must be marked in scope")
    if not boundary_rules.get("audio", {}).get("in_scope"):
        errors.append("audio must be marked in scope")
    if boundary_rules.get("video", {}).get("current_main_flow_is_proof"):
        errors.append("current Main Flow must not be treated as video runtime proof")
    if boundary_rules.get("audio", {}).get("current_main_flow_is_proof"):
        errors.append("current Main Flow must not be treated as audio runtime proof")

    errors.extend(validate_python_syntax(root))

    result = {
        "wave": "09",
        "validation": "PASS" if not errors else "FAIL",
        "required_files_checked": len(REQUIRED_FILES),
        "json_files_checked": json_checked,
        "environment_records": len(environments),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
