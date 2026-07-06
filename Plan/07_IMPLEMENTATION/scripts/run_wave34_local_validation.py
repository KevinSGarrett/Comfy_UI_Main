#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_FILES = [
    '08_SCHEMAS/wave34_app_mode_release_contract.schema.json',
    '08_SCHEMAS/wave34_orchestrator_release_plan.schema.json',
    '08_SCHEMAS/wave34_local_proof_report.schema.json',
    '08_SCHEMAS/wave34_ec2_proof_report.schema.json',
    '08_SCHEMAS/wave34_qa_certification_packet.schema.json',
    '08_SCHEMAS/wave34_release_manifest.schema.json',
    '08_SCHEMAS/wave34_final_handoff_packet.schema.json',
    '08_SCHEMAS/wave34_release_gate_decision.schema.json',
    '09_EXAMPLES/wave34_app_mode_release_contract.example.json',
    '09_EXAMPLES/wave34_orchestrator_release_plan.example.json',
    '09_EXAMPLES/wave34_local_proof_report.example.json',
    '09_EXAMPLES/wave34_ec2_proof_report.example.json',
    '09_EXAMPLES/wave34_qa_certification_packet.example.json',
    '09_EXAMPLES/wave34_release_manifest.example.json',
    '09_EXAMPLES/wave34_final_handoff_packet.example.json',
    '09_EXAMPLES/wave34_release_gate_decision.example.json',
    '10_REGISTRIES/wave34_app_mode_control_registry.json',
    '10_REGISTRIES/wave34_orchestrator_stage_registry.json',
    '10_REGISTRIES/wave34_proof_gate_requirements.json',
    '10_REGISTRIES/wave34_qa_certification_scoring_rules.json',
    '10_REGISTRIES/wave34_release_manifest_requirements.json',
    '10_REGISTRIES/wave34_release_block_policy.json',
    '10_REGISTRIES/wave34_final_handoff_registry.json',
    '10_REGISTRIES/wave34_final_integration_inventory.json',
    '11_RELEASES/WAVE34_FINAL_RELEASE_CHECKLIST.md',
    '11_RELEASES/WAVE34_FINAL_HANDOFF.md',
    '11_RELEASES/WAVE34_RELEASE_MANIFEST.json',
    '11_RELEASES/WAVE34_RELEASE_GATE_DECISION.json',
    '11_RELEASES/WAVE34_QA_CERTIFICATION_PACKET.json',
]
SCRIPTS = [
    '07_IMPLEMENTATION/scripts/compile_wave34_release_manifest.py',
    '07_IMPLEMENTATION/scripts/check_wave34_proof_gates.py',
    '07_IMPLEMENTATION/scripts/score_wave34_qa_certification.py',
    '07_IMPLEMENTATION/scripts/decide_wave34_release_gate.py',
    '07_IMPLEMENTATION/scripts/run_wave34_local_validation.py',
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
        elif p.suffix.lower() == '.json':
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

    # Explicit release block sanity checks
    block_policy = root / '10_REGISTRIES/wave34_release_block_policy.json'
    if block_policy.exists():
        policy = json.loads(block_policy.read_text(encoding='utf-8'))
        if 'runtime_certification_claimed_without_runtime_artifacts' not in policy.get('block_conditions', []):
            errors.append('release block policy missing runtime proof block')
        if 'final_render_unlocked_without_preview_QA_and_preflight' not in policy.get('block_conditions', []):
            errors.append('release block policy missing preflight block')

    if errors:
        print('FAIL: Wave34 validation failed')
        for err in errors:
            print('-', err)
        return 1
    print('PASS: Wave34 final integration/release pack validated')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Scripts checked: {len(SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
