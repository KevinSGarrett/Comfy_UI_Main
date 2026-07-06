#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview-qa', required=True)
    parser.add_argument('--realism-budget', required=True)
    parser.add_argument('--compute-budget', required=True)
    parser.add_argument('--selected-take-or-variant-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    preview_qa = json.loads(Path(args.preview_qa).read_text(encoding='utf-8'))
    realism_budget = json.loads(Path(args.realism_budget).read_text(encoding='utf-8'))
    compute_budget = json.loads(Path(args.compute_budget).read_text(encoding='utf-8'))

    blocked = []
    if preview_qa.get('promotion_decision') not in {'pass_preview', 'unlock_final_render'}:
        blocked.append('preview_qa_not_passed')
    if not realism_budget.get('budget_id'):
        blocked.append('missing_realism_budget_id')
    if not compute_budget.get('compute_budget_id'):
        blocked.append('missing_compute_budget_id')
    if not args.selected_take_or_variant_id:
        blocked.append('missing_selected_take_or_variant')
    allowed_tier = compute_budget.get('allowed_tier')
    if allowed_tier not in {'ec2_preview','ec2_final','ec2_hero_final'}:
        blocked.append('compute_budget_not_final_capable')
    if compute_budget.get('ec2_allowed') is not True:
        blocked.append('ec2_not_allowed_by_compute_budget')

    decision = 'unlock_final_render' if not blocked else 'block_final_render'
    out = {
        'preflight_id': f"preflight_{preview_qa.get('preview_id', 'unknown')}",
        'selected_preview_id': preview_qa.get('preview_id'),
        'selected_take_or_variant_id': args.selected_take_or_variant_id,
        'preview_qa_status': preview_qa.get('promotion_decision'),
        'realism_budget_id': realism_budget.get('budget_id'),
        'compute_budget_id': compute_budget.get('compute_budget_id'),
        'ec2_allowed': decision == 'unlock_final_render',
        'blocked_reasons': blocked,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
