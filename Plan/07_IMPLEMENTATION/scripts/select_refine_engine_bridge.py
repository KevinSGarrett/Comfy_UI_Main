#!/usr/bin/env python3
"""Select a Wave16 refine bridge from source/target engine hints."""
from __future__ import annotations

import argparse
import json


def select_bridge(source: str, target: str, masked: bool) -> dict:
    source = source.lower()
    target = target.lower()
    if source.startswith("flux2") and target.startswith("sdxl"):
        return {"bridge_id": "BRIDGE-FLUX2-TO-SDXL-DETAIL", "status": "planned_requires_runtime_proof"}
    if source.startswith("flux") and target.startswith("sdxl"):
        return {"bridge_id": "BRIDGE-FLUX1-TO-SDXL-DETAIL", "status": "allowed_after_runtime_proof"}
    if source in {"zimage", "z_image", "z-image"} and target.startswith("sdxl"):
        return {"bridge_id": "BRIDGE-ZIMAGE-TO-SDXL-DETAIL", "status": "present_as_static_template"}
    if source.startswith("sdxl") and target.startswith("pony"):
        return {"bridge_id": "BRIDGE-SDXL-TO-PONY-SPECIALTY", "status": "masked_only", "allowed": masked}
    if source.startswith("sdxl") and target.startswith("sdxl"):
        return {"bridge_id": "same_family_low_denoise", "status": "preferred"}
    return {"bridge_id": "unsupported_or_hold", "status": "hold", "allowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--masked", action="store_true")
    args = parser.parse_args()
    print(json.dumps(select_bridge(args.source, args.target, args.masked), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
