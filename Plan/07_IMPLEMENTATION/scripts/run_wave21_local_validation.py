#!/usr/bin/env python3
"""Run local validation for the Wave 21 soft-body material profile pack."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    '10_REGISTRIES/wave21_soft_body_material_profiles.json',
    '10_REGISTRIES/wave21_firmness_softness_spectrum.json',
    '10_REGISTRIES/wave21_body_region_soft_profile_bindings.json',
    '10_REGISTRIES/wave21_motion_response_profiles.json',
    '10_REGISTRIES/wave21_compression_rebound_profiles.json',
    '10_REGISTRIES/wave21_soft_body_qa_scoring_rules.json',
    '10_REGISTRIES/wave21_soft_body_rerun_policy.json',
    '10_REGISTRIES/wave21_main_flow_soft_body_material_inventory.json',
    '08_SCHEMAS/soft_body_material_profile.schema.json',
    '09_EXAMPLES/wave21_soft_body_material_profile.example.json',
]
SCRIPT_FILES = [
    '07_IMPLEMENTATION/scripts/compile_soft_body_material_contract.py',
    '07_IMPLEMENTATION/scripts/validate_soft_body_material_contract.py',
    '07_IMPLEMENTATION/scripts/score_soft_body_material_evidence.py',
    '07_IMPLEMENTATION/scripts/inventory_main_flow_soft_body_wave21.py',
    '07_IMPLEMENTATION/scripts/run_wave21_local_validation.py',
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

    for rel in SCRIPT_FILES:
        path = root / rel
        if not path.exists():
            errors.append(f'missing script: {rel}')
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f'script compile failed: {rel}: {exc}')

    inv_path = root / '10_REGISTRIES/wave21_main_flow_soft_body_material_inventory.json'
    if inv_path.exists():
        inv = load_json(inv_path)
        if inv.get('node_count', 0) <= 0:
            errors.append('main flow inventory node_count is zero')
        if len(inv.get('save_lanes', [])) < 1:
            errors.append('main flow inventory has no SaveImage lanes')
        if len(inv.get('mask_input_slots', [])) < 1:
            errors.append('main flow inventory has no mask input slots')
        if len(inv.get('low_denoise_anchors', [])) < 1:
            errors.append('main flow inventory has no low-denoise anchors')
        if inv.get('soft_body_candidate_summary', {}).get('count', 0) < 1:
            errors.append('soft-body candidate inventory is empty')

    profiles = root / '10_REGISTRIES/wave21_soft_body_material_profiles.json'
    if profiles.exists():
        data = load_json(profiles)
        if len(data.get('profiles', [])) < 5:
            errors.append('soft-body material profile registry has too few profiles')

    if errors:
        print('FAIL: Wave21 validation failed')
        for err in errors:
            print(f'- {err}')
        return 1

    print('PASS: Wave21 soft-body material profile pack validated')
    print(f'JSON files checked: {len(json_files)}')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
