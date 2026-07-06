#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def route_force(src: dict) -> dict:
    force_type = src.get('force_type', 'contact')
    intensity = src.get('intensity', 'low')
    material = src.get('material_profile', 'unknown')
    if force_type in {'impact', 'collision'}:
        layer = 'impact_sfx'
        sync_precision = 'frame_exact'
    elif force_type in {'fabric_motion'} or 'fabric' in material:
        layer = 'clothing_foley'
        sync_precision = 'within_2_frames'
    elif force_type in {'breath_force'}:
        layer = 'breath'
        sync_precision = 'windowed'
    elif force_type in {'prop_motion'}:
        layer = 'prop_foley'
        sync_precision = 'within_2_frames'
    else:
        layer = 'body_foley'
        sync_precision = 'within_2_frames'
    return {
        'force_event_id': src.get('force_event_id') or src.get('event_id'),
        'layer': layer,
        'force_type': force_type,
        'intensity': intensity,
        'material_profile': material,
        'expected_audio_force': src.get('expected_audio_force', intensity),
        'sync_precision': sync_precision,
        'start_time': src.get('start_time'),
        'end_time': src.get('end_time')
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    out = route_force(src)
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
