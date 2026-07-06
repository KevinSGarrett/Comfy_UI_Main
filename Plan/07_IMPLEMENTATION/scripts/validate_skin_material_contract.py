#!/usr/bin/env python3
"""Validate a Wave 18 skin/material contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    required = ['contract_version', 'source_image_id', 'target_regions', 'surface_profile']
    missing = [k for k in required if k not in obj]
    if missing:
        print('FAIL')
        for item in missing:
            print(f'missing: {item}')
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
