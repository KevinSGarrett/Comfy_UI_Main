#!/usr/bin/env python3
"""Re-emit the Wave 20 hard-anatomy inventory from the pack registry."""
from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / '10_REGISTRIES' / 'wave20_main_flow_hard_anatomy_inventory.json'


def main() -> int:
    obj = json.loads(SOURCE.read_text(encoding='utf-8'))
    dest = Path('10_REGISTRIES/wave20_main_flow_hard_anatomy_inventory.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    print(dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
