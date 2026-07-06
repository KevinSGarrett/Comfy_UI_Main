#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return len([p for p in path.rglob('*') if p.is_file()])

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--migration-id', required=True)
    parser.add_argument('--source-path', action='append', required=True)
    parser.add_argument('--target-path', action='append', required=True)
    parser.add_argument('--owner-domain', required=True)
    parser.add_argument('--artifact-type', action='append', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    sources = [Path(p) for p in args.source_path]
    targets = [Path(p) for p in args.target_path]
    out = {
        'migration_id': args.migration_id,
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'migration_scope': 'controlled_structure_migration',
        'source_paths': args.source_path,
        'target_paths': args.target_path,
        'owner_domain': args.owner_domain,
        'artifact_types': args.artifact_type,
        'pre_migration_counts': {str(p): count_files(p) for p in sources},
        'post_migration_counts': {str(p): count_files(p) for p in targets},
        'rollback_plan_id': f'rollback_{args.migration_id}',
        'catalog_refresh_required': True,
        'validation_required': ['file_count_match','catalog_refresh','stale_index_pass','owner_domain_mapping'],
        'status': 'generated_plan_not_executed'
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
