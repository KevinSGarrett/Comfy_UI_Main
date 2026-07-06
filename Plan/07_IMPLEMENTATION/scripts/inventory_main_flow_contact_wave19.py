#!/usr/bin/env python3
"""Refresh Wave 19 Main Flow contact inventory from the generated registry."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    src = root / '10_REGISTRIES' / 'wave19_main_flow_clothing_prop_contact_inventory.json'
    obj = json.loads(src.read_text(encoding='utf-8'))
    dest = Path('10_REGISTRIES/wave19_main_flow_clothing_prop_contact_inventory.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    print(dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
