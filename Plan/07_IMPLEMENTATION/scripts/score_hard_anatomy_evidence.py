#!/usr/bin/env python3
"""Score Wave 20 hard-anatomy evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


PASS_LIKE = {'pass', 'not_applicable'}


def status_passes(value: object) -> bool:
    return isinstance(value, dict) and value.get('status') in PASS_LIKE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    checks = {
        'local_anatomy_improved': bool(data.get('local_anatomy_improved', False)),
        'identity_preserved': bool(data.get('identity_preserved', False)),
        'pose_preserved': bool(data.get('pose_preserved', False)),
        'contact_preserved': bool(data.get('contact_preserved', False)),
        'frame_preserved': bool(data.get('frame_preserved', False)),
        'seam_blend_passed': bool(data.get('seam_blend_passed', False)),
    }
    local_score = float(data.get('local_score', 0.0))
    global_score = float(data.get('global_score', 0.0))
    anatomy_scorecard = data.get('anatomy_scorecard', {})
    hands_feet_check = data.get('hands_feet_check', {})
    face_teeth_eye_check = data.get('face_teeth_eye_check', {})
    hard_reject = data.get('hard_reject_on_deformation', {})
    regional_checks = [
        hands_feet_check.get('hands', {}),
        hands_feet_check.get('feet', {}),
        face_teeth_eye_check.get('face', {}),
        face_teeth_eye_check.get('eyes', {}),
        face_teeth_eye_check.get('teeth', {}),
    ]
    required_gates_pass = all(status_passes(gate) for gate in (anatomy_scorecard, hands_feet_check, face_teeth_eye_check))
    regional_checks_pass = all(
        status_passes(region) and (region.get('status') == 'not_applicable' or region.get('inspectable') is True)
        for region in regional_checks
    )
    hard_reject_clear = (
        hard_reject.get('enabled') is True
        and hard_reject.get('triggered') is False
        and hard_reject.get('promotion_allowed') is True
    )
    automatic_fail_flags = []
    if not status_passes(anatomy_scorecard):
        automatic_fail_flags.append('anatomy_scorecard_not_passed')
    if not all(status_passes(region) and region.get('inspectable') is True for region in regional_checks[:2]):
        automatic_fail_flags.append('hands_or_feet_not_inspectable')
    if not all(status_passes(region) and (region.get('status') == 'not_applicable' or region.get('inspectable') is True) for region in regional_checks[2:]):
        automatic_fail_flags.append('face_teeth_or_eyes_not_inspectable')
    if not hard_reject_clear:
        automatic_fail_flags.append('hard_reject_on_deformation_triggered')
    report = {
        'evidence_version': 'wave20.v1',
        **checks,
        'local_score': local_score,
        'global_score': global_score,
        'anatomy_scorecard': anatomy_scorecard,
        'hands_feet_check': hands_feet_check,
        'face_teeth_eye_check': face_teeth_eye_check,
        'hard_reject_on_deformation': hard_reject,
        'required_gates_pass': required_gates_pass,
        'regional_checks_pass': regional_checks_pass,
        'hard_reject_clear': hard_reject_clear,
        'automatic_fail_flags': automatic_fail_flags,
        'pass': (
            all(checks.values())
            and local_score >= 0.82
            and global_score >= 0.86
            and required_gates_pass
            and regional_checks_pass
            and hard_reject_clear
            and not automatic_fail_flags
        ),
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
