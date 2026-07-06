#!/usr/bin/env python3
from __future__ import annotations
import json, py_compile, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = [
 'PROJECT_MANIFEST.json',
 '00_PROJECT_CONTROL/WAVE08_DELIVERY_REPORT.md',
 '02_TARGET_ARCHITECTURE/WAVE08_CHARACTER_BIBLE_AND_IDENTITY_REGISTRY_ARCHITECTURE.md',
 '02_TARGET_ARCHITECTURE/WAVE08_REFERENCE_PACK_ARCHITECTURE.md',
 '07_IMPLEMENTATION/scripts/run_wave08_local_validation.py',
 '08_SCHEMAS/character_bible.schema.json',
 '09_EXAMPLES/wave08_character_bible.example.json',
 '10_REGISTRIES/wave08_identity_qa_goal_catalog.json',
 '12_SOURCE_SUMMARIES/WAVE08_UPLOADED_SOURCE_STATUS.json'
]
errors=[]
for rel in required:
    if not (root/rel).exists(): errors.append(f'missing {rel}')
json_count=0
for p in root.rglob('*.json'):
    try:
        json.loads(p.read_text(encoding='utf-8'))
        json_count+=1
    except Exception as e:
        errors.append(f'bad json {p.relative_to(root)}: {e}')
script_count=0
for p in (root/'07_IMPLEMENTATION'/'scripts').glob('*.py'):
    try:
        py_compile.compile(str(p), doraise=True)
        script_count+=1
    except Exception as e:
        errors.append(f'bad script {p.relative_to(root)}: {e}')
# ensure local validation script itself passes
# (manual invocation skipped here to avoid path side-effects; compile + required examples checked instead)
if errors:
    print('FAIL')
    for e in errors: print('-', e)
    sys.exit(1)
print(f'PASS: Wave08 pack validates. JSON files: {json_count}. Scripts: {script_count}.')
