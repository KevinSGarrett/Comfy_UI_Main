#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--readiness-report', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    readiness = json.loads(Path(args.readiness_report).read_text(encoding='utf-8'))

    out = {
        'handoff_id': 'wave37_expanded_final_handoff',
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'local_directory_map': '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_LOCAL_DIRECTORY_STRUCTURE.md',
        'repo_structure_map': '14_ORGANIZATION_SYSTEM/WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_DETAILED_REPO_STRUCTURE.md',
        'comfyui_runtime_map': '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_COMFYUI_RUNTIME_HANDOFF_PACKET.md',
        'app_mode_map': '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_APP_MODE_HANDOFF_PACKET.md',
        'catalog_refs': [
            '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_master_project_index.json',
            '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_file_catalog.json',
            '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_search_index.json',
            '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/wave36_expanded_stale_index_report.json'
        ],
        'migration_refs': [
            '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_CONTROLLED_LOCAL_MIGRATION_RUNBOOK.md',
            '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_MIGRATION_ROLLBACK_AND_BACKUP_PLAN.md'
        ],
        'governance_refs': [
            '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_GOVERNANCE_RULES_FOR_FUTURE_WAVES.md',
            '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_FOLDER_OWNERSHIP_GOVERNANCE.md',
            '14_ORGANIZATION_SYSTEM/WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_ARCHIVE_DEPRECATION_GOVERNANCE.md'
        ],
        'validation_refs': [
            args.readiness_report,
            '14_ORGANIZATION_SYSTEM/ORGANIZATION_VALIDATION/wave37_expanded_validation_report.json'
        ],
        'release_decision': readiness.get('promotion_decision'),
        'remaining_runtime_proof': [
            'organization handoff readiness is structural proof only',
            'runtime image proof remains governed by runtime output/evidence gates',
            'runtime video/GIF proof remains required later if used',
            'runtime audio proof remains required later if used',
            'EC2 final render remains gated by preview QA and final preflight'
        ]
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
