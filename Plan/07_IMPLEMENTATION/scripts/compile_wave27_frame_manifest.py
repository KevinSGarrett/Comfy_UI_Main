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
        'frame_index': src.get('frame_index'),
        'time_seconds': src.get('time_seconds'),
        'source_route': src.get('source_route'),
        'engine_name': src.get('engine_name'),
        'shot_id': src.get('shot_id'),
        'visible_characters': src.get('visible_characters', []),
        'camera_state': src.get('camera_state', {}),
        'qa_scores': src.get('qa_scores', {}),
        'repair_status': src.get('repair_status', 'unknown')
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
