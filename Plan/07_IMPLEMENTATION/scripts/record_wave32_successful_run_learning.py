#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--take', required=True)
    parser.add_argument('--diff', required=True)
    parser.add_argument('--qa', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    take = json.loads(Path(args.take).read_text(encoding='utf-8'))
    diff = json.loads(Path(args.diff).read_text(encoding='utf-8'))
    qa = json.loads(Path(args.qa).read_text(encoding='utf-8'))

    promoted = qa.get('promotion_decision') == 'promote' or diff.get('promotion_decision') == 'promote'
    learning_type = 'positive_pattern' if promoted else 'negative_anti_pattern'
    out = {
        'learning_id': f"learn_{take.get('take_id', 'unknown')}",
        'source_take_id': take.get('take_id'),
        'learning_type': learning_type,
        'successful_patterns': [] if not promoted else [{'domain': d.get('domain'), 'pattern': 'planned and generated state matched'} for d in diff.get('domain_diffs', []) if d.get('status') == 'matched'],
        'failed_patterns': [] if promoted else [{'domain': d.get('domain'), 'failure': d.get('status')} for d in diff.get('domain_diffs', []) if d.get('status') in {'mismatch','missing','uncertain'}],
        'reuse_constraints': ['must meet equal or higher QA thresholds', 'must not bypass future QA'],
        'evidence_refs': [args.take, args.diff, args.qa],
        'qa_thresholds': {'overall': 90}
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
