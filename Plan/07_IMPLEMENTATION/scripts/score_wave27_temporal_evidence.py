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
    identity = float(src.get('identity_drift_score', 100))
    flicker = float(src.get('flicker_score', 100))
    identity_stability = max(0.0, 100.0 - identity)
    flicker_stability = max(0.0, 100.0 - flicker)
    overall = round((identity_stability + flicker_stability) / 2.0, 2)
    if overall >= 90:
        decision = 'promote'
    elif overall >= 75:
        decision = 'repair'
    else:
        decision = 'rerun'
    out = {
        'run_id': src.get('run_id'),
        'engine_name': src.get('engine_name'),
        'overall_temporal_score': overall,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
