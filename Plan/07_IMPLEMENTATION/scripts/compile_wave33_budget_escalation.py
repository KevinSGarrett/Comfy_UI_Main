#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview-qa', required=True)
    parser.add_argument('--from-tier', required=True)
    parser.add_argument('--to-tier', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    preview_qa = json.loads(Path(args.preview_qa).read_text(encoding='utf-8'))
    evidence = [args.preview_qa]
    allowed = preview_qa.get('promotion_decision') == 'pass_preview'
    out = {
        'escalation_id': f"esc_{preview_qa.get('preview_id', 'unknown')}",
        'source_preview_id': preview_qa.get('preview_id'),
        'from_tier': args.from_tier,
        'to_tier': args.to_tier,
        'reason': 'preview QA passed and budget escalation requested' if allowed else 'preview QA did not pass',
        'evidence_refs': evidence,
        'approval_status': 'approved_by_policy' if allowed else 'blocked_preview_qa_not_passed'
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
