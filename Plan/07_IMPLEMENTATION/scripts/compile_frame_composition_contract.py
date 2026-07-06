#!/usr/bin/env python3
"""Compile a Wave12 frame composition contract from a simple request JSON.

This script intentionally uses only the Python standard library.
"""
import argparse
import json
from pathlib import Path

VISIBILITY_DEFAULTS = {
    "full_body": {"safe_margin_ratio": 0.06, "required_regions": ["head", "torso", "hands", "legs", "feet"], "forbidden_crop_points": ["head", "hands", "feet"]},
    "three_quarter_body": {"safe_margin_ratio": 0.05, "required_regions": ["head", "torso", "hips", "knees"], "forbidden_crop_points": ["head", "face"]},
    "half_body": {"safe_margin_ratio": 0.04, "required_regions": ["head", "torso", "waist_or_hips"], "forbidden_crop_points": ["head", "face"]},
    "one_third_body": {"safe_margin_ratio": 0.035, "required_regions": ["head", "face", "upper_torso"], "forbidden_crop_points": ["face"]},
    "one_quarter_body": {"safe_margin_ratio": 0.03, "required_regions": ["primary_focus_region"], "forbidden_crop_points": ["primary_focus_region"]},
    "close_up_face": {"safe_margin_ratio": 0.025, "required_regions": ["eyes", "nose", "mouth"], "forbidden_crop_points": ["eyes", "nose", "mouth"]},
}

def load_json(path: str):
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))

def compile_contract(request: dict) -> dict:
    count = int(request.get("expected_character_count", 1))
    profile = request.get("body_visibility_profile") or request.get("shot_size") or "full_body"
    defaults = VISIBILITY_DEFAULTS.get(profile, VISIBILITY_DEFAULTS["full_body"])
    character_ids = request.get("character_ids") or [f"character_{i+1}" for i in range(count)]
    slots = []
    for i, character_id in enumerate(character_ids[:count]):
        slots.append({
            "slot_id": f"slot_{i+1}",
            "character_id": character_id,
            "required_visible_regions": request.get("required_visible_regions", defaults["required_regions"]),
        })
    return {
        "contract_id": request.get("contract_id", "wave12_contract_generated"),
        "scene_id": request.get("scene_id", "scene_unset"),
        "expected_character_count": count,
        "shot_size": request.get("shot_size", profile),
        "body_visibility_profile": profile,
        "allow_background_people": bool(request.get("allow_background_people", False)),
        "no_merged_bodies_required": bool(request.get("no_merged_bodies_required", True)),
        "crop_boundary_policy": {
            "safe_margin_ratio": float(request.get("safe_margin_ratio", defaults["safe_margin_ratio"])),
            "forbidden_crop_points": request.get("forbidden_crop_points", defaults["forbidden_crop_points"]),
            "allowed_crop_points": request.get("allowed_crop_points", []),
            "auto_repair_actions": request.get("auto_repair_actions", ["rerun_wider_if_body_cut", "expand_canvas_outpaint"]),
        },
        "character_slots": slots,
        "qa_thresholds": {
            "minimum_total_score": float(request.get("minimum_total_score", 0.86)),
            "block_on_wrong_count": True,
            "block_on_merged_bodies": True,
            "block_on_forbidden_crop": True,
        },
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", help="Input request JSON", default="")
    ap.add_argument("--out", required=True, help="Output contract JSON")
    args = ap.parse_args()
    request = load_json(args.request)
    contract = compile_contract(request)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
