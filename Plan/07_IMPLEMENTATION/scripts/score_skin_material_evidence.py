#!/usr/bin/env python3
"""Score Wave 18 skin/material evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

GATES = ('surface_texture_check', 'lighting_consistency', 'material_state_continuity')


def gate_passes(value: object) -> bool:
    return isinstance(value, dict) and value.get('status') == 'pass' and value.get('inspectable') is True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    continuity_score = data.get('continuity_score', 0.0)
    visual = data.get('visual_score_threshold', {})
    visual_score = visual.get('score', -1)
    visual_threshold = visual.get('threshold', -1)
    bounded = all(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1 for value in (continuity_score,))
    visual_bounded = all(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100 for value in (visual_score, visual_threshold))
    if not bounded or not visual_bounded:
        print('FAIL: scores must be within their declared ranges')
        return 1
    gate_results = {gate: gate_passes(data.get(gate)) for gate in GATES}
    visual_ref = data.get('visual_qa_reference', {})
    visual_gate_pass = bool(
        visual_score >= visual_threshold
        and visual.get('macro_review_status') == 'pass'
        and visual.get('full_frame_review_status') == 'pass'
        and isinstance(visual_ref.get('evidence_path'), str)
        and visual_ref.get('evidence_path', '').strip()
        and isinstance(visual_ref.get('qa_result'), str)
        and visual_ref.get('qa_result', '').strip()
        and visual_ref.get('certification_allowed') is True
    )
    report = {
        'evidence_version': 'wave18.v1',
        'surface_target_visible': data.get('surface_target_visible', False),
        'identity_preserved': data.get('identity_preserved', False),
        'pose_preserved': data.get('pose_preserved', False),
        'body_preserved': data.get('body_preserved', False),
        'crop_preserved': data.get('crop_preserved', False),
        'continuity_score': continuity_score,
        **{gate: data.get(gate, {'status': 'blocked', 'inspectable': False}) for gate in GATES},
        'visual_score_threshold': visual,
        'visual_qa_reference': visual_ref,
        'automatic_fail_flags': [gate for gate, passed in gate_results.items() if not passed] + ([] if visual_gate_pass else ['visual_score_threshold']),
    }
    report['pass'] = bool(
        report['surface_target_visible']
        and report['identity_preserved']
        and report['pose_preserved']
        and report['body_preserved']
        and report['crop_preserved']
        and report['continuity_score'] >= 0.8
        and all(gate_results.values())
        and visual_gate_pass
    )
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
