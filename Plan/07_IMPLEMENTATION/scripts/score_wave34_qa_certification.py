#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DIMENSIONS = [
    'schema_validity','registry_validity','script_validity','app_mode_mapping',
    'orchestrator_route_integrity','pruntime_gate_integrity','state_diff_integrity',
    'local_proof','manifest_completeness','release_decision_consistency'
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    scores = src.get('domain_scores', {})
    vals = []
    for d in DIMENSIONS:
        v = scores.get(d, 0)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    overall = round(sum(vals) / len(vals), 2) if vals else 0.0
    missing = src.get('missing_evidence', [])
    flags = src.get('failure_flags', [])
    if flags:
        status = 'repair_required'
        recommendation = 'repair_required'
    elif missing:
        status = 'certified_with_runtime_boundaries'
        recommendation = 'release_with_runtime_boundaries'
    elif overall >= 95:
        status = 'certified'
        recommendation = 'release_runtime_certified'
    elif overall >= 85:
        status = 'repair_required'
        recommendation = 'repair_required'
    else:
        status = 'blocked_failed_QA'
        recommendation = 'blocked_failed_QA'

    out = {
        'certification_id': src.get('certification_id', 'qa_cert_wave34'),
        'overall_score': overall,
        'missing_evidence': missing,
        'failure_flags': flags,
        'certification_status': status,
        'release_recommendation': recommendation
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
