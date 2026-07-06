#!/usr/bin/env python3
"""Run Wave08 local validation for schemas, examples, registries, and scripts."""
from __future__ import annotations
import argparse, json, py_compile, subprocess, sys
from pathlib import Path

REQUIRED = [
 '02_TARGET_ARCHITECTURE/WAVE08_CHARACTER_BIBLE_AND_IDENTITY_REGISTRY_ARCHITECTURE.md',
 '02_TARGET_ARCHITECTURE/WAVE08_REFERENCE_PACK_ARCHITECTURE.md',
 '02_TARGET_ARCHITECTURE/WAVE08_CHARACTER_SCENE_DIRECTOR_BINDING.md',
 '08_SCHEMAS/character_bible.schema.json',
 '08_SCHEMAS/character_identity_registry.schema.json',
 '08_SCHEMAS/character_reference_pack.schema.json',
 '09_EXAMPLES/wave08_character_bible.example.json',
 '09_EXAMPLES/wave08_character_identity_registry.example.json',
 '09_EXAMPLES/wave08_reference_pack_manifest.example.json',
 '10_REGISTRIES/wave08_scene_director_character_binding_rules.json'
]

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    args=ap.parse_args()
    root=Path(args.root)
    errors=[]
    for rel in REQUIRED:
        if not (root/rel).exists():
            errors.append(f'missing required file: {rel}')
    json_count=0
    for p in root.rglob('*.json'):
        try:
            json.loads(p.read_text(encoding='utf-8'))
            json_count += 1
        except Exception as e:
            errors.append(f'json parse failed: {p.relative_to(root)}: {e}')
    py_count=0
    for p in (root/'07_IMPLEMENTATION'/'scripts').glob('*.py'):
        try:
            py_compile.compile(str(p), doraise=True)
            py_count += 1
        except Exception as e:
            errors.append(f'python compile failed: {p.relative_to(root)}: {e}')
    # Character example consistency
    cb=json.loads((root/'09_EXAMPLES/wave08_character_bible.example.json').read_text(encoding='utf-8'))
    reg=json.loads((root/'09_EXAMPLES/wave08_character_identity_registry.example.json').read_text(encoding='utf-8'))
    rp=json.loads((root/'09_EXAMPLES/wave08_reference_pack_manifest.example.json').read_text(encoding='utf-8'))
    cid=cb.get('character_id')
    if not any(c.get('character_id')==cid for c in reg.get('characters',[])):
        errors.append('example registry does not include example character_id')
    if rp.get('character_id') != cid:
        errors.append('reference pack example character_id mismatch')
    result={'status':'FAIL' if errors else 'PASS','json_files_checked':json_count,'python_scripts_checked':py_count,'errors':errors}
    print(json.dumps(result, indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
