#!/usr/bin/env python3
"""
Validate that a local .env file contains the minimum keys required by Wave03.
This does not validate actual secret values and never prints secret contents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_KEYS = [
    "PROJECT_ROOT",
    "GITHUB_REPO_URL",
    "CIVITAI_API_KEY",
    "AWS_PROFILE",
    "AWS_REGION",
    "S3_MODEL_BUCKET",
    "S3_MODEL_PREFIX",
    "LOCAL_MODEL_CACHE_ROOT",
    "COMFYUI_LOCAL_ROOT",
    "COMFYUI_API_URL",
    "MODEL_REGISTRY_PATH",
    "ASSET_COMPAT_REGISTRY_PATH",
]

def parse_env(path: Path):
    values = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-example-placeholders", action="store_true")
    args = parser.parse_args()

    path = Path(args.env_file)
    values = parse_env(path)
    missing = [key for key in REQUIRED_KEYS if key not in values or not values[key]]
    placeholder_keys = [
        key for key, value in values.items()
        if any(token in value.lower() for token in ["replace_me", "your_", "changeme", "<", ">"])
    ]

    result = "PASS"
    if missing:
        result = "FAIL"
    elif placeholder_keys and not args.allow_example_placeholders:
        result = "WARN"

    report = {
        "schema_version": "wave03.env_validation_report.v1",
        "env_file": str(path),
        "required_keys": REQUIRED_KEYS,
        "missing_keys": missing,
        "placeholder_keys": placeholder_keys,
        "result": result,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"result": result, "missing_count": len(missing), "placeholder_count": len(placeholder_keys)}, indent=2))
    return 0 if result in {"PASS", "WARN"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
