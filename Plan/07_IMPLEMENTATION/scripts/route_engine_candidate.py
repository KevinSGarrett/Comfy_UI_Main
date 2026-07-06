#!/usr/bin/env python3
"""
Simple deterministic Wave 06 engine router prototype.

This is not the final orchestrator. It is a local validation tool showing how
a structured pass request should be converted into a route decision.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

PROOF_FOR_PROMOTION = ["object_info_visibility", "model_load_proof", "output_file_proof", "qa_manifest"]

def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def decide(request, registry, pass_map):
    engines = {e["engine_id"]: e for e in registry}
    pass_type = request.get("pass_type")
    requested = request.get("requested_engine")
    requires_lora_family = request.get("requires_lora_family")
    promotion_required = bool(request.get("promotion_required", True))

    candidates = []
    blocked = []

    if requested:
        candidates = [requested]
    elif pass_type in pass_map:
        candidates = pass_map[pass_type].get("preferred", [])
    else:
        return {
            "selected_engine": None,
            "selected_family": None,
            "reason": f"No pass map entry for pass_type={pass_type}",
            "blocked": ["unknown_pass_type"],
            "required_proof": []
        }

    for eid in candidates:
        engine = engines.get(eid)
        if engine is None:
            # Some pass-map aliases may be future placeholders.
            blocked.append(f"engine_not_registered:{eid}")
            continue

        family = engine.get("family")
        status = engine.get("promotion_status", "")
        compatible = engine.get("compatible_lora_families", [])

        if requires_lora_family and requires_lora_family not in compatible and requires_lora_family != family:
            blocked.append(f"{eid}:incompatible_lora_family:{requires_lora_family}")
            continue

        if promotion_required and ("blocked" in status or "candidate" in status or "review" in status or "planned" in status):
            return {
                "selected_engine": eid,
                "selected_family": family,
                "reason": f"{eid} is the best candidate, but promotion proof is required before automatic production use.",
                "blocked": [f"{eid}:promotion_status:{status}"],
                "required_proof": PROOF_FOR_PROMOTION
            }

        return {
            "selected_engine": eid,
            "selected_family": family,
            "reason": f"Selected {eid} for pass_type={pass_type}.",
            "blocked": blocked,
            "required_proof": PROOF_FOR_PROMOTION if promotion_required else []
        }

    return {
        "selected_engine": None,
        "selected_family": None,
        "reason": "No compatible engine candidate found.",
        "blocked": blocked,
        "required_proof": []
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--request", required=True, help="Path to route request JSON")
    args = parser.parse_args()

    root = Path(args.root)
    registry = load(root / "10_REGISTRIES" / "wave06_engine_registry.json")
    pass_map = load(root / "10_REGISTRIES" / "wave06_pass_to_engine_map.json")
    request = load(Path(args.request))

    print(json.dumps(decide(request, registry, pass_map), indent=2))

if __name__ == "__main__":
    main()
