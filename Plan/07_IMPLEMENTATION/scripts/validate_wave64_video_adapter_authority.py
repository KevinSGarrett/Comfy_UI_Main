#!/usr/bin/env python3
"""Validate fail-closed Wave64 Rows185-188 video adapter authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_video_adapter_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_video_adapter_authority.schema.json")
REQUIRED_SOURCE_NAMES = {
    "image_dag_evidence",
    "keyframe_authority_schema",
    "video_engine_route_schema",
    "decoded_video_bridge_schema",
    "video_span_repair_schema",
    "video_temporal_qa_schema",
}
EXPECTED_SCHEMA_RECORD_TYPES = {
    "keyframe_authority_schema": "hyperreal_video_keyframe_authority",
    "video_engine_route_schema": "hyperreal_video_engine_route_decision",
    "decoded_video_bridge_schema": "hyperreal_decoded_video_bridge_qualification",
    "video_span_repair_schema": "hyperreal_video_span_repair_plan",
    "video_temporal_qa_schema": "hyperreal_video_temporal_qa_evaluation",
}
REQUIRED_KEYFRAME_INPUTS = {
    "accepted_image", "character_instances", "camera", "pose", "depth",
    "contact", "timing", "mask_bindings",
}
REQUIRED_TEMPORAL_CHECKS = {
    "frame_count", "duration", "fps", "loop_export", "lineage",
    "playback", "temporal_scorecard",
}


class VideoAdapterAuthorityError(ValueError):
    """Raised when video adapter authority crosses a fail-closed boundary."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise VideoAdapterAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_bound_file(root: Path, reference: dict[str, str], label: str) -> tuple[Path, dict[str, Any]]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise VideoAdapterAuthorityError(f"bound_path_not_relative:{label}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise VideoAdapterAuthorityError(f"bound_file_missing_or_outside:{label}")
    if sha256_file(path) != reference["sha256"]:
        raise VideoAdapterAuthorityError(f"bound_hash_mismatch:{label}")
    return path, load_json(path)


def validate_sources(root: Path, authority: dict[str, Any]) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for reference in authority["source_authorities"]:
        name = reference["name"]
        if name in loaded:
            raise VideoAdapterAuthorityError("duplicate_source_authority_name")
        _, payload = load_bound_file(root, reference, name)
        loaded[name] = payload
    if set(loaded) != REQUIRED_SOURCE_NAMES:
        raise VideoAdapterAuthorityError("source_authority_exact_set_mismatch")
    image = loaded["image_dag_evidence"]
    if image["classification"] != "WAVE64_IMAGE_DAG_AUTHORITY_SLICE_PASS":
        raise VideoAdapterAuthorityError("source_image_dag_classification_mismatch")
    if image["runtime_execution_allowed"] or image["promotion_allowed"]:
        raise VideoAdapterAuthorityError("source_image_dag_false_runtime_authority")
    for name, record_type in EXPECTED_SCHEMA_RECORD_TYPES.items():
        schema = loaded[name]
        if schema.get("properties", {}).get("record_type", {}).get("const") != record_type:
            raise VideoAdapterAuthorityError(f"source_schema_record_type_mismatch:{name}")
    return loaded


def validate_keyframe_adapter(authority: dict[str, Any]) -> dict[str, int]:
    adapter = authority["keyframe_adapter"]
    if set(adapter["required_input_contracts"]) != REQUIRED_KEYFRAME_INPUTS:
        raise VideoAdapterAuthorityError("keyframe_required_input_exact_set_mismatch")
    if adapter["source_image_artifact_ref"] is not None or adapter["keyframe_certificate_ref"] is not None:
        raise VideoAdapterAuthorityError("keyframe_false_artifact_or_certificate")
    if adapter["request_emitted"] or adapter["execution_allowed"]:
        raise VideoAdapterAuthorityError("keyframe_false_request_or_execution")
    if adapter["status"] != "blocked_no_approved_keyframe" or adapter["decision"] != "reject":
        raise VideoAdapterAuthorityError("keyframe_not_fail_closed")
    if not adapter["shot_instance_authority_preserved"] or not adapter["incompatible_keyframe_rejected"]:
        raise VideoAdapterAuthorityError("keyframe_authority_boundary_failed")
    return {"keyframe_input_contract_count": len(REQUIRED_KEYFRAME_INPUTS)}


def validate_route(authority: dict[str, Any]) -> dict[str, int]:
    route = authority["segment_route_plan"]
    segments = route["segments"]
    if len(segments) != 2 or [segment["segment_id"] for segment in segments] != ["segment_000_047", "segment_040_071"]:
        raise VideoAdapterAuthorityError("segment_route_exact_set_mismatch")
    first, second = segments
    if (first["start_frame"], first["end_frame"], second["start_frame"], second["end_frame"]) != (0, 47, 40, 71):
        raise VideoAdapterAuthorityError("segment_frame_contract_mismatch")
    if first["overlap_next_frames"] != 8 or second["overlap_previous_frames"] != 8:
        raise VideoAdapterAuthorityError("segment_overlap_contract_mismatch")
    for segment in segments:
        if segment["selected_bundle_ref"] is not None or segment["production_execution_allowed"]:
            raise VideoAdapterAuthorityError(f"segment_false_route_selection:{segment['segment_id']}")
        if segment["route_decision"] != "blocked" or not segment["temporal_constraints"]:
            raise VideoAdapterAuthorityError(f"segment_route_not_fail_closed:{segment['segment_id']}")
        if any(candidate["eligible"] or candidate["certificate_ref"] is not None for candidate in segment["evaluated_candidates"]):
            raise VideoAdapterAuthorityError(f"segment_false_candidate_eligibility:{segment['segment_id']}")
    if route["fallback_policy"] != "explicit_new_route_decision_or_block" or route["silent_substitution_allowed"]:
        raise VideoAdapterAuthorityError("segment_fallback_boundary_failed")
    return {"segment_count": len(segments), "segment_overlap_frames": 8}


