#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '10_REGISTRIES/wave28a_micro_motion_decision_rules.json',
    '10_REGISTRIES/wave28a_exertion_fatigue_profiles.json',
    '10_REGISTRIES/wave29_state_domain_registry.json',
    '10_REGISTRIES/wave29_long_form_transition_rules.json',
    '10_REGISTRIES/wave29_fatigue_repetition_rules.json',
    '10_REGISTRIES/wave29_clothing_state_profiles.json',
    '10_REGISTRIES/wave29_variation_controller_rules.json',
    '10_REGISTRIES/wave29_continuity_qa_scoring_rules.json',
    '10_REGISTRIES/wave29_long_form_rerun_policy.json',
    '10_REGISTRIES/wave29_main_flow_continuity_inventory.json',
    '08_SCHEMAS/wave28a_micro_motion_decision.schema.json',
    '08_SCHEMAS/wave29_long_form_state_ledger.schema.json',
    '08_SCHEMAS/wave29_scene_progression.schema.json',
    '08_SCHEMAS/wave29_continuity_evidence.schema.json',
    '09_EXAMPLES/wave28a_micro_motion_decision.example.json',
    '09_EXAMPLES/wave29_long_form_state_ledger.example.json',
    '09_EXAMPLES/wave29_continuity_evidence.example.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/compile_wave29_state_ledger.py',
    '07_IMPLEMENTATION/scripts/decide_wave28a_micro_motion.py',
    '07_IMPLEMENTATION/scripts/score_wave29_continuity_evidence.py',
    '07_IMPLEMENTATION/scripts/run_wave29_local_validation.py',
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
        print('FAIL: Wave29 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave29 long-form continuity + Wave28A micro-motion decision pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
