#!/usr/bin/env python3
"""Build a simple reference pack file-hash manifest from a character pack folder."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

MEDIA_EXTS = {'.png','.jpg','.jpeg','.webp','.tif','.tiff','.bmp','.mp3','.wav','.flac','.ogg','.json','.txt'}

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def infer_asset_type(rel: str) -> str:
    s=rel.replace('\\','/').lower()
    if '/face' in s: return 'face_reference_or_mask'
    if '/hair' in s: return 'hair_reference_or_mask'
    if '/body' in s: return 'body_reference_or_mask'
    if '/skin' in s: return 'skin_reference_or_mask'
    if '/outfit' in s: return 'outfit_reference_or_mask'
    if '/voice' in s or s.endswith(('.wav','.mp3','.flac','.ogg')): return 'voice_reference'
    if '/approved/' in s: return 'approved_reference'
    if '/raw/' in s: return 'raw_reference'
    if '/rejected/' in s: return 'rejected_reference'
    return 'supporting_asset'

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='Character pack version root')
    ap.add_argument('--character-id', required=True)
    ap.add_argument('--character-version', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    root=Path(args.root)
    assets=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file(): continue
        if path.suffix.lower() not in MEDIA_EXTS: continue
        rel=path.relative_to(root).as_posix()
        assets.append({
            'asset_id': rel.replace('/','_').replace('.','_'),
            'asset_type': infer_asset_type(rel),
            'approval_status': 'approved' if '/approved/' in f'/{rel}' else ('rejected' if '/rejected/' in f'/{rel}' else 'raw' if '/raw/' in f'/{rel}' else 'candidate'),
            'path_local': rel,
            'size_bytes': path.stat().st_size,
            'sha256': sha256_file(path),
            'runtime_consumer': []
        })
    manifest={
        'reference_pack_id': f'refpack_{args.character_id}_{args.character_version}',
        'character_id': args.character_id,
        'character_version': args.character_version,
        'pack_version': '001',
        'status': 'candidate',
        'root_path_local': str(root),
        'assets': assets
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Wrote {out} with {len(assets)} assets')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