def validate_bridge(authority: dict[str, Any]) -> dict[str, int]:
    bridge = authority["decoded_handoff"]
    if bridge["transfer_type"] != "decoded_frames_only" or bridge["latent_transfer_allowed"]:
        raise VideoAdapterAuthorityError("decoded_bridge_latent_boundary_failed")
    if bridge["source_bundle_ref"] is not None or bridge["target_bundle_ref"] is not None:
        raise VideoAdapterAuthorityError("decoded_bridge_false_bundle_binding")
    if bridge["certificate_ref"] is not None or bridge["execution_allowed"]:
        raise VideoAdapterAuthorityError("decoded_bridge_false_certificate_or_execution")
    if bridge["status"] != "blocked_uncertified" or bridge["roundtrip_status"] != "not_run":
        raise VideoAdapterAuthorityError("decoded_bridge_not_fail_closed")
    return {"decoded_bridge_count": 1}


def validate_span_repair(authority: dict[str, Any]) -> dict[str, int]:
    repair = authority["span_repair_plan"]
    target = repair["target_span"]
    if (target["start_frame"], target["end_frame"]) != (24, 47):
        raise VideoAdapterAuthorityError("span_repair_target_mismatch")
    accepted = [(span["start_frame"], span["end_frame"]) for span in repair["immutable_accepted_spans"]]
    if accepted != [(0, 23), (48, 71)]:
        raise VideoAdapterAuthorityError("span_repair_accepted_span_mismatch")
    if not repair["accepted_spans_immutable"] or not repair["smallest_failed_scope_only"] or repair["full_clip_rerender"]:
        raise VideoAdapterAuthorityError("span_repair_scope_boundary_failed")
    if repair["repair_executed"] or repair["candidate_span_ref"] is not None:
        raise VideoAdapterAuthorityError("span_repair_false_execution")
    if repair["boundary_reconnection_status"] != "not_run" or repair["max_attempts"] > 2:
        raise VideoAdapterAuthorityError("span_repair_boundary_or_budget_failed")
    if repair["write_mask_refs"] or repair["protected_mask_refs"]:
        raise VideoAdapterAuthorityError("span_repair_false_mask_binding")
    return {"repair_target_frame_count": target["end_frame"] - target["start_frame"] + 1}


def validate_temporal_gate(authority: dict[str, Any]) -> dict[str, int]:
    gate = authority["temporal_promotion_gate"]
    checks = {entry["check_id"] for entry in gate["checks"]}
    if checks != REQUIRED_TEMPORAL_CHECKS or len(gate["checks"]) != len(REQUIRED_TEMPORAL_CHECKS):
        raise VideoAdapterAuthorityError("temporal_check_exact_set_mismatch")
    if any(entry["status"] != "not_run" or entry["evidence_refs"] for entry in gate["checks"]):
        raise VideoAdapterAuthorityError("temporal_false_check_result")
    clock = gate["expected_clock"]
    if (clock["frame_count"], clock["fps_numerator"], clock["fps_denominator"], clock["duration_seconds"]) != (72, 24, 1, 3.0):
        raise VideoAdapterAuthorityError("temporal_expected_clock_mismatch")
    if gate["candidate_video_ref"] is not None or gate["promotion_transaction_ref"] is not None:
        raise VideoAdapterAuthorityError("temporal_false_artifact_or_promotion")
    if gate["decision"] != "blocked" or gate["promotion_allowed"] or not gate["accepted_spans_retained"]:
        raise VideoAdapterAuthorityError("temporal_gate_boundary_failed")
    return {"temporal_check_count": len(checks)}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema, "video_adapter_authority")
    validate_sources(root, authority)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_VIDEO_ADAPTER_AUTHORITY_SLICE_PASS",
        "rows_covered": [185, 186, 187, 188],
        "runtime_scope": "blocked_contract_validation_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "promotion_allowed": authority["promotion_allowed"],
    }
    result.update(validate_keyframe_adapter(authority))
    result.update(validate_route(authority))
    result.update(validate_bridge(authority))
    result.update(validate_span_repair(authority))
    result.update(validate_temporal_gate(authority))
    if any(authority["boundaries"].values()):
        raise VideoAdapterAuthorityError("authority_false_completion_boundary")
    return result


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_video_adapter_authority_slice_validation",
        **result,
        "authority": {
            "registry_path": registry_path.as_posix(),
            "registry_sha256": sha256_file(root / registry_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_video_adapter_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_video_adapter_authority.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T075135704Z_wave64_rows185_188_video_adapter_authority_74a6fce3",
            "result": "AI_WORKER_ADMISSION_REJECTED_UNTRACKED_PROSPECTIVE_SCOPE",
            "fallback": "bounded_codex_implementation_and_deterministic_validation",
        },
        "boundaries": {
            "approved_keyframe_claimed": False,
            "video_bundle_selected": False,
            "decoded_bridge_certified": False,
            "runtime_execution_claimed": False,
            "candidate_video_created": False,
            "temporal_qa_claimed": False,
            "accepted_span_mutated": False,
            "promotion_transaction_created": False,
            "item_tracker_status_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = validate_all(root, load_json(root / args.registry), load_json(root / args.schema))
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.registry, args.schema)
        if args.evidence_out:
            write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out:
            write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
