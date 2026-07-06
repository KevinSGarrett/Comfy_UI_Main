#!/usr/bin/env python3
"""
Wave03 local validation runner.

Recommended local sequence:
1. Static workflow graph validation.
2. Model-reference extraction.
3. JSON registry parse validation.
4. Optional .env validation.
5. Optional /object_info capture and node visibility validation.

This runner keeps EC2 off by default. It does not render images.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    print("+ " + " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--out-dir", default="Implementation/manifests/wave03_local_validation")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--object-info", default="")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    checks = []

    commands = [
        ("workflow_graph", [sys.executable, str(script_dir / "validate_workflow_graph.py"), "--workflow", args.workflow, "--out-dir", str(out_dir)]),
        ("model_refs", [sys.executable, str(script_dir / "extract_workflow_model_references.py"), "--workflow", args.workflow, "--out-csv", str(out_dir / "model_references.csv")]),
        ("json_registries", [sys.executable, str(script_dir / "validate_json_registries.py"), "--root", str(repo_root), "--out", str(out_dir / "json_registry_parse_report.json")]),
    ]

    if args.env_file:
        commands.append(("env_file", [sys.executable, str(script_dir / "validate_env_file.py"), "--env-file", args.env_file, "--out", str(out_dir / "env_validation_report.json")]))

    if args.object_info:
        commands.append(("object_info_node_visibility", [sys.executable, str(script_dir / "validate_object_info_against_workflows.py"), "--object-info", args.object_info, "--workflow", args.workflow, "--out", str(out_dir / "object_info_validation_report.json")]))

    final_code = 0
    for name, cmd in commands:
        code = run(cmd)
        checks.append({"name": name, "exit_code": code, "result": "PASS" if code == 0 else "FAIL"})
        if code != 0:
            final_code = code

    if not args.object_info:
        checks.append({
            "name": "object_info_node_visibility",
            "exit_code": None,
            "result": "BLOCKED_RUNTIME_PROOF_REQUIRED",
            "details": "Run collect_comfyui_object_info.py against a live local or EC2 ComfyUI runtime."
        })

    manifest = {
        "schema_version": "wave03.validation_manifest.v1",
        "wave": "03",
        "result": "PASS" if final_code == 0 and args.object_info else ("BLOCKED_RUNTIME_PROOF_REQUIRED" if final_code == 0 else "FAIL"),
        "checks": checks,
    }
    with (out_dir / "wave03_validation_manifest.json").open("w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps(manifest, indent=2))
    return final_code


if __name__ == "__main__":
    raise SystemExit(main())
