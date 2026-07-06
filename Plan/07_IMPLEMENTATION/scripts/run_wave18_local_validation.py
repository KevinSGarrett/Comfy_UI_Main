#!/usr/bin/env python3
"""Run local validation for the Wave 18 skin/material realism pack."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    '10_REGISTRIES/wave18_surface_state_taxonomy.json',
    '10_REGISTRIES/wave18_skin_material_profiles.json',
    '10_REGISTRIES/wave18_surface_pass_profiles.json',
    '10_REGISTRIES/wave18_skin_material_lora_selection_rules.json',
    '10_REGISTRIES/wave18_surface_continuity_scoring_rules.json',
    '10_REGISTRIES/wave18_pressure_mark_profiles.json',
    '10_REGISTRIES/wave18_skin_material_rerun_policy.json',
    '10_REGISTRIES/wave18_main_flow_skin_material_inventory.json',
    '08_SCHEMAS/skin_material_contract.schema.json',
    '09_EXAMPLES/wave18_skin_material_contract.example.json',
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f'missing required file: {rel}')

    json_files = list(root.rglob('*.json'))
    for path in json_files:
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f'invalid JSON: {path.relative_to(root)}: {exc}')

    script_files = [
        root / '07_IMPLEMENTATION/scripts/compile_skin_material_contract.py',
        root / '07_IMPLEMENTATION/scripts/validate_skin_material_contract.py',
        root / '07_IMPLEMENTATION/scripts/score_skin_material_evidence.py',
        root / '07_IMPLEMENTATION/scripts/inventory_main_flow_skin_wave18.py',
        root / '07_IMPLEMENTATION/scripts/run_wave18_local_validation.py',
    ]
    for path in script_files:
        if not path.exists():
            errors.append(f'missing script: {path.relative_to(root)}')
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f'script compile failed: {path.relative_to(root)}: {exc}')

    inv_path = root / '10_REGISTRIES/wave18_main_flow_skin_material_inventory.json'
    if inv_path.exists():
        inv = load_json(inv_path)
        if inv.get('node_count', 0) <= 0:
            errors.append('main flow inventory node_count is zero')
        if len(inv.get('mask_input_slots', [])) < 1:
            errors.append('main flow inventory has no mask input slots')
        if len(inv.get('low_denoise_anchors', [])) < 1:
            errors.append('main flow inventory has no low-denoise anchors')

    if errors:
        print('FAIL: Wave18 validation failed')
        for err in errors:
            print(f'- {err}')
        return 1

    print('PASS: Wave18 skin/material realism pack validated')
    print(f'JSON files checked: {len(json_files)}')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
