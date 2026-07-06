#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '08_SCHEMAS/wave33_proxy_preview_plan.schema.json',
    '08_SCHEMAS/wave33_animatic_plan.schema.json',
    '08_SCHEMAS/wave33_realism_budget.schema.json',
    '08_SCHEMAS/wave33_compute_budget.schema.json',
    '08_SCHEMAS/wave33_preview_qa_report.schema.json',
    '08_SCHEMAS/wave33_final_render_preflight.schema.json',
    '08_SCHEMAS/wave33_budget_escalation_record.schema.json',
    '09_EXAMPLES/wave33_proxy_preview_plan.example.json',
    '09_EXAMPLES/wave33_animatic_plan.example.json',
    '09_EXAMPLES/wave33_realism_budget.example.json',
    '09_EXAMPLES/wave33_compute_budget.example.json',
    '09_EXAMPLES/wave33_preview_qa_report.example.json',
    '09_EXAMPLES/wave33_final_render_preflight.example.json',
    '09_EXAMPLES/wave33_budget_escalation_record.example.json',
    '10_REGISTRIES/wave33_preview_tier_registry.json',
    '10_REGISTRIES/wave33_animatic_preview_rules.json',
    '10_REGISTRIES/wave33_realism_budget_profiles.json',
    '10_REGISTRIES/wave33_compute_budget_profiles.json',
    '10_REGISTRIES/wave33_preview_qa_scoring_rules.json',
    '10_REGISTRIES/wave33_final_render_block_policy.json',
    '10_REGISTRIES/wave33_budget_escalation_policy.json',
    '10_REGISTRIES/wave33_preview_rerun_policy.json',
    '10_REGISTRIES/wave33_main_flow_preview_budget_inventory.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/score_wave33_preview_qa.py',
    '07_IMPLEMENTATION/scripts/check_wave33_final_render_preflight.py',
    '07_IMPLEMENTATION/scripts/compile_wave33_budget_escalation.py',
    '07_IMPLEMENTATION/scripts/route_wave33_preview_rerun.py',
    '07_IMPLEMENTATION/scripts/run_wave33_local_validation.py',
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = []
    for rel in REQUIRED_FILES:
        p = root / rel
        if not p.exists():
            errors.append(f'missing required file: {rel}')
        elif p.suffix == '.json':
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except Exception as exc:
                errors.append(f'invalid JSON: {rel}: {exc}')
    for rel in SCRIPTS:
        p = root / rel
        if not p.exists():
            errors.append(f'missing script: {rel}')
        else:
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as exc:
                errors.append(f'script compile failed: {rel}: {exc}')
    if errors:
        print('FAIL: Wave33 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave33 proxy preview/animatic/realism budget pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
