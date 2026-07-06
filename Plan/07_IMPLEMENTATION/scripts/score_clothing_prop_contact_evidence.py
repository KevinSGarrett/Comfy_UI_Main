#!/usr/bin/env python3
"""Score Wave 19 contact evidence."""
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
    weights = {
        'contact_ownership_pass': 0.20,
        'no_floating_pass': 0.20,
        'no_clipping_pass': 0.20,
        'shadow_occlusion_pass': 0.15,
        'fabric_material_continuity_pass': 0.15,
        'identity_pose_body_preserved': 0.10,
    }
    score = 0.0
    for key, weight in weights.items():
        if data.get(key, False):
            score += weight
    report = {
        'evidence_version': 'wave19.v1',
        'score': round(score, 4),
        'minimum_score': 0.85,
        'pass': score >= 0.85,
        'failed_dimensions': [key for key in weights if not data.get(key, False)]
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
