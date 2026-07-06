#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_DOCS = [
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_EXPANDED_MIGRATION_GOVERNANCE_HANDOFF_ARCHITECTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_CONTROLLED_LOCAL_MIGRATION_RUNBOOK.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_MIGRATION_ROLLBACK_AND_BACKUP_PLAN.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_REPO_CLEANUP_SOURCE_CONTROL_HARDENING.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_COMFYUI_RUNTIME_HANDOFF_PACKET.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_APP_MODE_HANDOFF_PACKET.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_LOCAL_EC2_SYNC_BOUNDARY_RUNBOOK.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_GOVERNANCE_RULES_FOR_FUTURE_WAVES.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_FOLDER_OWNERSHIP_GOVERNANCE.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_ARCHIVE_DEPRECATION_GOVERNANCE.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_ORGANIZATION_VALIDATION_AND_CERTIFICATION.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_FINAL_HANDOFF_PACKET_EXPANDED.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_RELEASE_READINESS_CHECKLIST_EXPANDED.md',
]
REQUIRED_JSON = [
    '08_SCHEMAS/wave37_expanded_migration_manifest.schema.json',
    '08_SCHEMAS/wave37_expanded_rollback_plan.schema.json',
    '08_SCHEMAS/wave37_expanded_repo_cleanup_manifest.schema.json',
    '08_SCHEMAS/wave37_expanded_comfyui_handoff.schema.json',
    '08_SCHEMAS/wave37_expanded_app_mode_handoff.schema.json',
    '08_SCHEMAS/wave37_expanded_ec2_sync_manifest.schema.json',
    '08_SCHEMAS/wave37_expanded_governance_record.schema.json',
    '08_SCHEMAS/wave37_expanded_release_readiness_report.schema.json',
    '08_SCHEMAS/wave37_expanded_final_handoff_packet.schema.json',
    '10_REGISTRIES/wave37_expanded_migration_phase_registry.json',
    '10_REGISTRIES/wave37_expanded_repo_cleanup_registry.json',
    '10_REGISTRIES/wave37_expanded_handoff_packet_registry.json',
    '10_REGISTRIES/wave37_expanded_ec2_sync_boundary_registry.json',
    '10_REGISTRIES/wave37_expanded_governance_rule_registry.json',
    '10_REGISTRIES/wave37_expanded_archive_deprecation_registry.json',
    '10_REGISTRIES/wave37_expanded_validation_gate_registry.json',
    '10_REGISTRIES/wave37_expanded_release_readiness_registry.json',
    '14_ORGANIZATION_SYSTEM/ORGANIZATION_VALIDATION/WAVE37_EXPANDED/wave37_expanded_release_readiness_report.json',
    '14_ORGANIZATION_SYSTEM/ORGANIZATION_VALIDATION/WAVE37_EXPANDED/wave37_expanded_final_handoff_packet.json',
]
REQUIRED_SCRIPTS = [
    '07_IMPLEMENTATION/scripts/generate_wave37_expanded_migration_manifest.py',
    '07_IMPLEMENTATION/scripts/generate_wave37_expanded_release_readiness.py',
    '07_IMPLEMENTATION/scripts/generate_wave37_expanded_final_handoff_packet.py',
    '07_IMPLEMENTATION/scripts/validate_wave37_expanded_migration_governance_handoff.py',
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = []
    invalid_json = []
    script_failures = []

    for rel in REQUIRED_DOCS:
        if not (root / rel).exists():
            errors.append(f'missing required doc: {rel}')

    for rel in REQUIRED_JSON:
        p = root / rel
        if not p.exists():
            errors.append(f'missing required JSON: {rel}')
        else:
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except Exception as exc:
                invalid_json.append(f'{rel}: {exc}')

    for rel in REQUIRED_SCRIPTS:
        p = root / rel
        if not p.exists():
            errors.append(f'missing script: {rel}')
        else:
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as exc:
                script_failures.append(f'{rel}: {exc}')

    readiness_path = root / '14_ORGANIZATION_SYSTEM/ORGANIZATION_VALIDATION/WAVE37_EXPANDED/wave37_expanded_release_readiness_report.json'
    readiness_decision = None
    if readiness_path.exists():
        readiness = json.loads(readiness_path.read_text(encoding='utf-8'))
        readiness_decision = readiness.get('promotion_decision')
        if readiness_decision != 'organization_handoff_ready':
            errors.append('release readiness did not pass')

    report = {
        'validation_id': 'wave37_expanded_migration_governance_handoff_validation',
        'checked_required_docs': len(REQUIRED_DOCS),
        'checked_required_json': len(REQUIRED_JSON),
        'checked_required_scripts': len(REQUIRED_SCRIPTS),
        'missing_items': errors,
        'invalid_json': invalid_json,
        'script_failures': script_failures,
        'readiness_decision': readiness_decision,
        'promotion_decision': 'pass' if not errors and not invalid_json and not script_failures else 'fail'
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    if report['promotion_decision'] != 'pass':
        print('FAIL: Wave37 expanded migration/governance/handoff validation failed')
        for err in errors + invalid_json + script_failures:
            print('-', err)
        return 1

    print('PASS: Wave37 expanded migration/governance/validation/handoff system validated')
    print(f'Required docs checked: {len(REQUIRED_DOCS)}')
    print(f'Required JSON checked: {len(REQUIRED_JSON)}')
    print(f'Scripts checked: {len(REQUIRED_SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
