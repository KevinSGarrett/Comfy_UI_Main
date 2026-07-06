#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '10_REGISTRIES/wave28_micro_motion_taxonomy.json',
    '10_REGISTRIES/wave28_breathing_profiles.json',
    '10_REGISTRIES/wave28_gaze_grip_profiles.json',
    '10_REGISTRIES/wave28_hair_secondary_motion_profiles.json',
    '10_REGISTRIES/wave28_bounce_ripple_rebound_profiles.json',
    '10_REGISTRIES/wave28_micro_motion_qa_scoring_rules.json',
    '10_REGISTRIES/wave28_micro_motion_rerun_policy.json',
    '10_REGISTRIES/wave28_main_flow_micro_motion_inventory.json',
    '08_SCHEMAS/wave28_micro_motion_manifest.schema.json',
    '08_SCHEMAS/wave28_micro_motion_evidence.schema.json',
    '09_EXAMPLES/wave28_micro_motion_manifest.example.json',
    '09_EXAMPLES/wave28_micro_motion_evidence.example.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/compile_wave28_micro_motion_manifest.py',
    '07_IMPLEMENTATION/scripts/score_wave28_micro_motion_evidence.py',
    '07_IMPLEMENTATION/scripts/run_wave28_local_validation.py',
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
        print('FAIL: Wave28 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave28 micro-motion/secondary-motion pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
