#!/usr/bin/env python3
"""Compile a Wave 20 hard-anatomy repair contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def blocked_gate(reason: str) -> dict:
    return {
        'status': 'blocked',
        'evidence_paths': [],
        'blockers': [reason],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    out = {
        'contract_version': 'wave20.v1',
        'source_image_id': src.get('source_image_id'),
        'character_id': src.get('character_id'),
        'repair_regions': src.get('repair_regions', []),
        'crop_plans': src.get('crop_plans', []),
        'qa_goals': src.get('qa_goals', []),
        'global_preservation_goals': src.get('global_preservation_goals', [
            'identity', 'pose', 'body_proportions', 'frame_integrity', 'contact_continuity'
        ]),
        'anatomy_scorecard': src.get('anatomy_scorecard', {
            **blocked_gate('anatomy_scorecard_evidence_missing'),
            'local_score': 0.0,
            'global_score': 0.0,
            'regional_checks': [],
        }),
        'hands_feet_check': src.get('hands_feet_check', {
            **blocked_gate('hands_feet_evidence_missing'),
            'hands': {'status': 'blocked', 'inspectable': False},
            'feet': {'status': 'blocked', 'inspectable': False},
        }),
        'face_teeth_eye_check': src.get('face_teeth_eye_check', {
            **blocked_gate('face_teeth_eye_evidence_missing'),
            'face': {'status': 'blocked', 'inspectable': False},
            'eyes': {'status': 'blocked', 'inspectable': False},
            'teeth': {'status': 'blocked', 'inspectable': False},
        }),
        'hard_reject_on_deformation': src.get('hard_reject_on_deformation', {
            'enabled': True,
            'triggered': True,
            'reasons': ['required_hard_anatomy_evidence_missing'],
            'promotion_allowed': False,
        }),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
