#!/usr/bin/env python3
"""Run local validation for the Wave 20 hard-anatomy repair pack."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    '10_REGISTRIES/wave20_hard_anatomy_region_taxonomy.json',
    '10_REGISTRIES/wave20_crop_detail_repair_lane_profiles.json',
    '10_REGISTRIES/wave20_face_eye_teeth_rules.json',
    '10_REGISTRIES/wave20_hand_finger_foot_nail_rules.json',
    '10_REGISTRIES/wave20_hard_anatomy_qa_scoring_rules.json',
    '10_REGISTRIES/wave20_hard_anatomy_rerun_policy.json',
    '10_REGISTRIES/wave20_main_flow_hard_anatomy_inventory.json',
    '08_SCHEMAS/hard_anatomy_repair_contract.schema.json',
    '09_EXAMPLES/wave20_hard_anatomy_repair_contract.example.json',
]
SCRIPT_FILES = [
    '07_IMPLEMENTATION/scripts/compile_hard_anatomy_repair_contract.py',
    '07_IMPLEMENTATION/scripts/validate_hard_anatomy_repair_contract.py',
    '07_IMPLEMENTATION/scripts/score_hard_anatomy_evidence.py',
    '07_IMPLEMENTATION/scripts/inventory_main_flow_hard_anatomy_wave20.py',
    '07_IMPLEMENTATION/scripts/run_wave20_local_validation.py',
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


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

    inv_path = root / '10_REGISTRIES/wave20_main_flow_hard_anatomy_inventory.json'
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
        if inv.get('hard_anatomy_lora_summary', {}).get('count', 0) < 1:
            errors.append('hard anatomy signal inventory is empty')

    if errors:
        print('FAIL: Wave20 validation failed')
        for err in errors:
            print(f'- {err}')
        return 1

    print('PASS: Wave20 hard-anatomy repair pack validated')
    print(f'JSON files checked: {len(json_files)}')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
