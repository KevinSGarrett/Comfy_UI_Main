import json, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[1]
errors=[]
required=[
 'README.md',
 '00_PROJECT_CONTROL/WAVE_00_TO_34_MASTER_SCHEDULE.md',
 '00_PROJECT_CONTROL/WAVE_00_TO_34_MASTER_SCHEDULE.json',
 '02_TARGET_ARCHITECTURE/GITHUB_LOCAL_EC2_S3_DEVELOPMENT_STRATEGY.md',
 '02_TARGET_ARCHITECTURE/MODEL_ASSET_STORAGE_AND_CACHE_STRATEGY.md',
 '03_IMAGE_SYSTEM/MASK_TAXONOMY_MAJOR_MINOR_MICRO_NANO.md',
 '03_IMAGE_SYSTEM/SOFT_BODY_MECHANICS_ULTIMATE_SPEC.md',
 '13_ADVANCED_ADDITIONS_INTEGRATION/ADVANCED_ADDITIONS_REVIEW.md'
]
for r in required:
    if not (root/r).exists(): errors.append(f'missing {r}')
# validate JSON files
for p in root.rglob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'invalid json {p.relative_to(root)}: {e}')
# schedule count
try:
    sched=json.loads((root/'00_PROJECT_CONTROL/WAVE_00_TO_34_MASTER_SCHEDULE.json').read_text(encoding='utf-8'))
    if len(sched)!=35: errors.append(f'expected 35 waves, got {len(sched)}')
except Exception as e: errors.append(str(e))
if errors:
    print('\n'.join(errors)); sys.exit(1)
print('PASS: Wave00 35-wave expansion pack validates.')
