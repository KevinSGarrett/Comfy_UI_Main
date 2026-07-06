#!/usr/bin/env python3
"""Compile a Wave16 image-refine bridge plan from a simple request JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def choose_bridge(base_engine: str, allow_pony: bool = False) -> str:
    if base_engine in {"flux2", "flux2_dev", "flux2_klein"}:
        return "BRIDGE-FLUX2-TO-SDXL-DETAIL"
    if base_engine in {"flux", "flux1", "flux1_dev", "flux1_schnell"}:
        return "BRIDGE-FLUX1-TO-SDXL-DETAIL"
    if base_engine in {"z_image", "zimage", "z-image"}:
        return "BRIDGE-ZIMAGE-TO-SDXL-DETAIL"
    if base_engine in {"sdxl", "sdxl_realvisxl", "realvisxl"} and allow_pony:
        return "BRIDGE-SDXL-TO-PONY-SPECIALTY"
    return "same_family_low_denoise"


def compile_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    base = request.get("base_image", {})
    base_engine = str(base.get("engine_family", "unknown")).lower()
    allow_pony = bool(request.get("allow_pony_masked_specialty", False))
    bridge_id = choose_bridge(base_engine, allow_pony=allow_pony)
    target = "pony_sdxl_specialty" if bridge_id == "BRIDGE-SDXL-TO-PONY-SPECIALTY" else "sdxl_realvisxl"

    passes: List[Dict[str, Any]] = [
        {
            "pass_id": "REFINE-00-BASE-PRESERVATION-CHECK",
            "source_engine": base_engine,
            "target_engine": "none",
            "denoise": 0.0,
            "scope": "evidence_only",
            "mask_required": False,
        }
    ]

    if bridge_id != "same_family_low_denoise":
        passes.append(
            {
                "pass_id": "REFINE-50-CROSS-ENGINE-SDXL-BRIDGE",
                "source_engine": base_engine,
                "target_engine": target,
                "denoise": 0.18 if target == "sdxl_realvisxl" else 0.14,
                "scope": "image_based_bridge",
                "mask_required": bridge_id == "BRIDGE-SDXL-TO-PONY-SPECIALTY",
                "bridge_contract_id": bridge_id,
            }
        )

    if "regional" in " ".join(request.get("desired_refine", [])).lower() or request.get("mask_contract_id"):
        passes.append(
            {
                "pass_id": "REFINE-20-REGIONAL-INPAINT-DETAIL",
                "source_engine": target if target != "none" else base_engine,
                "target_engine": "sdxl_realvisxl",
                "denoise": 0.24,
                "scope": "masked_regional_detail",
                "mask_required": True,
                "mask_contract_id": request.get("mask_contract_id", "required_at_runtime"),
            }
        )

    return {
        "plan_id": request.get("request_id", "wave16_refine_plan"),
        "base_image": base,
        "passes": passes,
        "qa_gates": [
            "base_preserved",
            "identity_preserved",
            "pose_preserved",
            "frame_preserved",
            "mask_ownership_pass",
            "engine_family_compatible",
        ],
        "max_reruns_per_pass": int(request.get("max_reruns_per_pass", 2)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    plan = compile_plan(load_json(args.request))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
