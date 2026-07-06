#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_DOCS = [
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_EXPANDED_CANONICAL_SYSTEM_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_LOCAL_DIRECTORY_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_REPO_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_COMFYUI_RUNTIME_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_WORKFLOW_LIBRARY_CONTROLLED_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_APP_MODE_PACKAGE_STRUCTURE_DETAILED.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_SOURCE_OF_TRUTH_BOUNDARY_MATRIX.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_LOCAL_REPO_COMFYUI_APP_MAPPING.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_MODEL_LORA_ASSET_BOUNDARY_POLICY.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_GENERATED_OUTPUT_SEPARATION_POLICY.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_ENV_CONFIG_SECRETS_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_ARCHIVE_DEPRECATION_STRUCTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_CANONICAL_PATH_ALIAS_SYSTEM.md',
    '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_FOLDER_OWNERSHIP_ALLOWED_CONTENT.md',
]
REQUIRED_JSON = [
    '08_SCHEMAS/wave35_expanded_canonical_directory.schema.json',
    '08_SCHEMAS/wave35_expanded_path_alias.schema.json',
    '08_SCHEMAS/wave35_expanded_source_of_truth.schema.json',
    '08_SCHEMAS/wave35_expanded_workflow_library_entry.schema.json',
    '08_SCHEMAS/wave35_expanded_app_mode_control_entry.schema.json',
    '08_SCHEMAS/wave35_expanded_folder_validation_report.schema.json',
    '09_EXAMPLES/wave35_expanded_canonical_directory.example.json',
    '09_EXAMPLES/wave35_expanded_path_alias.example.json',
    '09_EXAMPLES/wave35_expanded_source_of_truth.example.json',
    '09_EXAMPLES/wave35_expanded_workflow_library_entry.example.json',
    '09_EXAMPLES/wave35_expanded_app_mode_control_entry.example.json',
    '10_REGISTRIES/wave35_expanded_owner_domain_registry.json',
    '10_REGISTRIES/wave35_expanded_canonical_path_alias_registry.json',
    '10_REGISTRIES/wave35_expanded_local_directory_registry.json',
    '10_REGISTRIES/wave35_expanded_repo_directory_registry.json',
    '10_REGISTRIES/wave35_expanded_comfyui_runtime_registry.json',
    '10_REGISTRIES/wave35_expanded_workflow_library_registry.json',
    '10_REGISTRIES/wave35_expanded_app_mode_structure_registry.json',
    '10_REGISTRIES/wave35_expanded_source_of_truth_registry.json',
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors = []
    invalid_json = []
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
    # compile this validator itself
    try:
        py_compile.compile(str(Path(__file__)), doraise=True)
    except Exception as exc:
        errors.append(f'validator compile failed: {exc}')

    report = {
        'validation_id': 'wave35_expanded_structure_validation',
        'checked_required_docs': len(REQUIRED_DOCS),
        'checked_required_json': len(REQUIRED_JSON),
        'checked_required_scripts': 1,
        'missing_items': errors,
        'invalid_json': invalid_json,
        'script_failures': [],
        'promotion_decision': 'pass' if not errors and not invalid_json else 'fail'
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    if errors or invalid_json:
        print('FAIL: Wave35 expanded structure validation failed')
        for err in errors + invalid_json:
            print('-', err)
        return 1

    print('PASS: Wave35 expanded canonical system structure validated')
    print(f'Required docs checked: {len(REQUIRED_DOCS)}')
    print(f'Required JSON checked: {len(REQUIRED_JSON)}')
    print('Scripts checked: 1')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
