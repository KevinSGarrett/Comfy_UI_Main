#!/usr/bin/env python3
"""Compile a Wave 18 skin/material contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EVIDENCE_GATES = [
    'surface_texture_check',
    'lighting_consistency',
    'material_state_continuity',
    'visual_score_threshold',
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    out = {
        'contract_version': 'wave18.v1',
        'source_image_id': src.get('source_image_id'),
        'character_id': src.get('character_id'),
        'target_regions': src.get('target_regions', []),
        'surface_profile': src.get('surface_profile'),
        'pass_order': src.get('pass_order', []),
        'qa_goals': src.get('qa_goals', []),
        'required_evidence_gates': REQUIRED_EVIDENCE_GATES,
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
