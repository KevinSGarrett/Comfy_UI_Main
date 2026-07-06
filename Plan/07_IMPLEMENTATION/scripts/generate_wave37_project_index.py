#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from collections import Counter

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    out = {
        'index_id': 'generated_project_index',
        'source_root': str(root),
        'file_count': len(files),
        'json_count': len([p for p in files if p.suffix.lower() == '.json']),
        'python_count': len([p for p in files if p.suffix.lower() == '.py']),
        'top_level_directories': [
            {'directory': k, 'file_count': v}
            for k, v in sorted(Counter(p.relative_to(root).parts[0] for p in files if p.relative_to(root).parts).items())
        ],
        'extension_counts': dict(Counter(p.suffix.lower() or '[no_ext]' for p in files).most_common(50))
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
