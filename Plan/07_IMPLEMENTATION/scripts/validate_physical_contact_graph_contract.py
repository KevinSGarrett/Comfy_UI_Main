#!/usr/bin/env python3
"""Validate a Wave 22 physical contact graph contract fail closed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PLAN_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = PLAN_ROOT / "10_REGISTRIES"
EXPECTED_CONTRACT_VERSION = "wave22.v1"
ROOT_FIELDS = {
    "contract_version",
    "contact_graph_id",
    "scene_id",
    "source_image_id",
    "contact_edges",
    "qa_goals",
}
REQUIRED_ROOT_FIELDS = {"contract_version", "contact_graph_id", "contact_edges"}
EDGE_FIELDS = {
    "edge_id",
    "source_owner_id",
    "source_region_id",
    "source_region_type",
    "target_owner_id",
    "target_region_id",
    "target_region_type",
    "contact_edge_type",
    "pressure",
    "intensity",
    "occlusion",
    "duration",
    "audio_force_class",
    "mask_ids",
}
REQUIRED_EDGE_FIELDS = {
    "edge_id",
    "source_owner_id",
    "source_region_id",
    "target_owner_id",
    "target_region_id",
    "contact_edge_type",
    "pressure",
    "intensity",
    "occlusion",
    "duration",
    "audio_force_class",
}
QA_GOALS = {
    "source_target_ownership",
    "pressure_intensity_valid",
    "occlusion_valid",
    "duration_valid",
    "audio_force_valid",
    "deformation_evidence_pass",
    "preservation_pass",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_list(path: Path, field: str) -> set[str]:
    payload = _load_json(path)
    if not isinstance(payload, dict) or set(payload) == set():
        raise ValueError(f"invalid registry object: {path}")
    values = payload.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"registry {path} must contain non-empty {field}")
    if any(type(value) is not str or not value.strip() for value in values):
        raise ValueError(f"registry {path} {field} must contain non-empty strings")
    normalized = [value.strip() for value in values]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"registry {path} {field} must be unique")
    return set(normalized)


def _load_authority() -> dict[str, set[str]]:
    edge_types_path = REGISTRY_ROOT / "wave22_contact_edge_type_taxonomy.json"
    edge_types_payload = _load_json(edge_types_path)
    if not isinstance(edge_types_payload, dict):
        raise ValueError("contact edge taxonomy must be an object")
    edge_types = _load_list(edge_types_path, "edge_types")
    required_masks = _load_list(edge_types_path, "requires_contact_boundary_mask")
    if not required_masks.issubset(edge_types):
        raise ValueError("requires_contact_boundary_mask contains an unknown edge type")

    pressure_path = REGISTRY_ROOT / "wave22_pressure_intensity_profiles.json"
    occlusion_path = REGISTRY_ROOT / "wave22_occlusion_duration_profiles.json"
    force_path = REGISTRY_ROOT / "wave22_audio_force_profiles.json"
    return {
        "edge_types": edge_types,
        "required_masks": required_masks,
        "pressure": _load_list(pressure_path, "pressure_levels"),
        "intensity": _load_list(pressure_path, "intensity_levels"),
        "occlusion": _load_list(occlusion_path, "occlusion_states"),
        "duration": _load_list(occlusion_path, "duration_classes"),
        "audio_force": _load_list(force_path, "audio_force_classes"),
    }


def _non_empty_string(value: Any, label: str, errors: list[str]) -> str | None:
    if type(value) is not str or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return None
    return value.strip()


def _validate_optional_string(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if key not in payload or payload[key] is None:
        return
    _non_empty_string(payload[key], key, errors)


def validate_contract(payload: Any, authority: dict[str, set[str]] | None = None) -> tuple[list[str], int]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["contract must be an object"], 0

    missing_root = sorted(REQUIRED_ROOT_FIELDS - set(payload))
    unexpected_root = sorted(set(payload) - ROOT_FIELDS)
    errors.extend(f"missing root field: {key}" for key in missing_root)
    errors.extend(f"unexpected root field: {key}" for key in unexpected_root)

    if payload.get("contract_version") != EXPECTED_CONTRACT_VERSION:
        errors.append(f"contract_version must equal {EXPECTED_CONTRACT_VERSION}")
    _non_empty_string(payload.get("contact_graph_id"), "contact_graph_id", errors)
    _validate_optional_string(payload, "scene_id", errors)
    _validate_optional_string(payload, "source_image_id", errors)

    if "qa_goals" in payload:
        goals = payload["qa_goals"]
        if not isinstance(goals, list) or not goals:
            errors.append("qa_goals must be a non-empty array")
        else:
            normalized_goals: list[str] = []
            for idx, goal in enumerate(goals):
                value = _non_empty_string(goal, f"qa_goals[{idx}]", errors)
                if value is not None:
                    normalized_goals.append(value)
                    if value not in QA_GOALS:
                        errors.append(f"qa_goals[{idx}] is not registered: {value}")
            if len(normalized_goals) != len(set(normalized_goals)):
                errors.append("qa_goals must be unique")

    edges = payload.get("contact_edges")
    if not isinstance(edges, list) or not edges:
        errors.append("contact_edges must be a non-empty array")
        return errors, 0

    if authority is None:
        try:
            authority = _load_authority()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"authority registry invalid: {exc}")
            return errors, len(edges)

    seen_edge_ids: set[str] = set()
    for idx, edge in enumerate(edges):
        label = f"contact_edges[{idx}]"
        if not isinstance(edge, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = sorted(REQUIRED_EDGE_FIELDS - set(edge))
        unexpected = sorted(set(edge) - EDGE_FIELDS)
        errors.extend(f"{label} missing field: {key}" for key in missing)
        errors.extend(f"{label} unexpected field: {key}" for key in unexpected)

        normalized: dict[str, str | None] = {}
        for key in sorted(REQUIRED_EDGE_FIELDS):
            normalized[key] = _non_empty_string(edge.get(key), f"{label}.{key}", errors)
        for key in ("source_region_type", "target_region_type"):
            if key in edge:
                normalized[key] = _non_empty_string(edge[key], f"{label}.{key}", errors)

        edge_id = normalized.get("edge_id")
        if edge_id is not None:
            if edge_id in seen_edge_ids:
                errors.append(f"duplicate edge_id: {edge_id}")
            seen_edge_ids.add(edge_id)

        for key, authority_key in (
            ("contact_edge_type", "edge_types"),
            ("pressure", "pressure"),
            ("intensity", "intensity"),
            ("occlusion", "occlusion"),
            ("duration", "duration"),
            ("audio_force_class", "audio_force"),
        ):
            value = normalized.get(key)
            if value is not None and value not in authority[authority_key]:
                errors.append(f"{label}.{key} is not registered: {value}")

        masks = edge.get("mask_ids")
        normalized_masks: list[str] = []
        if masks is not None:
            if not isinstance(masks, list):
                errors.append(f"{label}.mask_ids must be an array")
            else:
                for mask_idx, mask_id in enumerate(masks):
                    value = _non_empty_string(mask_id, f"{label}.mask_ids[{mask_idx}]", errors)
                    if value is not None:
                        normalized_masks.append(value)
                if len(normalized_masks) != len(set(normalized_masks)):
                    errors.append(f"{label}.mask_ids must be unique")
        edge_type = normalized.get("contact_edge_type")
        if edge_type in authority["required_masks"] and not normalized_masks:
            errors.append(f"{label}.mask_ids must be non-empty for contact_edge_type {edge_type}")

    return errors, len(edges)


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    errors: list[str]
    edge_count = 0
    try:
        payload = _load_json(Path(args.input))
        errors, edge_count = validate_contract(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors = [f"invalid input JSON: {exc}"]

    report = {
        "validation_version": "wave22.v2",
        "classification": "WAVE22_PHYSICAL_CONTACT_GRAPH_VALIDATION_PASS" if not errors else "WAVE22_PHYSICAL_CONTACT_GRAPH_VALIDATION_FAIL",
        "input": args.input,
        "passed": not errors,
        "errors": errors,
        "contact_edge_count": edge_count,
        "strict_types": True,
        "authority_registries_enforced": True,
    }
    if args.output:
        _write_report(Path(args.output), report)

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
