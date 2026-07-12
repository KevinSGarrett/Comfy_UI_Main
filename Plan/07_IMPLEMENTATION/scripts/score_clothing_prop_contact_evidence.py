#!/usr/bin/env python3
"""Score Wave 19 contact evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_GATES = ('contact_graph_check', 'shadow_contact_check', 'no_floating_check', 'visual_reject_on_clip')


def gate_passes(value: object) -> bool:
    return isinstance(value, dict) and value.get('status') == 'pass' and value.get('inspectable') is True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    weights = {
        'contact_graph_check': 0.20,
        'no_floating_check': 0.20,
        'visual_reject_on_clip': 0.20,
        'shadow_contact_check': 0.15,
        'fabric_material_continuity': 0.15,
        'identity_pose_body_preserved': 0.10,
    }
    results = {key: gate_passes(data.get(key)) for key in weights}
    clip = data.get('visual_reject_on_clip', {})
    visual = data.get('visual_qa_reference', {})
    visual_authority = bool(
        isinstance(visual.get('evidence_path'), str)
        and visual.get('evidence_path', '').strip()
        and visual.get('certification_scope') == 'wave19'
        and visual.get('final_certification_allowed') is True
    )
    required_gates_pass = all(results[key] for key in REQUIRED_GATES)
    clip_clear = clip.get('clip_detected') is False
    score = 0.0
    for key, weight in weights.items():
        if results[key]:
            score += weight
    report = {
        'evidence_version': 'wave19.v1',
        'score': round(score, 4),
        'minimum_score': 0.85,
        'required_gates_pass': required_gates_pass,
        'clip_clear': clip_clear,
        'visual_authority_pass': visual_authority,
        'pass': bool(score >= 0.85 and required_gates_pass and clip_clear and visual_authority),
        'failed_dimensions': [key for key in weights if not results[key]],
        'automatic_fail_flags': ([] if required_gates_pass else ['required_gate_failure']) + ([] if clip_clear else ['clip_detected']) + ([] if visual_authority else ['wave19_visual_authority_missing']),
        'visual_qa_reference': visual,
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
