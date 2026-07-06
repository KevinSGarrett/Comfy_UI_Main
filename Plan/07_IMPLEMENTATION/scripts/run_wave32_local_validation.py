#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '08_SCHEMAS/wave32_planned_state.schema.json',
    '08_SCHEMAS/wave32_generated_state.schema.json',
    '08_SCHEMAS/wave32_state_diff_report.schema.json',
    '08_SCHEMAS/wave32_revision_take_variant_ledger.schema.json',
    '08_SCHEMAS/wave32_targeted_rerun_plan.schema.json',
    '08_SCHEMAS/wave32_successful_run_learning.schema.json',
    '08_SCHEMAS/wave32_state_diff_qa_report.schema.json',
    '09_EXAMPLES/wave32_planned_state.example.json',
    '09_EXAMPLES/wave32_generated_state.example.json',
    '09_EXAMPLES/wave32_state_diff_report.example.json',
    '09_EXAMPLES/wave32_revision_take_variant_ledger.example.json',
    '09_EXAMPLES/wave32_targeted_rerun_plan.example.json',
    '09_EXAMPLES/wave32_successful_run_learning.example.json',
    '09_EXAMPLES/wave32_state_diff_qa_report.example.json',
    '10_REGISTRIES/wave32_state_domain_registry.json',
    '10_REGISTRIES/wave32_state_diff_status_taxonomy.json',
    '10_REGISTRIES/wave32_revision_policy.json',
    '10_REGISTRIES/wave32_take_variant_policy.json',
    '10_REGISTRIES/wave32_targeted_rerun_rules.json',
    '10_REGISTRIES/wave32_successful_run_learning_rules.json',
    '10_REGISTRIES/wave32_variant_selection_scoring_rules.json',
    '10_REGISTRIES/wave32_state_diff_rerun_policy.json',
    '10_REGISTRIES/wave32_main_flow_state_diff_inventory.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/compile_wave32_state_diff.py',
    '07_IMPLEMENTATION/scripts/plan_wave32_targeted_rerun.py',
    '07_IMPLEMENTATION/scripts/score_wave32_state_diff_qa.py',
    '07_IMPLEMENTATION/scripts/record_wave32_successful_run_learning.py',
    '07_IMPLEMENTATION/scripts/run_wave32_local_validation.py',
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
        print('FAIL: Wave32 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave32 state diff/revision/take/variant pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
