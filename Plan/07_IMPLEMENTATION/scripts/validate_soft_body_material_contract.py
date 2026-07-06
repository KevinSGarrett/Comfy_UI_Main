#!/usr/bin/env python3
"""Validate a Wave 21 soft-body material contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    required = ['contract_version', 'source_image_id', 'profile_id', 'region_bindings']
    missing = [k for k in required if k not in obj]
    errors: list[str] = []
    errors.extend(f'missing: {item}' for item in missing)
    if not isinstance(obj.get('region_bindings', []), list) or not obj.get('region_bindings', []):
        errors.append('region_bindings must be a non-empty list')
    if errors:
        print('FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
