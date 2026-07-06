#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    bounded = float(src.get('bounded_motion_score', 0))
    identity = float(src.get('identity_stability_score', 0))
    flicker = float(src.get('flicker_score', 100))
    flicker_stability = max(0.0, 100.0 - flicker)
    overall = round((bounded + identity + flicker_stability) / 3.0, 2)
    if overall >= 90:
        decision = 'promote'
    elif overall >= 75:
        decision = 'repair'
    else:
        decision = 'rerun'
    out = {
        'run_id': src.get('run_id'),
        'event_id': src.get('event_id'),
        'overall_micro_motion_score': overall,
        'promotion_decision': decision,
        'repair_events': src.get('repair_events', [])
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
