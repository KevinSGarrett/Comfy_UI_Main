#!/usr/bin/env python3
"""Copy the Wave 21 soft-body Main Flow inventory into the current working tree."""
from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / '10_REGISTRIES' / 'wave21_main_flow_soft_body_material_inventory.json'


def main() -> int:
    obj = json.loads(SOURCE.read_text(encoding='utf-8'))
    dest = Path('10_REGISTRIES/wave21_main_flow_soft_body_material_inventory.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    print(dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
