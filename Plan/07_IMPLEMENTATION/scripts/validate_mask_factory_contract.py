#!/usr/bin/env python3
"""Validate a Wave13 Mask Factory contract using standard-library checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


ALLOWED_SCALES = {"macro", "major", "minor", "micro", "nano"}


def fail(message: str, errors: List[str]) -> None:
    errors.append(message)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Contract must be a JSON object")
    return data


def validate(contract: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    for key in ["contract_id", "scene_id", "mask_factory_mode", "required_mask_scales", "person_instances", "promotion_gates"]:
        if key not in contract:
            fail(f"missing_required_key:{key}", errors)

    scales = contract.get("required_mask_scales", [])
    if not isinstance(scales, list) or not scales:
        fail("required_mask_scales_must_be_nonempty_list", errors)
    else:
        for scale in scales:
            if scale not in ALLOWED_SCALES:
                fail(f"invalid_mask_scale:{scale}", errors)

    people = contract.get("person_instances", [])
    if not isinstance(people, list):
        fail("person_instances_must_be_list", errors)
        people = []

    expected = int(contract.get("character_count_expected", len(people) or 0))
    if expected != len(people):
        warnings.append(f"expected_character_count_{expected}_but_person_instances_{len(people)}")

    person_ids = set()
    for person in people:
        if not isinstance(person, dict):
            fail("person_instance_must_be_object", errors)
            continue
        pid = person.get("person_instance_id")
        if not pid:
            fail("person_instance_missing_id", errors)
        elif pid in person_ids:
            fail(f"duplicate_person_instance_id:{pid}", errors)
        else:
            person_ids.add(pid)

    layers = contract.get("mask_layers", [])
    if layers is None:
        layers = []
    if not isinstance(layers, list):
        fail("mask_layers_must_be_list", errors)
        layers = []

    for layer in layers:
        if not isinstance(layer, dict):
            fail("mask_layer_must_be_object", errors)
            continue
        mask_id = layer.get("mask_id")
        scale = layer.get("scale")
        target_type = layer.get("target_type")
        if not mask_id:
            fail("mask_layer_missing_mask_id", errors)
        if scale not in ALLOWED_SCALES:
            fail(f"mask_layer_invalid_scale:{mask_id}:{scale}", errors)
        if not target_type:
            fail(f"mask_layer_missing_target_type:{mask_id}", errors)
        pid = layer.get("person_instance_id")
        if target_type in {"person_instance", "body_part"} and pid not in person_ids:
            fail(f"mask_layer_missing_or_invalid_person_owner:{mask_id}", errors)

    for group_name in ["fabric_masks", "contact_masks"]:
        group = contract.get(group_name, [])
        if group is None:
            group = []
        if not isinstance(group, list):
            fail(f"{group_name}_must_be_list", errors)

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "contract_id": contract.get("contract_id"),
        "mask_layer_count": len(layers),
        "person_instance_count": len(people),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    contract = load_json(args.contract)
    report = validate(contract)
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
