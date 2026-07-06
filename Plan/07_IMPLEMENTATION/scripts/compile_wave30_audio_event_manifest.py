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
    event = {
        'audio_event_id': src.get('audio_event_id'),
        'scene_id': src.get('scene_id'),
        'shot_id': src.get('shot_id'),
        'event_type': src.get('event_type'),
        'source_event_id': src.get('source_event_id'),
        'start_time': src.get('start_time'),
        'end_time': src.get('end_time'),
        'layer': src.get('layer'),
        'routing': src.get('routing', {}),
        'qa_targets': src.get('qa_targets', [])
    }
    Path(args.output).write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
