#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '08_SCHEMAS/wave31_pose_audio_force_event.schema.json',
    '08_SCHEMAS/wave31_spatial_audio_mix.schema.json',
    '08_SCHEMAS/wave31_room_acoustics.schema.json',
    '08_SCHEMAS/wave31_camera_spatial_state.schema.json',
    '08_SCHEMAS/wave31_pose_audio_qa_report.schema.json',
    '09_EXAMPLES/wave31_pose_audio_force_event.example.json',
    '09_EXAMPLES/wave31_spatial_audio_mix.example.json',
    '09_EXAMPLES/wave31_room_acoustics.example.json',
    '09_EXAMPLES/wave31_camera_spatial_state.example.json',
    '09_EXAMPLES/wave31_pose_audio_qa_report.example.json',
    '10_REGISTRIES/wave31_pose_audio_force_taxonomy.json',
    '10_REGISTRIES/wave31_visual_force_to_audio_rules.json',
    '10_REGISTRIES/wave31_spatial_audio_profiles.json',
    '10_REGISTRIES/wave31_room_acoustics_profiles.json',
    '10_REGISTRIES/wave31_occlusion_muffling_rules.json',
    '10_REGISTRIES/wave31_camera_distance_panning_rules.json',
    '10_REGISTRIES/wave31_spatial_audio_qa_scoring_rules.json',
    '10_REGISTRIES/wave31_spatial_audio_rerun_policy.json',
    '10_REGISTRIES/wave31_main_flow_pose_audio_inventory.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/route_wave31_pose_audio_force.py',
    '07_IMPLEMENTATION/scripts/compile_wave31_spatial_mix_manifest.py',
    '07_IMPLEMENTATION/scripts/score_wave31_pose_audio_qa.py',
    '07_IMPLEMENTATION/scripts/run_wave31_local_validation.py',
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
        print('FAIL: Wave31 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave31 pose-to-audio force/spatial audio pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
