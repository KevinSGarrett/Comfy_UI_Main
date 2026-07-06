#!/usr/bin/env python3
"""Score Wave 18 skin/material evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    report = {
        'evidence_version': 'wave18.v1',
        'surface_target_visible': data.get('surface_target_visible', False),
        'identity_preserved': data.get('identity_preserved', False),
        'pose_preserved': data.get('pose_preserved', False),
        'body_preserved': data.get('body_preserved', False),
        'crop_preserved': data.get('crop_preserved', False),
        'continuity_score': data.get('continuity_score', 0.0),
    }
    report['pass'] = bool(
        report['surface_target_visible']
        and report['identity_preserved']
        and report['pose_preserved']
        and report['body_preserved']
        and report['crop_preserved']
        and report['continuity_score'] >= 0.8
    )
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
