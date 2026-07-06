#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DIMENSIONS = ['state_match_score','preservation_score','rerun_scope_score','evidence_score','learning_safety_score']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    vals = [float(src.get(k, 0)) for k in DIMENSIONS]
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
        'qa_report_id': src.get('qa_report_id'),
        'diff_id': src.get('diff_id'),
        'overall_state_diff_score': overall,
        'failure_flags': flags,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
