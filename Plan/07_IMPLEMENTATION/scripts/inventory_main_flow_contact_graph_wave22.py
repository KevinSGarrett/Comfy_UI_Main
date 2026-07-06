#!/usr/bin/env python3
"""Write the Wave 22 Main Flow contact-graph inventory to the registry path."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    source = Path(__file__).resolve().parents[2] / "10_REGISTRIES" / "wave22_main_flow_contact_graph_inventory.json"
    obj = json.loads(source.read_text(encoding="utf-8"))
    dest = Path("10_REGISTRIES/wave22_main_flow_contact_graph_inventory.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
