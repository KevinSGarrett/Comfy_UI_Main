#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '10_REGISTRIES/wave27_video_engine_registry.json',
    '10_REGISTRIES/wave27_video_route_selection_rules.json',
    '10_REGISTRIES/wave27_temporal_qa_scoring_rules.json',
    '10_REGISTRIES/wave27_frame_repair_policy.json',
    '10_REGISTRIES/wave27_main_flow_video_routing_inventory.json',
    '08_SCHEMAS/wave27_frame_manifest.schema.json',
    '08_SCHEMAS/wave27_temporal_evidence.schema.json',
    '09_EXAMPLES/wave27_frame_manifest.example.json',
    '09_EXAMPLES/wave27_temporal_evidence.example.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/compile_wave27_frame_manifest.py',
    '07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py',
    '07_IMPLEMENTATION/scripts/run_wave27_local_validation.py',
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors=[]
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
        print('FAIL: Wave27 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave27 video routing/temporal QA pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
