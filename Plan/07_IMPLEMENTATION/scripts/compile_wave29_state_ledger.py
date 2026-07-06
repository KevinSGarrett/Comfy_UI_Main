#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    ledger = {
        'state_id': src.get('state_id'),
        'sequence_id': src.get('sequence_id'),
        'segment_id': src.get('segment_id'),
        'characters': src.get('characters', {}),
        'scene_phase': src.get('scene_phase'),
        'body_state': src.get('body_state', {}),
        'fatigue_state': src.get('fatigue_state', {}),
        'clothing_state': src.get('clothing_state', {}),
        'hair_state': src.get('hair_state', {}),
        'surface_state': src.get('surface_state', {}),
        'contact_state': src.get('contact_state', {}),
        'variation_state': src.get('variation_state', {}),
        'continuity_notes': src.get('continuity_notes', [])
    }
    Path(args.output).write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
