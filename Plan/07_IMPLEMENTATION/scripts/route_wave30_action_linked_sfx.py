#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def route_event(src: dict) -> dict:
    event_type = src.get('event_type', 'unknown')
    material = src.get('material_profile', 'unknown')
    intensity = src.get('intensity', 'low')
    if event_type == 'dialogue':
        layer = 'dialogue'
    elif event_type == 'breath':
        layer = 'breath'
    elif event_type in {'impact','collision'}:
        layer = 'impact_sfx'
    elif 'fabric' in material or event_type == 'clothing_motion':
        layer = 'clothing_foley'
    elif event_type in {'prop_contact','object_motion'}:
        layer = 'prop_foley'
    else:
        layer = 'body_foley'
    return {
        'audio_event_id': src.get('event_id'),
        'layer': layer,
        'event_type': event_type,
        'material_profile': material,
        'intensity': intensity,
        'expected_audio_force': src.get('expected_audio_force', intensity),
        'start_time': src.get('start_time'),
        'end_time': src.get('end_time')
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    out = route_event(src)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
