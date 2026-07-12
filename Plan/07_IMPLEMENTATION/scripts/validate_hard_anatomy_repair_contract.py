#!/usr/bin/env python3
"""Validate a Wave 20 hard-anatomy repair contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = [
    'contract_version', 'source_image_id', 'repair_regions', 'crop_plans', 'qa_goals',
    'anatomy_scorecard', 'hands_feet_check', 'face_teeth_eye_check',
    'hard_reject_on_deformation',
]
STATUSES = {'pass', 'fail', 'blocked', 'not_applicable'}


def validate_gate(name: str, gate: object, errors: list[str]) -> None:
    if not isinstance(gate, dict):
        errors.append(f'invalid: {name} must be an object')
        return
    if gate.get('status') not in STATUSES:
        errors.append(f'invalid: {name}.status')
    if not isinstance(gate.get('evidence_paths'), list):
        errors.append(f'invalid: {name}.evidence_paths')
    if not isinstance(gate.get('blockers'), list):
        errors.append(f'invalid: {name}.blockers')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    errors = [f'missing: {key}' for key in REQUIRED if key not in obj]
    if not obj.get('repair_regions'):
        errors.append('missing: at least one repair region')

    for name in ('anatomy_scorecard', 'hands_feet_check', 'face_teeth_eye_check'):
        validate_gate(name, obj.get(name), errors)

    scorecard = obj.get('anatomy_scorecard', {})
    for field in ('local_score', 'global_score'):
        value = scorecard.get(field) if isinstance(scorecard, dict) else None
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
            errors.append(f'invalid: anatomy_scorecard.{field}')
    if isinstance(scorecard, dict) and not isinstance(scorecard.get('regional_checks'), list):
        errors.append('invalid: anatomy_scorecard.regional_checks')

    for gate_name, region_names in (
        ('hands_feet_check', ('hands', 'feet')),
        ('face_teeth_eye_check', ('face', 'eyes', 'teeth')),
    ):
        gate = obj.get(gate_name, {})
        for region_name in region_names:
            region = gate.get(region_name) if isinstance(gate, dict) else None
            if not isinstance(region, dict) or region.get('status') not in STATUSES or not isinstance(region.get('inspectable'), bool):
                errors.append(f'invalid: {gate_name}.{region_name}')

    hard_reject = obj.get('hard_reject_on_deformation')
    if not isinstance(hard_reject, dict):
        errors.append('invalid: hard_reject_on_deformation must be an object')
    else:
        if hard_reject.get('enabled') is not True:
            errors.append('invalid: hard_reject_on_deformation.enabled must be true')
        if not isinstance(hard_reject.get('triggered'), bool):
            errors.append('invalid: hard_reject_on_deformation.triggered')
        if not isinstance(hard_reject.get('reasons'), list):
            errors.append('invalid: hard_reject_on_deformation.reasons')
        if not isinstance(hard_reject.get('promotion_allowed'), bool):
            errors.append('invalid: hard_reject_on_deformation.promotion_allowed')

        gate_statuses = [obj.get(name, {}).get('status') for name in ('anatomy_scorecard', 'hands_feet_check', 'face_teeth_eye_check')]
        regional_statuses = [
            obj.get('hands_feet_check', {}).get(name, {}).get('status') for name in ('hands', 'feet')
        ] + [
            obj.get('face_teeth_eye_check', {}).get(name, {}).get('status') for name in ('face', 'eyes', 'teeth')
        ]
        regional_objects = [
            obj.get('hands_feet_check', {}).get(name, {}) for name in ('hands', 'feet')
        ] + [
            obj.get('face_teeth_eye_check', {}).get(name, {}) for name in ('face', 'eyes', 'teeth')
        ]
        regions_pass = all(
            region.get('status') == 'not_applicable'
            or (region.get('status') == 'pass' and region.get('inspectable') is True)
            for region in regional_objects
        )
        all_pass = all(status in {'pass', 'not_applicable'} for status in gate_statuses) and regions_pass
        if hard_reject.get('promotion_allowed') and (hard_reject.get('triggered') or not all_pass):
            errors.append('invalid: promotion allowed while a hard-anatomy gate is not pass-like')
        if hard_reject.get('triggered') and not hard_reject.get('reasons'):
            errors.append('invalid: triggered hard reject requires reasons')

    if errors:
        print('FAIL')
        for error in errors:
            print(error)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
