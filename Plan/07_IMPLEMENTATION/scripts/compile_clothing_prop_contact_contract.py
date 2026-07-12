#!/usr/bin/env python3
"""Compile a Wave 19 clothing/prop/furniture contact contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EVIDENCE_GATES = [
    'contact_graph_check',
    'shadow_contact_check',
    'no_floating_check',
    'visual_reject_on_clip',
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    out = {
        'contract_version': 'wave19.v1',
        'source_image_id': src.get('source_image_id'),
        'character_ids': src.get('character_ids', []),
        'contact_graph': src.get('contact_graph', []),
        'fabric_targets': src.get('fabric_targets', []),
        'prop_targets': src.get('prop_targets', []),
        'furniture_targets': src.get('furniture_targets', []),
        'mask_ids': src.get('mask_ids', []),
        'pass_order': src.get('pass_order', []),
        'qa_goals': src.get('qa_goals', []),
        'required_evidence_gates': REQUIRED_EVIDENCE_GATES,
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
