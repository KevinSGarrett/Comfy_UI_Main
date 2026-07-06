#!/usr/bin/env python3
"""Validate a Wave 19 clothing/prop/furniture contact contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    required = ['contract_version', 'source_image_id', 'contact_graph', 'mask_ids']
    errors = [f'missing: {k}' for k in required if k not in obj]
    if not obj.get('contact_graph'):
        errors.append('contact_graph is empty')
    if not obj.get('mask_ids'):
        errors.append('mask_ids is empty')
    if errors:
        print('FAIL')
        for err in errors:
            print(err)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
