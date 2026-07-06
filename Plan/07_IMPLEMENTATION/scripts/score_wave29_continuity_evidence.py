#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DIMENSIONS = ['identity','body_state','fatigue','breathing','clothing','hair_surface','contact_deformation','scene_progression','variation']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    scores = src.get('continuity_scores', {})
    vals = [float(scores.get(k, 0)) for k in DIMENSIONS]
    overall = round(sum(vals) / len(vals), 2)
    flags = src.get('failure_flags', [])
    if flags:
        decision = 'repair' if overall >= 75 else 'rerun'
    elif overall >= 90:
        decision = 'promote'
    elif overall >= 75:
        decision = 'repair'
    else:
        decision = 'rerun'
    out = {
        'sequence_id': src.get('sequence_id'),
        'segment_id': src.get('segment_id'),
        'overall_continuity_score': overall,
        'failure_flags': flags,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
