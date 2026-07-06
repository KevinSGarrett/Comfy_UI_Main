#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_DOCS = [
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_EXPANDED_CATALOG_INDEX_ARCHITECTURE.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_MASTER_PROJECT_INDEX_EXPANDED.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_FILE_CATALOG_EXPANDED_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_WORKFLOW_CATALOG_EXPANDED_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_ASSET_CATALOG_EXPANDED_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_QA_EVIDENCE_CATALOG_EXPANDED_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_REGISTRY_AND_SEARCH_METADATA_SYSTEM.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_STALE_INDEX_POLICY_EXPANDED.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_CATALOG_REFRESH_PIPELINE.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_DISCOVERY_SEARCH_TAGGING_STANDARD.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_APP_MODE_SEARCH_AND_CATALOG_BINDING.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_EC2_SYNC_CATALOG_BINDING.md',
    '14_ORGANIZATION_SYSTEM/WAVE36_CATALOGS_INDEXES/EXPANDED/WAVE36_CATALOG_PROMOTION_GATE_MODEL.md',
]
REQUIRED_JSON = [
    '08_SCHEMAS/wave36_expanded_master_project_index.schema.json',
    '08_SCHEMAS/wave36_expanded_file_catalog.schema.json',
    '08_SCHEMAS/wave36_expanded_workflow_catalog.schema.json',
    '08_SCHEMAS/wave36_expanded_asset_catalog.schema.json',
    '08_SCHEMAS/wave36_expanded_qa_evidence_catalog.schema.json',
    '08_SCHEMAS/wave36_expanded_search_index.schema.json',
    '08_SCHEMAS/wave36_expanded_stale_index_report.schema.json',
    '08_SCHEMAS/wave36_expanded_catalog_refresh_report.schema.json',
    '10_REGISTRIES/wave36_expanded_catalog_owner_registry.json',
    '10_REGISTRIES/wave36_expanded_search_field_registry.json',
    '10_REGISTRIES/wave36_expanded_artifact_type_taxonomy.json',
    '10_REGISTRIES/wave36_expanded_stale_index_detection_rules.json',
    '10_REGISTRIES/wave36_expanded_index_promotion_gate_registry.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_master_project_index.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_file_catalog.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_workflow_catalog.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_asset_catalog.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_qa_evidence_catalog.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_search_index.json',
    '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_stale_index_report.json',
]
REQUIRED_SCRIPTS = [
    '07_IMPLEMENTATION/scripts/generate_wave36_expanded_catalogs.py',
    '07_IMPLEMENTATION/scripts/search_wave36_expanded_catalogs.py',
    '07_IMPLEMENTATION/scripts/detect_wave36_stale_indexes.py',
    '07_IMPLEMENTATION/scripts/validate_wave36_expanded_catalog_system.py',
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

    stale_path = root / '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_stale_index_report.json'
    stale_blockers = []
    if stale_path.exists():
        stale = json.loads(stale_path.read_text(encoding='utf-8'))
        stale_blockers = stale.get('blocking_flags', [])
        if stale.get('promotion_decision') != 'pass':
            errors.append('stale index report did not pass')

    report = {
        'validation_id': 'wave36_expanded_catalog_system_validation',
        'checked_required_docs': len(REQUIRED_DOCS),
        'checked_required_json': len(REQUIRED_JSON),
        'checked_required_scripts': len(REQUIRED_SCRIPTS),
        'missing_items': errors,
        'invalid_json': invalid_json,
        'script_failures': script_failures,
        'stale_blockers': stale_blockers,
        'promotion_decision': 'pass' if not errors and not invalid_json and not script_failures and not stale_blockers else 'fail'
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    if report['promotion_decision'] != 'pass':
        print('FAIL: Wave36 expanded catalog system validation failed')
        for err in errors + invalid_json + script_failures + stale_blockers:
            print('-', err)
        return 1

    print('PASS: Wave36 expanded index/catalog/registry/search system validated')
    print(f'Required docs checked: {len(REQUIRED_DOCS)}')
    print(f'Required JSON checked: {len(REQUIRED_JSON)}')
    print(f'Scripts checked: {len(REQUIRED_SCRIPTS)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
