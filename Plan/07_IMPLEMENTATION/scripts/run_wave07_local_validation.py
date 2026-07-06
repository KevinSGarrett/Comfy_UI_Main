#!/usr/bin/env python3
"""
run_wave07_local_validation.py

Validates the Wave07 cumulative pack statically.
"""
from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_FILES = [
    "08_SCHEMAS/scene_director_request.schema.json",
    "08_SCHEMAS/scene_director_plan.schema.json",
    "08_SCHEMAS/scene_graph.schema.json",
    "08_SCHEMAS/pass_plan.schema.json",
    "08_SCHEMAS/mask_goal.schema.json",
    "08_SCHEMAS/qa_goal.schema.json",
    "10_REGISTRIES/wave07_director_profiles.json",
    "10_REGISTRIES/wave07_intent_taxonomy.json",
    "10_REGISTRIES/wave07_pass_compiler_rules.json",
    "10_REGISTRIES/wave07_qa_goal_catalog.json",
    "10_REGISTRIES/wave07_plan_to_engine_route_map.json",
    "09_EXAMPLES/wave07_scene_director_request.example.json",
    "09_EXAMPLES/wave07_scene_director_plan.example.json",
    "07_IMPLEMENTATION/scripts/compile_scene_director_plan.py",
    "07_IMPLEMENTATION/scripts/validate_scene_director_plan.py",
    "07_IMPLEMENTATION/scripts/score_scene_director_plan.py",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root

    errors = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")

    json_count = 0
    for path in root.rglob("*.json"):
        try:
            load_json(path)
            json_count += 1
        except Exception as e:
            errors.append(f"invalid json: {path}: {e}")

    for rel in [
        "07_IMPLEMENTATION/scripts/compile_scene_director_plan.py",
        "07_IMPLEMENTATION/scripts/validate_scene_director_plan.py",
        "07_IMPLEMENTATION/scripts/score_scene_director_plan.py",
        "07_IMPLEMENTATION/scripts/run_wave07_local_validation.py",
    ]:
        path = root / rel
        if path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as e:
                errors.append(f"script compile failed: {rel}: {e}")

    if not errors:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "compiled_plan.json"
            compile_cmd = [
                sys.executable,
                str(root / "07_IMPLEMENTATION/scripts/compile_scene_director_plan.py"),
                "--request",
                str(root / "09_EXAMPLES/wave07_scene_director_request.example.json"),
                "--out",
                str(out),
            ]
            validate_cmd = [
                sys.executable,
                str(root / "07_IMPLEMENTATION/scripts/validate_scene_director_plan.py"),
                "--plan",
                str(out),
            ]
            score_cmd = [
                sys.executable,
                str(root / "07_IMPLEMENTATION/scripts/score_scene_director_plan.py"),
                "--plan",
                str(out),
            ]
            for cmd in [compile_cmd, validate_cmd, score_cmd]:
                proc = subprocess.run(cmd, text=True, capture_output=True)
                if proc.returncode != 0:
                    errors.append(f"command failed: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

    profiles = []
    try:
        profiles = load_json(root / "10_REGISTRIES/wave07_director_profiles.json")
    except Exception:
        pass

    report = {
        "status": "PASS" if not errors else "FAIL",
        "json_files_checked": json_count,
        "director_profiles": len(profiles) if isinstance(profiles, list) else 0,
        "errors": errors,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
