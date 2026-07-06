#!/usr/bin/env python3
"""Run local static validation for Wave12 pack."""
import argparse
import json
import py_compile
import sys
from pathlib import Path

REQUIRED_FILES = [
    "08_SCHEMAS/frame_composition_contract.schema.json",
    "08_SCHEMAS/frame_composition_evidence.schema.json",
    "10_REGISTRIES/wave12_body_visibility_taxonomy.json",
    "10_REGISTRIES/wave12_character_count_rules.json",
    "10_REGISTRIES/wave12_crop_boundary_rules.json",
    "10_REGISTRIES/wave12_no_merged_body_rules.json",
    "09_EXAMPLES/wave12_frame_composition_contract.example.json",
    "09_EXAMPLES/wave12_frame_composition_evidence.example.json",
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    errors = []
    for rel in REQUIRED_FILES:
        p = root / rel
        if not p.exists():
            errors.append(f"missing {rel}")
        elif p.suffix == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"invalid json {rel}: {e}")
    for script in (root / "07_IMPLEMENTATION" / "scripts").glob("*.py"):
        try:
            py_compile.compile(str(script), doraise=True)
        except Exception as e:
            errors.append(f"python compile failed {script.name}: {e}")
    report = {"validation": "FAIL" if errors else "PASS", "errors": errors, "required_files_checked": len(REQUIRED_FILES)}
    print(json.dumps(report, indent=2))
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
