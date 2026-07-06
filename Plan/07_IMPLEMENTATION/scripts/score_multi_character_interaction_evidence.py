#!/usr/bin/env python3
"""Score Wave 25 multi-character interaction evidence."""
from __future__ import annotations
import argparse, json
from pathlib import Path

CHECK_KEYS = ['instance_ids_pass','source_target_ownership_pass','mask_alignment_pass','occlusion_depth_pass','object_ownership_pass','merge_prevention_pass','identity_preservation_pass']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    raw = data.get('checks', {})
    checks = {key: bool(raw.get(key)) for key in CHECK_KEYS}
    score = sum(1 for v in checks.values() if v) / len(CHECK_KEYS)
    report = {
        'evidence_version': 'wave25.v1',
        'event_id': data.get('event_id'),
        'checks': checks,
        'score': round(score, 4),
        'pass': score >= 0.9 and all(checks.values()),
        'failure_flags': data.get('failure_flags', [])
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
