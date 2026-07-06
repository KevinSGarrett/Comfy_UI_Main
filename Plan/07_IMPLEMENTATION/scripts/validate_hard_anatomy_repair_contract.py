#!/usr/bin/env python3
"""Validate a Wave 20 hard-anatomy repair contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = ['contract_version', 'source_image_id', 'repair_regions', 'crop_plans', 'qa_goals']


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    missing = [k for k in REQUIRED if k not in obj]
    if missing:
        print('FAIL')
        for item in missing:
            print(f'missing: {item}')
        return 1
    if not obj.get('repair_regions'):
        print('FAIL')
        print('missing: at least one repair region')
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
