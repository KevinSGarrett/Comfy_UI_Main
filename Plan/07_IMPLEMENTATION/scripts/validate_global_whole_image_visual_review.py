#!/usr/bin/env python3
"""Validate the Wave64 Row017 whole-image review contract."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

GATES = ('whole_frame_visual_scan', 'required_target_region_check', 'required_non_target_region_scan')
CATEGORIES = ('hands', 'face', 'body', 'background', 'contact', 'lighting')
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = load(Path(args.input))
    errors: list[str] = []
    required = ('schema_version', 'artifact', 'localized_change', *GATES, 'hands_face_body_background_contact_lighting_check', 'reject_on_any_global_defect', 'overall_decision')
    errors.extend(f'missing: {key}' for key in required if key not in obj)
    if obj.get('schema_version') != 'row017.v1':
        errors.append('schema_version must be row017.v1')
    for label, artifact in (('artifact', obj.get('artifact')), ('localized_change.source_artifact', obj.get('localized_change', {}).get('source_artifact'))):
        if not isinstance(artifact, dict) or not isinstance(artifact.get('path'), str) or not artifact.get('path', '').strip() or not isinstance(artifact.get('sha256'), str) or not SHA256.fullmatch(artifact['sha256']):
            errors.append(f'{label} must contain a non-empty path and lowercase SHA256')
    target = obj.get('localized_change', {}).get('target_region')
    if not isinstance(target, str) or not target.strip():
        errors.append('localized_change.target_region must be a non-empty string')
    for gate in GATES:
        value = obj.get(gate)
        if not isinstance(value, dict) or value.get('status') not in {'pass', 'blocked', 'fail'}:
            errors.append(f'{gate}.status is invalid')
        paths = value.get('evidence_paths') if isinstance(value, dict) else None
        if not isinstance(paths, list) or any(not isinstance(path, str) or not path.strip() for path in paths):
            errors.append(f'{gate}.evidence_paths must contain only non-empty strings')
    whole = obj.get('whole_frame_visual_scan', {})
    if whole.get('pre_edit_status') not in {'pass', 'blocked', 'fail'} or whole.get('post_edit_status') not in {'pass', 'blocked', 'fail'}:
        errors.append('whole_frame_visual_scan pre/post status is invalid')
    target_gate = obj.get('required_target_region_check', {})
    if target_gate.get('target_region') != target:
        errors.append('required_target_region_check must match localized_change.target_region')
    non_target = obj.get('required_non_target_region_scan', {})
    if not isinstance(non_target.get('regions_scanned'), list) or not non_target.get('regions_scanned'):
        errors.append('required_non_target_region_scan.regions_scanned must be nonempty')
    coverage = obj.get('hands_face_body_background_contact_lighting_check', {})
    coverage_pass = True
    for category in CATEGORIES:
        value = coverage.get(category)
        if not isinstance(value, dict) or value.get('inspected') is not True:
            errors.append(f'{category} must be explicitly inspected')
            coverage_pass = False
            continue
        visibility, status, reason = value.get('visibility'), value.get('status'), value.get('reason')
        if visibility == 'visible' and status != 'pass':
            coverage_pass = False
        elif visibility in {'not_visible', 'not_applicable'} and (status != 'not_applicable' or not isinstance(reason, str) or not reason.strip()):
            errors.append(f'{category} not-applicable coverage requires status and reason')
            coverage_pass = False
        elif visibility not in {'visible', 'not_visible', 'not_applicable'}:
            errors.append(f'{category}.visibility is invalid')
            coverage_pass = False
    reject = obj.get('reject_on_any_global_defect', {})
    defects = reject.get('global_defects')
    if not isinstance(defects, list):
        errors.append('reject_on_any_global_defect.global_defects must be an array')
        defects = []
    decision = obj.get('overall_decision')
    if defects and (reject.get('status') != 'fail' or reject.get('rejection_applied') is not True or decision != 'reject'):
        errors.append('any global defect requires fail status and rejection')
    if decision == 'pass':
        if any(obj.get(gate, {}).get('status') != 'pass' for gate in GATES) or whole.get('pre_edit_status') != 'pass' or whole.get('post_edit_status') != 'pass':
            errors.append('pass requires whole-frame, target, and non-target gates to pass')
        if not coverage_pass:
            errors.append('pass requires complete global category coverage')
        if defects or reject.get('status') != 'pass' or reject.get('rejection_applied') is not False:
            errors.append('pass requires zero global defects')
    if decision not in {'pass', 'reject', 'blocked'}:
        errors.append('overall_decision is invalid')
    if errors:
        print('FAIL')
        for error in errors:
            print(error)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
