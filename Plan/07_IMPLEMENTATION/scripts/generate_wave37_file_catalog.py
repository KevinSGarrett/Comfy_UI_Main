#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = []
    for p in sorted(root.rglob('*')):
        if not p.is_file() or '__pycache__' in str(p):
            continue
        rel = str(p.relative_to(root)).replace('\\', '/')
        files.append({
            'path': rel,
            'extension': p.suffix.lower() or '[no_ext]',
            'top_level_directory': rel.split('/')[0],
            'size_bytes': p.stat().st_size
        })
    out = {'catalog_id': 'generated_file_catalog', 'file_count': len(files), 'files': files}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
