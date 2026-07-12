#!/usr/bin/env python3
"""Validate a Wave 18 skin/material contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EVIDENCE_GATES = [
    'surface_texture_check',
    'lighting_consistency',
    'material_state_continuity',
    'visual_score_threshold',
]


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--profiles')
    args = parser.parse_args()
    obj = load(Path(args.input))
    profiles_path = Path(args.profiles) if args.profiles else Path(__file__).resolve().parents[2] / '10_REGISTRIES/wave18_skin_material_profiles.json'
    profiles = {row.get('profile_id') for row in load(profiles_path).get('profiles', [])}
    errors: list[str] = []
    required = ['contract_version', 'source_image_id', 'target_regions', 'surface_profile', 'required_evidence_gates']
    errors.extend(f'missing: {key}' for key in required if key not in obj)
    if obj.get('contract_version') != 'wave18.v1':
        errors.append('contract_version must be wave18.v1')
    if not isinstance(obj.get('source_image_id'), str) or not obj.get('source_image_id', '').strip():
        errors.append('source_image_id must be a non-empty string')
    regions = obj.get('target_regions')
    if not isinstance(regions, list) or not regions or any(not isinstance(row, str) or not row.strip() for row in regions):
        errors.append('target_regions must contain at least one non-empty string')
    profile = obj.get('surface_profile')
    if not isinstance(profile, str) or profile not in profiles:
        errors.append('surface_profile is not registered')
    if obj.get('required_evidence_gates') != REQUIRED_EVIDENCE_GATES:
        errors.append('required_evidence_gates must match the Wave18 gate contract')
    for key in ('pass_order', 'qa_goals'):
        if key in obj and not isinstance(obj[key], list):
            errors.append(f'{key} must be an array')
    if errors:
        print('FAIL')
        for item in errors:
            print(item)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
