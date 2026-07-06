#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()

    structure_required = [
        '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_LOCAL_DIRECTORY_STRUCTURE.md',
        '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_REPO_STRUCTURE.md',
        '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_COMFYUI_RUNTIME_STRUCTURE.md',
        '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_APP_MODE_PACKAGE_STRUCTURE_DETAILED.md',
    ]
    catalog_required = [
        '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_master_project_index.json',
        '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_file_catalog.json',
        '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_search_index.json',
        '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_stale_index_report.json',
    ]
    handoff_required = [
        '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_COMFYUI_RUNTIME_HANDOFF_PACKET.md',
        '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_APP_MODE_HANDOFF_PACKET.md',
        '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_LOCAL_EC2_SYNC_BOUNDARY_RUNBOOK.md',
        '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_FINAL_HANDOFF_PACKET_EXPANDED.md',
    ]

    missing_structure = [p for p in structure_required if not exists(root, p)]
    missing_catalog = [p for p in catalog_required if not exists(root, p)]
    missing_handoff = [p for p in handoff_required if not exists(root, p)]

    blockers = []
    if missing_structure:
        blockers.append('missing_structure_docs')
    if missing_catalog:
        blockers.append('missing_catalog_outputs')
    if missing_handoff:
        blockers.append('missing_handoff_docs')

    stale_report_path = root / '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_stale_index_report.json'
    if stale_report_path.exists():
        stale = json.loads(stale_report_path.read_text(encoding='utf-8'))
        if stale.get('promotion_decision') != 'pass':
            blockers.append('stale_index_report_not_pass')
    else:
        blockers.append('missing_stale_index_report')

    out = {
        'readiness_id': 'wave37_expanded_release_readiness',
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'structure_readiness': 'pass' if not missing_structure else 'missing_items',
        'catalog_readiness': 'pass' if not missing_catalog else 'missing_items',
        'migration_readiness': 'not_performed_or_not_required',
        'runtime_boundary_readiness': 'explicit',
        'handoff_readiness': 'pass' if not missing_handoff else 'missing_items',
        'missing_structure': missing_structure,
        'missing_catalog': missing_catalog,
        'missing_handoff': missing_handoff,
        'blocking_items': blockers,
        'promotion_decision': 'organization_handoff_ready' if not blockers else 'repair_required'
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0 if not blockers else 1

if __name__ == '__main__':
    raise SystemExit(main())
