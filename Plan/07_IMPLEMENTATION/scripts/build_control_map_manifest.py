#!/usr/bin/env python3
"""Build a manifest for generated Wave 11 control-map assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_type(path: Path) -> str:
    lower = path.name.lower()
    for t in ["dwpose", "openpose", "depth", "normal", "canny", "lineart", "mask"]:
        if t in lower:
            return "segmentation_or_region_mask" if t == "mask" else t
    return "unknown"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-map-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.control_map_root)
    records = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        width = height = None
        try:
            with Image.open(path) as im:
                width, height = im.size
        except Exception:
            pass
        records.append({
            "asset_id": path.stem,
            "type": detect_type(path),
            "path": str(path),
            "sha256": sha256_file(path),
            "width": width,
            "height": height,
            "qa_status": "pending",
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"control_map_root": str(root), "asset_count": len(records), "assets": records}, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} control map asset records to {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
