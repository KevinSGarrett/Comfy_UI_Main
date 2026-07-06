#!/usr/bin/env python3
"""Validate a Wave08 Character Bible JSON file with no external dependencies."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REQUIRED = [
    'character_id','character_version','status','identity_lock','body_profile',
    'skin_profile','hair_profile','outfit_profile','reference_packs','allowed_engines','qa_goals'
]
VALID_STATUS = {'draft','candidate','active','frozen','superseded','deprecated'}

def validate(path: Path) -> list[str]:
    errors=[]
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return [f'JSON parse failed: {e}']
    for key in REQUIRED:
        if key not in data:
            errors.append(f'missing required field: {key}')
    cid=data.get('character_id','')
    if cid and not re.match(r'^char_[a-z0-9_\-]+$', cid):
        errors.append('character_id must match char_<slug>')
    ver=data.get('character_version','')
    if ver and not re.match(r'^v[0-9]{3}$', ver):
        errors.append('character_version must match v001 format')
    if data.get('status') and data['status'] not in VALID_STATUS:
        errors.append(f'invalid status: {data.get("status")}')
    for arr in ['reference_packs','allowed_engines','qa_goals']:
        if arr in data and not isinstance(data[arr], list):
            errors.append(f'{arr} must be a list')
    return errors

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('character_bible')
    args=ap.parse_args()
    errors=validate(Path(args.character_bible))
    if errors:
        print('FAIL')
        for e in errors: print('-', e)
        return 1
    print('PASS')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
