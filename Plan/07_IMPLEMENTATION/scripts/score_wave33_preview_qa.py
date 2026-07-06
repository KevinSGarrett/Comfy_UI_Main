#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DIMENSIONS = [
    'plan_completeness','composition','character_count','identity','pose','mask_region',
    'contact_occlusion','camera','animatic_timing','audio_placeholders','budget_fit','evidence_complete'
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    scores = src.get('scores', {})
    vals = [float(scores.get(k, 0)) for k in DIMENSIONS if k in scores]
    if not vals:
        vals = [0.0]
    overall = round(sum(vals) / len(vals), 2)
    flags = src.get('failure_flags', [])

    if flags:
        decision = 'repair_preview' if overall >= 75 else 'rerun_preview'
    elif overall >= 85:
        decision = 'pass_preview'
    elif overall >= 75:
        decision = 'repair_preview'
    else:
        decision = 'rerun_preview'

    out = {
        'preview_qa_id': src.get('preview_qa_id'),
        'preview_id': src.get('preview_id'),
        'overall_preview_score': overall,
        'failure_flags': flags,
        'rerun_recommendation': src.get('rerun_recommendation', 'none' if decision == 'pass_preview' else 'rerun_preview'),
        'promotion_decision': decision if decision != 'rerun_preview' else 'block_final_render'
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
