#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_PATHS = [
    '14_ORGANIZATION_SYSTEM/README.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/WAVE35_CANONICAL_SYSTEM_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/WAVE35_LOCAL_DIRECTORY_BLUEPRINT.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/WAVE35_REPO_STRUCTURE_BLUEPRINT.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/WAVE35_COMFYUI_RUNTIME_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/WAVE35_APP_MODE_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/WAVE36_CATALOG_INDEX_ARCHITECTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/WAVE36_MASTER_PROJECT_INDEX.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/WAVE36_WORKFLOW_CATALOG_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/WAVE36_ASSET_CATALOG_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/WAVE37_MIGRATION_GOVERNANCE_HANDOFF_ARCHITECTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/WAVE37_LOCAL_DIRECTORY_MIGRATION_PLAN.md',
    '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/WAVE37_FINAL_ORGANIZATION_HANDOFF.md',
    '10_REGISTRIES/wave35_canonical_directory_registry.json',
    '10_REGISTRIES/wave36_catalog_registry.json',
    '10_REGISTRIES/wave37_migration_governance_registry.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/wave37_master_project_index.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/wave37_file_catalog.json',
]
REQUIRED_SCRIPTS = [
    '07_IMPLEMENTATION/scripts/generate_wave37_project_index.py',
    '07_IMPLEMENTATION/scripts/generate_wave37_file_catalog.py',
    '07_IMPLEMENTATION/scripts/validate_wave37_organization.py',
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = []
    checked_json = 0
    checked_scripts = 0

    for rel in REQUIRED_PATHS:
        p = root / rel
        if not p.exists():
            errors.append(f'missing required path: {rel}')
        elif p.suffix.lower() == '.json':
            checked_json += 1
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except Exception as exc:
                errors.append(f'invalid JSON: {rel}: {exc}')

    for rel in REQUIRED_SCRIPTS:
        p = root / rel
        if not p.exists():
            errors.append(f'missing script: {rel}')
        else:
            checked_scripts += 1
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as exc:
                errors.append(f'script compile failed: {rel}: {exc}')

    report = {
        'validation_id': 'wave37_organization_validation',
        'checked_files': len(REQUIRED_PATHS),
        'checked_json': checked_json,
        'checked_scripts': checked_scripts,
        'missing_required_paths': [e for e in errors if e.startswith('missing')],
        'stale_catalog_flags': [],
        'errors': errors,
        'promotion_decision': 'pass' if not errors else 'fail'
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    if errors:
        print('FAIL: Wave37 organization validation failed')
        for err in errors:
            print('-', err)
        return 1

    print('PASS: Wave35-37 organization structure/catalog pack validated')
    print(f'Required paths checked: {len(REQUIRED_PATHS)}')
    print(f'JSON files checked: {checked_json}')
    print(f'Scripts checked: {checked_scripts}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
