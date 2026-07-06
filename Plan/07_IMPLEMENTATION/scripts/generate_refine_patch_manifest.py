#!/usr/bin/env python3
"""Generate a Wave16 low-denoise patch manifest without modifying a workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--source-engine", required=True)
    parser.add_argument("--target-engine", required=True)
    parser.add_argument("--pass-id", required=True)
    parser.add_argument("--denoise", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.denoise > 0.4:
        raise ValueError("denoise above 0.4 is not a Wave16 refine pass")

    manifest = {
        "patch_manifest_id": f"{args.pass_id}_patch",
        "base_image": args.base_image,
        "source_engine": args.source_engine,
        "target_engine": args.target_engine,
        "pass_id": args.pass_id,
        "denoise": args.denoise,
        "allowed_transfer_objects": ["image_file", "mask_file", "control_map_file", "qa_manifest"],
        "forbidden_transfer_objects": ["latent_tensor", "MODEL", "CLIP", "cross_engine_lora_stack"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
