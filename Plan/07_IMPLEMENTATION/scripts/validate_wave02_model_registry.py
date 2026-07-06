#!/usr/bin/env python3
"""
Wave 02 model registry validator.

Validates:
- registry has at least 70 columns
- required fields exist
- no likely model binary paths are inside repo
- no real secrets are present in .env.example
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


REQUIRED_COLUMNS = {
    "asset_id_internal",
    "hash_sha256",
    "engine_family",
    "asset_type",
    "resource_type",
    "comfyui_target_folder",
    "recommended_pass_scope",
    "required_qa_tests",
    "promotion_status",
}

MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx")


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def validate_csv(path: Path, failures: list[str]) -> None:
    if not path.exists():
        fail(f"registry CSV missing: {path}", failures)
        return
    with path.open(newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            fail("registry CSV is empty", failures)
            return
    if len(header) < 70:
        fail(f"registry has {len(header)} columns; expected at least 70", failures)
    missing = sorted(REQUIRED_COLUMNS - set(header))
    if missing:
        fail(f"registry missing required columns: {missing}", failures)


def validate_templates(repo_root: Path, failures: list[str]) -> None:
    env_example = repo_root / "07_IMPLEMENTATION/templates/repo/.env.example"
    if not env_example.exists():
        fail(".env.example missing", failures)
        return
    text = env_example.read_text(encoding="utf-8", errors="ignore")
    # Fail only obvious non-placeholder secrets.
    secret_patterns = [
        r"GITHUB_TOKEN=(ghp_|github_pat_)[A-Za-z0-9_]+",
        r"CIVITAI_API_KEY=[A-Za-z0-9_-]{20,}",
        r"AWS_SECRET_ACCESS_KEY=[A-Za-z0-9/+=]{20,}",
        r"AWS_ACCESS_KEY_ID=AKIA[A-Z0-9]+",
    ]
    for pat in secret_patterns:
        if re.search(pat, text):
            fail(f"possible real secret found in .env.example pattern: {pat}", failures)


def validate_no_model_binaries(repo_root: Path, failures: list[str]) -> None:
    for p in repo_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in MODEL_EXTENSIONS:
            fail(f"model binary present inside blueprint/repo tree: {p}", failures)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--registry-csv", type=Path, default=Path("09_EXAMPLES/civitai_model_registry_70plus.columns.csv"))
    parser.add_argument("--report-json", type=Path, default=Path("11_RELEASES/WAVE02_VALIDATION_REPORT.json"))
    args = parser.parse_args()

    failures: list[str] = []
    validate_csv(args.repo_root / args.registry_csv, failures)
    validate_templates(args.repo_root, failures)
    validate_no_model_binaries(args.repo_root, failures)

    report = {
        "wave": "02",
        "passed": not failures,
        "failures": failures,
        "required_columns": sorted(REQUIRED_COLUMNS),
        "minimum_columns": 70,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
