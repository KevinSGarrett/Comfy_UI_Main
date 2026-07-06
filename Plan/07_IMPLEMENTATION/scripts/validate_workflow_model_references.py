#!/usr/bin/env python3
"""
Validate workflow model references against local cache roots and/or a model
registry CSV/JSON. Designed to run locally before EC2 is turned on.

The validator is intentionally conservative:
- Exact local file hit => PASS for that asset.
- Registry hash/path hit but local file missing => WARN/HYDRATE_REQUIRED.
- No local or registry hit => FAIL unless --allow-missing is used.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


def read_refs(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_registry_assets(paths):
    assets = set()
    for path_str in paths or []:
        path = Path(path_str)
        if not path.exists():
            continue
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            def walk(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key.lower() in {"asset_reference", "local_path", "relative_path", "filename", "file_name", "s3_key"} and isinstance(value, str):
                            assets.add(value.replace("\\", "/"))
                        walk(value)
                elif isinstance(obj, list):
                    for item in obj:
                        walk(item)
            walk(data)
        elif path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for key, value in row.items():
                        if value and key and key.lower() in {"asset_reference", "local_path", "relative_path", "filename", "file_name", "s3_key", "Source_Path", "Output_Artifact"}:
                            assets.add(value.replace("\\", "/"))
    return assets


def find_local(asset_ref: str, roots):
    asset_name = asset_ref.replace("\\", "/").split("/")[-1]
    candidates = []
    for root_str in roots or []:
        root = Path(root_str)
        if not root.exists():
            continue
        direct = root / asset_ref
        candidates.append(direct)
        candidates.append(root / asset_name)
        for c in candidates:
            if c.exists():
                return str(c)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refs-csv", required=True)
    parser.add_argument("--local-root", action="append", default=[])
    parser.add_argument("--registry", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    refs = read_refs(Path(args.refs_csv))
    registry_assets = load_registry_assets(args.registry)
    rows = []
    missing = []

    for ref in refs:
        asset_ref = ref.get("asset_reference", "")
        normalized = asset_ref.replace("\\", "/")
        local_hit = find_local(asset_ref, args.local_root)
        registry_hit = any(
            normalized == a or normalized.endswith("/" + a.split("/")[-1]) or a.endswith("/" + normalized.split("/")[-1])
            for a in registry_assets
        )
        if local_hit:
            result = "PASS_LOCAL_FILE_FOUND"
        elif registry_hit:
            result = "WARN_REGISTRY_HIT_LOCAL_HYDRATION_REQUIRED"
        else:
            result = "MISSING"
            missing.append(asset_ref)
        rows.append({**ref, "local_hit": local_hit, "registry_hit": registry_hit, "result": result})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else ["asset_reference", "result"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary = {
        "result": "PASS" if (not missing or args.allow_missing) else "FAIL",
        "reference_count": len(refs),
        "missing_count": len(missing),
        "missing": missing[:100],
        "out": str(out),
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
