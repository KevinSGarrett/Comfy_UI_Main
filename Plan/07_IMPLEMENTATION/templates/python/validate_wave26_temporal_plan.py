from pathlib import Path
import json

ROOT = Path('.')
required = [
    ROOT / '10_REGISTRIES' / 'wave26_keyframe_schema.json',
    ROOT / '10_REGISTRIES' / 'wave26_shot_plan_schema.json',
    ROOT / '11_SCHEMAS' / 'examples' / 'wave26_sample_scene_keyframe_plan.json',
    ROOT / '11_SCHEMAS' / 'examples' / 'wave26_sample_video_shot_plan.json',
]
for path in required:
    if not path.exists():
        raise SystemExit(f'Missing required file: {path}')
    json.loads(path.read_text(encoding='utf-8'))
print('WAVE26 VALIDATION: PASS')
print('Temporal planning schemas/examples are readable JSON.')
