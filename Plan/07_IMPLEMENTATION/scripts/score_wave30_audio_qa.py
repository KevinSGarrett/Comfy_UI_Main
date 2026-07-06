#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DIMENSIONS = ['decode','duration','loudness','clipping','sync','voice_identity','event_coverage','mix_balance']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    scores = src.get('qa_scores', {})
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
        'run_id': src.get('run_id'),
        'overall_audio_score': overall,
        'failure_flags': flags,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
