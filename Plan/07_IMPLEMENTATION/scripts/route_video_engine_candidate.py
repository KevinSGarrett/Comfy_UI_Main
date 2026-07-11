#!/usr/bin/env python3
"""
Deterministic offline router for Wave64 video engine candidates.

This script is intentionally fail-closed: canonical unknown or unverified
registry values block compatibility and prevent selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


REQUEST_REQUIRED_FIELDS = {
    "output_type",
    "width",
    "height",
    "duration_seconds",
    "fps",
    "character_count",
    "camera_movement",
    "motion_complexity",
    "reference_video_present",
    "keyframe_count",
    "identity_lock_required",
    "contact_deformation_required",
    "audio_required",
    "prior_generation_failed",
    "frame_sequence_available",
    "isolated_frame_failure",
    "structured_linear_guidance",
    "execution_target",
    "available_vram_gb",
    "cost_tier",
    "requested_engine",
    "promotion_required",
}

REQUEST_OPTIONAL_FIELDS = set()
REQUEST_ALLOWED_FIELDS = REQUEST_REQUIRED_FIELDS | REQUEST_OPTIONAL_FIELDS

REQUEST_OUTPUT_TYPES = {"gif", "mp4", "webm", "image_sequence"}
REQUEST_CAMERA_MOVEMENT = {"none", "low", "moderate", "high"}
REQUEST_MOTION_COMPLEXITY = {"low", "moderate", "high"}
REQUEST_EXECUTION_TARGET = {"local", "ec2"}
REQUEST_COST_TIERS = {"low", "medium", "high"}
REQUEST_INTEGER_FIELDS = {
    "width",
    "height",
    "character_count",
    "keyframe_count",
}
REQUEST_NUMBER_FIELDS = {
    "duration_seconds",
    "fps",
    "available_vram_gb",
}

ENGINE_REQUIRED_FIELDS = {
    "id",
    "class",
    "best_for",
    "model_registry_link",
    "object_info_evidence",
    "runtime_proof",
    "supported_outputs",
    "supported_features",
    "resource_limits",
    "execution_targets",
    "cost_tiers",
    "availability",
    "promotion_proof",
}

ENGINE_ALLOWED_FIELDS = ENGINE_REQUIRED_FIELDS
ENGINE_CLASSES = {"video_model", "fallback", "repair"}
VERIFICATION_STATUSES = {"verified", "unverified"}
ENGINE_AVAILABILITY_STATES = {"available", "unavailable", "unknown"}
ENGINE_SUPPORTED_OUTPUTS = REQUEST_OUTPUT_TYPES
ENGINE_SUPPORTED_FEATURES = {
    "reference_video_input",
    "keyframes",
    "identity_lock",
    "contact_deformation",
    "audio_sync",
    "frame_repair",
    "frame_sequence_bridge",
    "high_motion",
    "camera_motion_control",
    "structured_linear_guidance",
}
ENGINE_EXECUTION_TARGETS = REQUEST_EXECUTION_TARGET
ENGINE_COST_TIERS = REQUEST_COST_TIERS

RULE_REQUIRED_FIELDS = {"id", "priority", "route", "all"}
RULE_ALLOWED_OPS = {"eq", "gte", "lte"}
RULE_CONDITION_KEYS = {"field", "op", "value"}
REQUEST_FIELD_TYPES = {
    "output_type": "string",
    "width": "int",
    "height": "int",
    "duration_seconds": "number",
    "fps": "number",
    "character_count": "int",
    "camera_movement": "string",
    "motion_complexity": "string",
    "reference_video_present": "bool",
    "keyframe_count": "int",
    "identity_lock_required": "bool",
    "contact_deformation_required": "bool",
    "audio_required": "bool",
    "prior_generation_failed": "bool",
    "frame_sequence_available": "bool",
    "isolated_frame_failure": "bool",
    "structured_linear_guidance": "bool",
    "execution_target": "string",
    "available_vram_gb": "number",
    "cost_tier": "string",
    "requested_engine": "string_or_null",
    "promotion_required": "bool",
}

DECISION_SCOPE = "offline_routing_only"


def reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite number is not allowed: {value}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=reject_non_finite)


def expect_type(value: Any, expected: type, field: str) -> None:
    if not isinstance(value, expected):
        raise ValueError(f"field '{field}' must be of type {expected.__name__}")


def expect_int(value: Any, field: str, minimum: int | None = None) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"field '{field}' must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"field '{field}' must be >= {minimum}")


def expect_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"field '{field}' must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"field '{field}' cannot be blank")
    return stripped


def expect_string_list(
    value: Any,
    field: str,
    allowed_values: set[str] | None = None,
    must_be_non_empty: bool = False,
    require_unique: bool = True,
) -> List[str]:
    expect_type(value, list, field)
    parsed: List[str] = []
    seen: set[str] = set()
    for idx, entry in enumerate(value):
        item = expect_non_empty_string(entry, f"{field}[{idx}]")
        if allowed_values is not None and item not in allowed_values:
            raise ValueError(f"field '{field}[{idx}]' has unsupported value '{item}'")
        if require_unique:
            if item in seen:
                raise ValueError(f"field '{field}' contains duplicate value '{item}'")
            seen.add(item)
        parsed.append(item)
    if must_be_non_empty and not parsed:
        raise ValueError(f"field '{field}' must not be empty")
    return parsed


def expect_finite_number(value: Any, field: str, minimum: float | None = None) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"field '{field}' must be a number")
    if not math.isfinite(float(value)):
        raise ValueError(f"field '{field}' must be finite")
    if minimum is not None and float(value) < minimum:
        raise ValueError(f"field '{field}' must be >= {minimum}")


def expect_verification_status(value: Any, field: str) -> str:
    status = expect_non_empty_string(value, field)
    if status not in VERIFICATION_STATUSES:
        raise ValueError(f"field '{field}' has unsupported value '{status}'")
    return status


def validate_verified_scalar_record(record: Any, field: str) -> None:
    expect_type(record, dict, field)
    if set(record.keys()) != {"verification_status", "value"}:
        raise ValueError(f"field '{field}' must contain only verification_status and value")
    status = expect_verification_status(record["verification_status"], f"{field}.verification_status")
    if status == "verified":
        expect_non_empty_string(record["value"], f"{field}.value")
    elif record["value"] is not None:
        raise ValueError(f"field '{field}.value' must be null when unverified")


def validate_verified_values_record(
    record: Any,
    field: str,
    allowed_values: set[str],
) -> None:
    expect_type(record, dict, field)
    if set(record.keys()) != {"verification_status", "values"}:
        raise ValueError(f"field '{field}' must contain only verification_status and values")
    status = expect_verification_status(record["verification_status"], f"{field}.verification_status")
    values = expect_string_list(
        record["values"],
        f"{field}.values",
        allowed_values=allowed_values,
        must_be_non_empty=(status == "verified"),
        require_unique=True,
    )
    if status == "unverified" and values:
        raise ValueError(f"field '{field}.values' must be empty when unverified")


def validate_verified_limits_record(record: Any, field: str) -> None:
    expect_type(record, dict, field)
    required_keys = {
        "verification_status",
        "max_width",
        "max_height",
        "max_duration_seconds",
        "max_fps",
        "min_vram_gb",
    }
    if set(record.keys()) != required_keys:
        raise ValueError(f"field '{field}' has invalid shape")
    status = expect_verification_status(record["verification_status"], f"{field}.verification_status")
    numeric_fields = [
        "max_width",
        "max_height",
        "max_duration_seconds",
        "max_fps",
        "min_vram_gb",
    ]
    if status == "verified":
        expect_int(record["max_width"], f"{field}.max_width", minimum=1)
        expect_int(record["max_height"], f"{field}.max_height", minimum=1)
        expect_finite_number(
            record["max_duration_seconds"], f"{field}.max_duration_seconds", minimum=0.001
        )
        expect_finite_number(record["max_fps"], f"{field}.max_fps", minimum=0.001)
        expect_finite_number(record["min_vram_gb"], f"{field}.min_vram_gb", minimum=0.0)
    else:
        for name in numeric_fields:
            if record[name] is not None:
                raise ValueError(f"field '{field}.{name}' must be null when unverified")


def validate_verified_availability(record: Any, field: str) -> None:
    expect_type(record, dict, field)
    if set(record.keys()) != {"verification_status", "state"}:
        raise ValueError(f"field '{field}' must contain only verification_status and state")
    status = expect_verification_status(record["verification_status"], f"{field}.verification_status")
    state = record["state"]
    if status == "verified":
        state_value = expect_non_empty_string(state, f"{field}.state")
        if state_value not in ENGINE_AVAILABILITY_STATES:
            raise ValueError(f"field '{field}.state' has unsupported value '{state_value}'")
    elif state is not None:
        raise ValueError(f"field '{field}.state' must be null when unverified")


def validate_verified_items_record(record: Any, field: str) -> None:
    expect_type(record, dict, field)
    if set(record.keys()) != {"verification_status", "items"}:
        raise ValueError(f"field '{field}' must contain only verification_status and items")
    status = expect_verification_status(record["verification_status"], f"{field}.verification_status")
    items = expect_string_list(
        record["items"],
        f"{field}.items",
        allowed_values=None,
        must_be_non_empty=(status == "verified"),
        require_unique=True,
    )
    if status == "unverified" and items:
        raise ValueError(f"field '{field}.items' must be empty when unverified")


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_request(request: Dict[str, Any]) -> None:
    expect_type(request, dict, "request")
    unknown = set(request.keys()) - REQUEST_ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"unknown request fields: {sorted(unknown)}")
    missing = REQUEST_REQUIRED_FIELDS - set(request.keys())
    if missing:
        raise ValueError(f"missing request fields: {sorted(missing)}")

    if request["output_type"] not in REQUEST_OUTPUT_TYPES:
        raise ValueError("field 'output_type' has unsupported value")
    if request["camera_movement"] not in REQUEST_CAMERA_MOVEMENT:
        raise ValueError("field 'camera_movement' has unsupported value")
    if request["motion_complexity"] not in REQUEST_MOTION_COMPLEXITY:
        raise ValueError("field 'motion_complexity' has unsupported value")
    if request["execution_target"] not in REQUEST_EXECUTION_TARGET:
        raise ValueError("field 'execution_target' has unsupported value")
    if request["cost_tier"] not in REQUEST_COST_TIERS:
        raise ValueError("field 'cost_tier' has unsupported value")

    expect_int(request["width"], "width", minimum=1)
    expect_int(request["height"], "height", minimum=1)
    expect_int(request["character_count"], "character_count", minimum=0)
    expect_int(request["keyframe_count"], "keyframe_count", minimum=0)

    expect_finite_number(request["duration_seconds"], "duration_seconds", minimum=0.0)
    expect_finite_number(request["fps"], "fps", minimum=0.0)
    if float(request["duration_seconds"]) <= 0:
        raise ValueError("field 'duration_seconds' must be > 0")
    if float(request["fps"]) <= 0:
        raise ValueError("field 'fps' must be > 0")
    expect_finite_number(request["available_vram_gb"], "available_vram_gb", minimum=0.0)

    bool_fields = [
        "reference_video_present",
        "identity_lock_required",
        "contact_deformation_required",
        "audio_required",
        "prior_generation_failed",
        "frame_sequence_available",
        "isolated_frame_failure",
        "structured_linear_guidance",
        "promotion_required",
    ]
    for field in bool_fields:
        expect_type(request[field], bool, field)

    requested_engine = request["requested_engine"]
    if requested_engine is not None and not isinstance(requested_engine, str):
        raise ValueError("field 'requested_engine' must be string or null")
    if isinstance(requested_engine, str) and not requested_engine.strip():
        raise ValueError("field 'requested_engine' cannot be blank string")


def validate_registry(registry: Dict[str, Any]) -> None:
    expect_type(registry, dict, "registry")
    if set(registry.keys()) != {"engines"}:
        raise ValueError("registry must contain only the 'engines' field")
    expect_type(registry["engines"], list, "engines")
    seen_ids: set[str] = set()
    for idx, engine in enumerate(registry["engines"]):
        field_prefix = f"engines[{idx}]"
        expect_type(engine, dict, field_prefix)
        unknown = set(engine.keys()) - ENGINE_ALLOWED_FIELDS
        missing = ENGINE_REQUIRED_FIELDS - set(engine.keys())
        if unknown:
            raise ValueError(f"{field_prefix} has unknown fields: {sorted(unknown)}")
        if missing:
            raise ValueError(f"{field_prefix} is missing fields: {sorted(missing)}")

        engine_id = expect_non_empty_string(engine["id"], f"{field_prefix}.id")
        if engine_id in seen_ids:
            raise ValueError(f"duplicate engine id '{engine_id}'")
        seen_ids.add(engine_id)

        engine_class = expect_non_empty_string(engine["class"], f"{field_prefix}.class")
        if engine_class not in ENGINE_CLASSES:
            raise ValueError(f"{field_prefix}.class has unsupported value '{engine_class}'")

        expect_string_list(engine["best_for"], f"{field_prefix}.best_for")
        validate_verified_scalar_record(engine["model_registry_link"], f"{field_prefix}.model_registry_link")
        validate_verified_scalar_record(engine["object_info_evidence"], f"{field_prefix}.object_info_evidence")
        validate_verified_scalar_record(engine["runtime_proof"], f"{field_prefix}.runtime_proof")
        validate_verified_values_record(
            engine["supported_outputs"], f"{field_prefix}.supported_outputs", ENGINE_SUPPORTED_OUTPUTS
        )
        validate_verified_values_record(
            engine["supported_features"], f"{field_prefix}.supported_features", ENGINE_SUPPORTED_FEATURES
        )
        validate_verified_limits_record(engine["resource_limits"], f"{field_prefix}.resource_limits")
        validate_verified_values_record(
            engine["execution_targets"], f"{field_prefix}.execution_targets", ENGINE_EXECUTION_TARGETS
        )
        validate_verified_values_record(
            engine["cost_tiers"], f"{field_prefix}.cost_tiers", ENGINE_COST_TIERS
        )
        validate_verified_availability(engine["availability"], f"{field_prefix}.availability")
        validate_verified_items_record(engine["promotion_proof"], f"{field_prefix}.promotion_proof")


def validate_rules(rules_data: Dict[str, Any]) -> None:
    expect_type(rules_data, dict, "rules")
    if set(rules_data.keys()) != {"rules"}:
        raise ValueError("rules payload must contain only the 'rules' field")
    expect_type(rules_data["rules"], list, "rules")
    seen_rule_ids: set[str] = set()
    seen_priorities: set[int] = set()
    for idx, rule in enumerate(rules_data["rules"]):
        expect_type(rule, dict, f"rules[{idx}]")
        unknown = set(rule.keys()) - RULE_REQUIRED_FIELDS
        missing = RULE_REQUIRED_FIELDS - set(rule.keys())
        if unknown:
            raise ValueError(f"rules[{idx}] has unknown fields: {sorted(unknown)}")
        if missing:
            raise ValueError(f"rules[{idx}] is missing fields: {sorted(missing)}")
        rule_id = expect_non_empty_string(rule["id"], f"rules[{idx}].id")
        if rule_id in seen_rule_ids:
            raise ValueError(f"duplicate rule id '{rule_id}'")
        seen_rule_ids.add(rule_id)
        expect_int(rule["priority"], f"rules[{idx}].priority", minimum=0)
        if rule["priority"] in seen_priorities:
            raise ValueError(f"duplicate rule priority '{rule['priority']}'")
        seen_priorities.add(rule["priority"])
        expect_non_empty_string(rule["route"], f"rules[{idx}].route")
        expect_type(rule["all"], list, f"rules[{idx}].all")
        for cond_idx, cond in enumerate(rule["all"]):
            expect_type(cond, dict, f"rules[{idx}].all[{cond_idx}]")
            unknown = set(cond.keys()) - RULE_CONDITION_KEYS
            missing = RULE_CONDITION_KEYS - set(cond.keys())
            if unknown:
                raise ValueError(
                    f"rules[{idx}].all[{cond_idx}] has unknown fields: {sorted(unknown)}"
                )
            if missing:
                raise ValueError(
                    f"rules[{idx}].all[{cond_idx}] missing fields: {sorted(missing)}"
                )
            field_name = expect_non_empty_string(cond["field"], f"rules[{idx}].all[{cond_idx}].field")
            if field_name not in REQUEST_ALLOWED_FIELDS:
                raise ValueError(
                    f"rules[{idx}].all[{cond_idx}] references unknown request field '{field_name}'"
                )
            op = expect_non_empty_string(cond["op"], f"rules[{idx}].all[{cond_idx}].op")
            if op not in RULE_ALLOWED_OPS:
                raise ValueError(
                    f"rules[{idx}].all[{cond_idx}] has unsupported op '{cond['op']}'"
                )
            expected_type = REQUEST_FIELD_TYPES[field_name]
            cond_value = cond["value"]
            if op in {"gte", "lte"} and expected_type not in {"int", "number"}:
                raise ValueError(
                    f"rules[{idx}].all[{cond_idx}] op '{op}' incompatible with field '{field_name}'"
                )
            if expected_type == "bool":
                if not isinstance(cond_value, bool):
                    raise ValueError(
                        f"rules[{idx}].all[{cond_idx}] value must be boolean for '{field_name}'"
                    )
            elif expected_type == "int":
                if not isinstance(cond_value, int) or isinstance(cond_value, bool):
                    raise ValueError(
                        f"rules[{idx}].all[{cond_idx}] value must be integer for '{field_name}'"
                    )
            elif expected_type == "number":
                if not isinstance(cond_value, (int, float)) or isinstance(cond_value, bool):
                    raise ValueError(
                        f"rules[{idx}].all[{cond_idx}] value must be number for '{field_name}'"
                    )
                if not math.isfinite(float(cond_value)):
                    raise ValueError(
                        f"rules[{idx}].all[{cond_idx}] value must be finite for '{field_name}'"
                    )
            elif expected_type == "string":
                expect_non_empty_string(cond_value, f"rules[{idx}].all[{cond_idx}].value")
            elif expected_type == "string_or_null":
                if cond_value is not None:
                    expect_non_empty_string(cond_value, f"rules[{idx}].all[{cond_idx}].value")


def is_verified(record: Dict[str, Any], expected_key: str) -> Tuple[bool, str]:
    if not isinstance(record, dict):
        return False, "invalid_record_shape"
    if record.get("verification_status") != "verified":
        return False, "unverified"
    if record.get(expected_key) in (None, "", []):
        return False, "verified_but_empty"
    return True, ""


def evaluate_rule_matches(
    request: Dict[str, Any],
    rules_data: Dict[str, Any],
) -> Tuple[List[str], List[str]]:
    matched: List[Tuple[int, str, str]] = []
    for rule in sorted(rules_data["rules"], key=lambda item: item["priority"]):
        matches = True
        for cond in rule["all"]:
            field = cond["field"]
            op = cond["op"]
            value = cond["value"]
            if field not in request:
                matches = False
                break
            request_value = request[field]
            if op == "eq":
                if request_value != value:
                    matches = False
                    break
            elif op == "gte":
                if request_value < value:
                    matches = False
                    break
            elif op == "lte":
                if request_value > value:
                    matches = False
                    break
        if matches:
            matched.append((rule["priority"], rule["id"], rule["route"]))
    routes: List[str] = []
    matched_rule_ids: List[str] = []
    seen_routes: set[str] = set()
    for _, rule_id, route in matched:
        matched_rule_ids.append(rule_id)
        if route not in seen_routes:
            routes.append(route)
            seen_routes.add(route)
    return routes, matched_rule_ids


def required_features_from_request(request: Dict[str, Any]) -> List[str]:
    features: List[str] = []
    if request["reference_video_present"]:
        features.append("reference_video_input")
    if request["keyframe_count"] > 0:
        features.append("keyframes")
    if request["identity_lock_required"]:
        features.append("identity_lock")
    if request["contact_deformation_required"]:
        features.append("contact_deformation")
    if request["audio_required"]:
        features.append("audio_sync")
    if request["isolated_frame_failure"]:
        features.append("frame_repair")
    if request["prior_generation_failed"] and request["frame_sequence_available"]:
        features.append("frame_sequence_bridge")
    if request["motion_complexity"] == "high":
        features.append("high_motion")
    if request["camera_movement"] in {"moderate", "high"}:
        features.append("camera_motion_control")
    if request["structured_linear_guidance"]:
        features.append("structured_linear_guidance")
    return sorted(set(features))


def get_candidates(request: Dict[str, Any], rules_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    requested = request["requested_engine"]
    if requested:
        return [requested], ["requested_engine_override"]
    return evaluate_rule_matches(request, rules_data)


def evaluate_engine(
    request: Dict[str, Any],
    engine: Dict[str, Any],
    required_features: List[str],
) -> Dict[str, Any]:
    blocked_reasons: List[str] = []
    required_proof: List[str] = []

    model_ok, model_reason = is_verified(engine["model_registry_link"], "value")
    if not model_ok:
        blocked_reasons.append(f"model_registry_link:{model_reason}")
        required_proof.append("model_registry_link_verified")

    object_ok, object_reason = is_verified(engine["object_info_evidence"], "value")
    if not object_ok:
        blocked_reasons.append(f"object_info_evidence:{object_reason}")
        required_proof.append("object_info_verified")

    runtime_ok, runtime_reason = is_verified(engine["runtime_proof"], "value")
    if not runtime_ok:
        blocked_reasons.append(f"runtime_proof:{runtime_reason}")
        required_proof.append("runtime_proof_verified")

    availability_ok = False
    if isinstance(engine["availability"], dict):
        availability_ok = (
            engine["availability"].get("verification_status") == "verified"
            and engine["availability"].get("state") == "available"
        )
    if not availability_ok:
        blocked_reasons.append("availability:unverified_or_unavailable")
        required_proof.append("availability_verified")

    outputs_ok = False
    if isinstance(engine["supported_outputs"], dict):
        outputs_ok = (
            engine["supported_outputs"].get("verification_status") == "verified"
            and request["output_type"] in engine["supported_outputs"].get("values", [])
        )
    if not outputs_ok:
        blocked_reasons.append("supported_outputs:unsupported_or_unverified")
        required_proof.append("supported_outputs_verified")

    features_ok = False
    supported_features_values: List[str] = []
    if isinstance(engine["supported_features"], dict):
        supported_features_values = engine["supported_features"].get("values", [])
        features_ok = (
            engine["supported_features"].get("verification_status") == "verified"
            and all(feature in supported_features_values for feature in required_features)
        )
    if not features_ok:
        blocked_reasons.append("supported_features:missing_or_unverified")
        required_proof.append("supported_features_verified")

    execution_ok = False
    if isinstance(engine["execution_targets"], dict):
        execution_ok = (
            engine["execution_targets"].get("verification_status") == "verified"
            and request["execution_target"] in engine["execution_targets"].get("values", [])
        )
    if not execution_ok:
        blocked_reasons.append("execution_targets:unsupported_or_unverified")
        required_proof.append("execution_targets_verified")

    cost_ok = False
    if isinstance(engine["cost_tiers"], dict):
        cost_ok = (
            engine["cost_tiers"].get("verification_status") == "verified"
            and request["cost_tier"] in engine["cost_tiers"].get("values", [])
        )
    if not cost_ok:
        blocked_reasons.append("cost_tiers:unsupported_or_unverified")
        required_proof.append("cost_tiers_verified")

    resource_ok = False
    limits = engine["resource_limits"]
    if isinstance(limits, dict) and limits.get("verification_status") == "verified":
        width_ok = request["width"] <= limits.get("max_width", -1)
        height_ok = request["height"] <= limits.get("max_height", -1)
        duration_ok = request["duration_seconds"] <= limits.get("max_duration_seconds", -1)
        fps_ok = request["fps"] <= limits.get("max_fps", -1)
        vram_ok = request["available_vram_gb"] >= limits.get("min_vram_gb", math.inf)
        resource_ok = width_ok and height_ok and duration_ok and fps_ok and vram_ok
    if not resource_ok:
        blocked_reasons.append("resource_limits:insufficient_or_unverified")
        required_proof.append("resource_limits_verified")

    promotion_ok = not request["promotion_required"]
    if request["promotion_required"]:
        if isinstance(engine["promotion_proof"], dict):
            promotion_ok = (
                engine["promotion_proof"].get("verification_status") == "verified"
                and len(engine["promotion_proof"].get("items", [])) > 0
            )
        if not promotion_ok:
            blocked_reasons.append("promotion_proof:required_and_unverified")
            required_proof.append("promotion_proof_verified")

    compatibility_passed = (
        model_ok
        and object_ok
        and runtime_ok
        and outputs_ok
        and features_ok
        and execution_ok
    )
    resource_passed = resource_ok and cost_ok
    availability_passed = availability_ok
    promotion_passed = promotion_ok
    can_select = (
        compatibility_passed
        and resource_passed
        and availability_passed
        and promotion_passed
    )

    return {
        "engine_id": engine["id"],
        "compatibility_passed": compatibility_passed,
        "resource_passed": resource_passed,
        "availability_passed": availability_passed,
        "promotion_passed": promotion_passed,
        "can_select": can_select,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "required_proof": sorted(set(required_proof)),
    }


def decide_route(
    request: Dict[str, Any],
    registry: Dict[str, Any],
    rules_data: Dict[str, Any],
) -> Dict[str, Any]:
    validate_request(request)
    validate_registry(registry)
    validate_rules(rules_data)

    registered_ids = {engine["id"] for engine in registry["engines"]}
    for rule in rules_data["rules"]:
        if rule["route"] not in registered_ids:
            raise ValueError(f"rule route '{rule['route']}' is not registered")

    request_sha256 = canonical_json_sha256(request)
    registry_sha256 = canonical_json_sha256(registry)
    rules_sha256 = canonical_json_sha256(rules_data)

    engines_by_id = {engine["id"]: engine for engine in registry["engines"]}
    candidates, matched_rule_ids = get_candidates(request, rules_data)
    required_features = required_features_from_request(request)

    evaluations: List[Dict[str, Any]] = []
    blocked_reasons: List[str] = []
    required_proof: List[str] = []

    if not candidates:
        blocked_reasons.append("no_rule_candidate")

    for candidate in candidates:
        engine = engines_by_id.get(candidate)
        if engine is None:
            blocked_reasons.append(f"candidate_not_registered:{candidate}")
            required_proof.append(f"registry_entry_required:{candidate}")
            continue
        evaluation = evaluate_engine(request, engine, required_features)
        evaluations.append(evaluation)
        blocked_reasons.extend([f"{candidate}:{item}" for item in evaluation["blocked_reasons"]])
        required_proof.extend(evaluation["required_proof"])
        if evaluation["can_select"]:
            return {
                "selected_engine": candidate,
                "result": "compatible",
                "decision_scope": DECISION_SCOPE,
                "runtime_ready": True,
                "final_promotion_ready": False,
                "request_sha256": request_sha256,
                "registry_sha256": registry_sha256,
                "rules_sha256": rules_sha256,
                "matched_rule_ids": matched_rule_ids,
                "required_features": required_features,
                "candidate_order": candidates,
                "engine_evaluations": evaluations,
                "blocked_reasons": sorted(set(blocked_reasons)),
                "required_proof": sorted(set(required_proof)),
            }

    return {
        "selected_engine": None,
        "result": "blocked",
        "decision_scope": DECISION_SCOPE,
        "runtime_ready": False,
        "final_promotion_ready": False,
        "request_sha256": request_sha256,
        "registry_sha256": registry_sha256,
        "rules_sha256": rules_sha256,
        "matched_rule_ids": matched_rule_ids,
        "required_features": required_features,
        "candidate_order": candidates,
        "engine_evaluations": evaluations,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "required_proof": sorted(set(required_proof)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline video engine routing tool")
    script_path = Path(__file__).resolve()
    default_root = script_path.parents[2]
    parser.add_argument(
        "--request",
        required=True,
        help="Path to request JSON file",
    )
    parser.add_argument(
        "--registry",
        default=str(default_root / "10_REGISTRIES" / "wave27_video_engine_registry.json"),
        help="Path to video engine registry JSON file",
    )
    parser.add_argument(
        "--rules",
        default=str(default_root / "10_REGISTRIES" / "wave27_video_route_selection_rules.json"),
        help="Path to video route rules JSON file",
    )
    parser.add_argument(
        "--output",
        help="Optional path for decision JSON output file",
    )
    return parser


def write_json_output(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cli_error_payload(error: Exception) -> Dict[str, Any]:
    return {
        "result": "blocked",
        "selected_engine": None,
        "decision_scope": DECISION_SCOPE,
        "runtime_ready": False,
        "final_promotion_ready": False,
        "request_sha256": None,
        "registry_sha256": None,
        "rules_sha256": None,
        "matched_rule_ids": [],
        "required_features": [],
        "candidate_order": [],
        "engine_evaluations": [],
        "blocked_reasons": [f"validation_error:{error}"],
        "required_proof": ["valid_input_registry_rules_required"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        request = load_json(Path(args.request))
        registry = load_json(Path(args.registry))
        rules_data = load_json(Path(args.rules))
        decision = decide_route(request, registry, rules_data)
    except Exception as exc:
        error_payload = cli_error_payload(exc)
        sys.stderr.write(json.dumps(error_payload, sort_keys=True) + "\n")
        return 1

    try:
        decision_text = json.dumps(decision, indent=2, sort_keys=True)
        if args.output:
            write_json_output(Path(args.output), decision)
        else:
            print(decision_text)
    except Exception as exc:
        error_payload = cli_error_payload(exc)
        sys.stderr.write(json.dumps(error_payload, sort_keys=True) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
