#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--file-catalog', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    catalog = json.loads(Path(args.file_catalog).read_text(encoding='utf-8'))
    catalog_paths = {entry['path'] for entry in catalog.get('files', [])}
    disk_paths = {str(p.relative_to(root)).replace('\\', '/') for p in root.rglob('*') if p.is_file() and '__pycache__' not in str(p)}

    # Ignore generated catalog outputs themselves to avoid self-reference churn.
    ignored_prefix = '14_ORGANIZATION_SYSTEM/GENERATED_INDEXES/WAVE36_EXPANDED/'
    catalog_paths_filtered = {p for p in catalog_paths if not p.startswith(ignored_prefix)}
    disk_paths_filtered = {p for p in disk_paths if not p.startswith(ignored_prefix)}

    missing_on_disk = sorted(catalog_paths_filtered - disk_paths_filtered)
    missing_in_catalog = sorted(disk_paths_filtered - catalog_paths_filtered)

    blocking = []
    if missing_on_disk:
        blocking.append('catalog_references_missing_disk_files')
    # Missing in catalog can occur after new files were generated; flag only if non-generated important files.
    important_missing = [p for p in missing_in_catalog if not p.startswith('14_ORGANIZATION_SYSTEM/ORGANIZATION_VALIDATION/')]
    if important_missing:
        blocking.append('disk_files_missing_from_catalog')

    report = {
        'report_id': 'wave36_stale_index_detection',
        'checked_catalogs': ['file_catalog'],
        'stale_flags': [{'type': 'missing_on_disk', 'paths': missing_on_disk[:200]}, {'type': 'missing_in_catalog', 'paths': missing_in_catalog[:200]}],
        'blocking_flags': blocking,
        'promotion_decision': 'pass' if not blocking else 'block'
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if not blocking else 1

if __name__ == '__main__':
    raise SystemExit(main())
