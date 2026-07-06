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
    out = {
        'mix_id': src.get('mix_id'),
        'scene_id': src.get('scene_id'),
        'shot_id': src.get('shot_id'),
        'audio_events': src.get('audio_events', []),
        'room_profile': src.get('room_profile'),
        'camera_listener_state': src.get('camera_listener_state'),
        'spatial_layers': src.get('spatial_layers', []),
        'qa_scores': src.get('qa_scores', {}),
        'promotion_decision': src.get('promotion_decision', 'block')
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
