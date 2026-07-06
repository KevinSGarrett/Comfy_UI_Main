#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '08_SCHEMAS/wave30_audio_event_manifest.schema.json',
    '08_SCHEMAS/wave30_voice_dialogue_contract.schema.json',
    '08_SCHEMAS/wave30_breathing_foley_sfx_contract.schema.json',
    '08_SCHEMAS/wave30_audio_mix_manifest.schema.json',
    '08_SCHEMAS/wave30_audio_qa_report.schema.json',
    '09_EXAMPLES/wave30_audio_event_manifest.example.json',
    '09_EXAMPLES/wave30_voice_dialogue_contract.example.json',
    '09_EXAMPLES/wave30_breathing_foley_sfx_contract.example.json',
    '09_EXAMPLES/wave30_audio_mix_manifest.example.json',
    '09_EXAMPLES/wave30_audio_qa_report.example.json',
    '10_REGISTRIES/wave30_audio_event_taxonomy.json',
    '10_REGISTRIES/wave30_voice_profile_registry.json',
    '10_REGISTRIES/wave30_breathing_audio_profiles.json',
    '10_REGISTRIES/wave30_foley_material_profiles.json',
    '10_REGISTRIES/wave30_ambience_music_profiles.json',
    '10_REGISTRIES/wave30_action_linked_sfx_rules.json',
    '10_REGISTRIES/wave30_audio_qa_scoring_rules.json',
    '10_REGISTRIES/wave30_audio_rerun_policy.json',
    '10_REGISTRIES/wave30_main_flow_audio_inventory.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/compile_wave30_audio_event_manifest.py',
    '07_IMPLEMENTATION/scripts/score_wave30_audio_qa.py',
    '07_IMPLEMENTATION/scripts/route_wave30_action_linked_sfx.py',
    '07_IMPLEMENTATION/scripts/run_wave30_local_validation.py',
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
        print('FAIL: Wave30 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave30 audio generation pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
