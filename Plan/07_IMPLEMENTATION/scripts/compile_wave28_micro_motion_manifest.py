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
        'run_id': src.get('run_id'),
        'shot_id': src.get('shot_id'),
        'frame_count': src.get('frame_count', 0),
        'micro_motion_events': src.get('micro_motion_events', []),
        'per_frame_motion': src.get('per_frame_motion', [])
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
