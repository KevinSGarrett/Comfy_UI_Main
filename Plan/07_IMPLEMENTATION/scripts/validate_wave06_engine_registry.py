#!/usr/bin/env python3
"""
Validate Wave 06 engine registry and router rules.

Usage:
  python validate_wave06_engine_registry.py --root C:\Comfy_UI_Main
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()
    root = Path(args.root)

    registry_path = root / "10_REGISTRIES" / "wave06_engine_registry.json"
    rules_path = root / "10_REGISTRIES" / "wave06_engine_router_rules.json"
    pass_map_path = root / "10_REGISTRIES" / "wave06_pass_to_engine_map.json"

    errors = []
    for p in [registry_path, rules_path, pass_map_path]:
        if not p.exists():
            errors.append(f"Missing required file: {p}")

    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1

    registry = load_json(registry_path)
    rules = load_json(rules_path)
    pass_map = load_json(pass_map_path)

    seen = set()
    families = set()
    for idx, engine in enumerate(registry):
        for field in ["engine_id", "family", "tier", "runtime_type", "model_role", "required_assets", "compatible_lora_families", "promotion_status"]:
            if field not in engine:
                errors.append(f"Engine index {idx} missing field {field}")
        eid = engine.get("engine_id")
        if eid in seen:
            errors.append(f"Duplicate engine_id: {eid}")
        seen.add(eid)
        families.add(engine.get("family"))

    hard_rules = rules.get("hard_rules", [])
    if not hard_rules:
        errors.append("Router rules missing hard_rules")

    for pass_type, route in pass_map.items():
        for key in ["preferred", "requires", "blocked"]:
            if key not in route:
                errors.append(f"Pass map {pass_type} missing {key}")

    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1

    print("PASS: Wave06 engine registry validated")
    print(f"Engines: {len(registry)}")
    print(f"Families: {', '.join(sorted(str(f) for f in families))}")
    print(f"Hard rules: {len(hard_rules)}")
    print(f"Pass routes: {len(pass_map)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
