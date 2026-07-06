#!/usr/bin/env python3
"""Compile a Wave 21 soft-body material contract."""
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
        'contract_version': 'wave21.v1',
        'source_image_id': src.get('source_image_id'),
        'profile_id': src.get('profile_id'),
        'region_bindings': src.get('region_bindings', []),
        'motion_profile_id': src.get('motion_profile_id', 'static_still_only'),
        'compression_profile_id': src.get('compression_profile_id'),
        'pass_profile_id': src.get('pass_profile_id'),
        'qa_goals': src.get('qa_goals', []),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
