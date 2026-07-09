#!/usr/bin/env python3
"""Compile a Wave13 Mask Factory contract from a small JSON request.

This script intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SCALES = ["macro", "major", "minor"]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return data


def build_person_instances(expected_count: int) -> List[Dict[str, Any]]:
    people: List[Dict[str, Any]] = []
    for index in range(1, expected_count + 1):
        pid = f"person_{index:03d}"
        people.append(
            {
                "person_instance_id": pid,
                "character_id": f"character_{index:03d}",
                "required_masks": ["whole_person", "face", "hair", "body_outline_edge"],
            }
        )
    return people


def compile_contract(request: Dict[str, Any]) -> Dict[str, Any]:
    expected_count = int(request.get("expected_character_count", 1))
    required_masks = request.get("required_masks", ["person_instance"])
    if not isinstance(required_masks, list):
        required_masks = ["person_instance"]

    scales = request.get("required_mask_scales") or request.get("mask_scales") or DEFAULT_SCALES
    if not isinstance(scales, list):
        scales = DEFAULT_SCALES

    contract_id = request.get("contract_id") or f"mask_contract_{request.get('request_id', 'manual')}"
    scene_id = request.get("scene_id") or request.get("scene_director_plan_id") or "scene_manual"
    supplied_people = request.get("person_instances")
    if isinstance(supplied_people, list) and supplied_people:
        person_instances = supplied_people
    else:
        person_instances = build_person_instances(expected_count)

    contract: Dict[str, Any] = {
        "contract_id": contract_id,
        "scene_id": scene_id,
        "character_count_expected": expected_count,
        "mask_factory_mode": "runtime_plan",
        "required_mask_scales": scales,
        "person_instances": person_instances,
        "requested_mask_types": required_masks,
        "mask_layers": [],
        "fabric_masks": [],
        "contact_masks": [],
        "promotion_gates": [
            "mask_contract_valid",
            "runtime_masks_generated",
            "mask_evidence_scored",
            "qa_passed",
        ],
    }

    supplied_layers = request.get("mask_layers")
    if isinstance(supplied_layers, list) and supplied_layers:
        contract["mask_layers"] = supplied_layers
    else:
        for person in contract["person_instances"]:
            pid = person["person_instance_id"]
            contract["mask_layers"].append(
                {
                    "mask_id": f"{pid}__whole_person",
                    "scale": "major",
                    "target_type": "person_instance",
                    "person_instance_id": pid,
                    "source": "planned",
                    "required_evidence": ["mask_png_path", "bbox_normalized", "coverage_percent"],
                }
            )
            for region in person["required_masks"][1:]:
                contract["mask_layers"].append(
                    {
                        "mask_id": f"{pid}__{region}",
                        "scale": "minor" if region != "body_outline_edge" else "nano",
                        "target_type": "body_part",
                        "person_instance_id": pid,
                        "body_region_id": region,
                        "source": "planned",
                        "required_evidence": ["mask_png_path", "edge_quality_score"],
                    }
                )

    supplied_fabric_masks = request.get("fabric_masks")
    if isinstance(supplied_fabric_masks, list):
        contract["fabric_masks"] = supplied_fabric_masks
    elif "fabric" in " ".join(required_masks).lower():
        contract["fabric_masks"].append(
            {
                "mask_id": "fabric_001",
                "scale": "major",
                "fabric_region_id": "full_garment",
                "source": "planned",
                "required_evidence": ["mask_png_path", "outfit_lock_status"],
            }
        )

    supplied_contact_masks = request.get("contact_masks")
    if isinstance(supplied_contact_masks, list):
        contract["contact_masks"] = supplied_contact_masks
    elif "contact" in " ".join(required_masks).lower() or expected_count > 1:
        contract["contact_masks"].append(
            {
                "mask_id": "contact_001",
                "scale": "minor",
                "contact_type": "person_person_boundary" if expected_count > 1 else "object_surface_contact",
                "participants": [p["person_instance_id"] for p in contract["person_instances"][:2]],
                "source": "planned",
                "required_evidence": ["mask_png_path", "occlusion_order", "edge_quality_score"],
            }
        )

    return contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    request = load_json(args.request)
    contract = compile_contract(request)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    print(f"Wrote mask contract: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
