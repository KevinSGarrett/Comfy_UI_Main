#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--search-index', required=True)
    parser.add_argument('--query', required=True)
    parser.add_argument('--limit', type=int, default=25)
    args = parser.parse_args()

    idx = json.loads(Path(args.search_index).read_text(encoding='utf-8'))
    q = args.query.lower()
    results = []
    for entry in idx.get('entries', []):
        text = ' '.join([
            str(entry.get('artifact_id','')),
            str(entry.get('artifact_type','')),
            str(entry.get('path','')),
            str(entry.get('title','')),
            ' '.join(entry.get('tags', [])),
            str(entry.get('owner_domain','')),
            str(entry.get('status','')),
            str(entry.get('proof_status','')),
        ]).lower()
        if q in text:
            results.append(entry)
            if len(results) >= args.limit:
                break
    print(json.dumps({'query': args.query, 'count': len(results), 'results': results}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
