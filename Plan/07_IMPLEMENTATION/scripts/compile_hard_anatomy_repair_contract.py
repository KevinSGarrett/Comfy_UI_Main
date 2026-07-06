#!/usr/bin/env python3
"""Compile a Wave 20 hard-anatomy repair contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    out = {
        'contract_version': 'wave20.v1',
        'source_image_id': src.get('source_image_id'),
        'character_id': src.get('character_id'),
        'repair_regions': src.get('repair_regions', []),
        'crop_plans': src.get('crop_plans', []),
        'qa_goals': src.get('qa_goals', []),
        'global_preservation_goals': src.get('global_preservation_goals', [
            'identity', 'pose', 'body_proportions', 'frame_integrity', 'contact_continuity'
        ]),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
