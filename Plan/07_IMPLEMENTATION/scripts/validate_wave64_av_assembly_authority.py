#!/usr/bin/env python3
"""Validate fail-closed Wave64 Rows193-196 AV assembly authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_av_assembly_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_av_assembly_authority.schema.json")
REQUIRED_SOURCES = {
    "video_adapter_evidence", "audio_adapter_evidence", "room_spatial_runtime_evidence",
    "mmaudio_mux_evidence", "av_sync_evaluation_schema", "av_local_repair_schema",
    "av_promotion_certificate_schema", "av_sync_gate_registry",
}
REQUIRED_TIMELINE_FIELDS = {"cuts", "dialogue", "events", "offsets", "handles", "ownership"}
REQUIRED_COMPONENTS = {
    "video", "audio_master", "individual_stems", "captions", "metadata", "codecs",
    "hashes", "source_lineage",
}
REQUIRED_RECONCILIATION = {"stream_set", "durations", "artifact_hashes", "manifest_bindings", "codec_metadata"}
REQUIRED_DEFECT_CLASSES = {"lip_sync", "event_sync", "cumulative_drift", "constant_offset", "source_timing", "mux_timing"}
REQUIRED_PACKAGE_CONTENTS = {"video", "audio", "stems", "timeline", "captions", "hashes", "qa", "playback", "decisions", "rollback", "revocation"}
REQUIRED_CERTIFICATION_GATES = {"sync", "identity", "continuity", "technical", "provenance", "full_playback"}


class AVAssemblyAuthorityError(ValueError):
    """Raised when AV assembly authority crosses a fail-closed boundary."""


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
        raise AVAssemblyAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_bound(root: Path, reference: dict[str, str], label: str) -> dict[str, Any]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise AVAssemblyAuthorityError(f"bound_path_not_relative:{label}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise AVAssemblyAuthorityError(f"bound_file_missing_or_outside:{label}")
    if sha256_file(path) != reference["sha256"]:
        raise AVAssemblyAuthorityError(f"bound_hash_mismatch:{label}")
    return load_json(path)


def validate_sources(root: Path, authority: dict[str, Any]) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for reference in authority["source_authorities"]:
        name = reference["name"]
        if name in loaded:
            raise AVAssemblyAuthorityError("duplicate_source_authority_name")
        loaded[name] = load_bound(root, reference, name)
    if set(loaded) != REQUIRED_SOURCES:
        raise AVAssemblyAuthorityError("source_authority_exact_set_mismatch")
    video = loaded["video_adapter_evidence"]
    audio = loaded["audio_adapter_evidence"]
    if video.get("classification") != "WAVE64_VIDEO_ADAPTER_AUTHORITY_SLICE_PASS":
        raise AVAssemblyAuthorityError("video_source_classification_mismatch")
    if audio.get("classification") != "WAVE64_AUDIO_ADAPTER_LINEAGE_AUTHORITY_SLICE_PASS":
        raise AVAssemblyAuthorityError("audio_source_classification_mismatch")
    if any(source.get("runtime_execution_allowed") or source.get("promotion_allowed") for source in (video, audio)):
        raise AVAssemblyAuthorityError("parent_source_false_runtime_or_promotion")
    room = loaded["room_spatial_runtime_evidence"]
    if room.get("classification") != "W64_ROWS029_030_056_FULL_MIX_TECHNICAL_RUNTIME_PASS_AUTHORITY_BLOCKED":
        raise AVAssemblyAuthorityError("room_source_classification_mismatch")
    if room.get("pass_like") or room.get("row_complete"):
        raise AVAssemblyAuthorityError("room_source_false_completion")
    mux = loaded["mmaudio_mux_evidence"]
    if mux.get("classification") != "GENUINE_MMAUDIO_REVIEW_MUX_TECHNICAL_PASS" or mux.get("promotion_allowed"):
        raise AVAssemblyAuthorityError("mmaudio_source_boundary_mismatch")
    return loaded


def validate_clock(authority: dict[str, Any]) -> dict[str, int]:
    clock = authority["canonical_av_clock"]
    fields = clock["required_timeline_fields"]
    if set(fields) != REQUIRED_TIMELINE_FIELDS or len(fields) != len(REQUIRED_TIMELINE_FIELDS):
        raise AVAssemblyAuthorityError("timeline_field_exact_set_mismatch")
    expected = clock["sample_rate_hz"] * clock["frame_rate_denominator"]
    if expected % clock["frame_rate_numerator"]:
        raise AVAssemblyAuthorityError("clock_non_integer_sample_frame_ratio")
    if expected // clock["frame_rate_numerator"] != clock["samples_per_frame"]:
        raise AVAssemblyAuthorityError("clock_sample_frame_conversion_mismatch")
    if not clock["monotonic"] or clock["cumulative_drift_allowed"] or clock["rounding_policy"] != "exact_integer_only":
        raise AVAssemblyAuthorityError("clock_drift_or_rounding_boundary_failed")
    if clock["timeline_manifest_ref"] is not None or clock["execution_receipt_ref"] is not None:
        raise AVAssemblyAuthorityError("clock_false_runtime_binding")
    return {"timeline_field_count": len(fields), "samples_per_frame": clock["samples_per_frame"]}


def validate_mux(authority: dict[str, Any]) -> dict[str, int]:
    mux = authority["mux_assembly_contract"]
    components = mux["retained_components"]
    if set(components) != REQUIRED_COMPONENTS or len(components) != len(REQUIRED_COMPONENTS):
        raise AVAssemblyAuthorityError("mux_retained_component_exact_set_mismatch")
    checks = mux["reconciliation_checks"]
    if {item["check_id"] for item in checks} != REQUIRED_RECONCILIATION or len(checks) != len(REQUIRED_RECONCILIATION):
        raise AVAssemblyAuthorityError("mux_reconciliation_exact_set_mismatch")
    if any(item["status"] != "not_run" or item["evidence_refs"] for item in checks):
        raise AVAssemblyAuthorityError("mux_false_reconciliation_result")
    if mux["accepted_video_ref"] is not None or mux["accepted_audio_ref"] is not None or mux["output_artifact_ref"] is not None:
        raise AVAssemblyAuthorityError("mux_false_artifact_binding")
    if not mux["accepted_inputs_only"] or mux["unapproved_substitution_allowed"] or mux["assembly_executed"]:
        raise AVAssemblyAuthorityError("mux_execution_or_substitution_boundary_failed")
    return {"retained_component_count": len(components), "reconciliation_check_count": len(checks)}


def validate_repair(authority: dict[str, Any]) -> dict[str, int]:
    repair = authority["localized_sync_repair"]
    defects = repair["defect_classes"]
    if set(defects) != REQUIRED_DEFECT_CLASSES or len(defects) != len(REQUIRED_DEFECT_CLASSES):
        raise AVAssemblyAuthorityError("repair_defect_class_exact_set_mismatch")
    if repair["target_span"] is not None or repair["target_stem_ref"] is not None or repair["candidate_artifact_ref"] is not None:
        raise AVAssemblyAuthorityError("repair_false_target_or_artifact")
    if not repair["accepted_parents_immutable"] or not repair["smallest_authoritative_scope_only"]:
        raise AVAssemblyAuthorityError("repair_parent_or_scope_boundary_failed")
    if repair["full_regeneration_allowed"] or repair["repair_executed"]:
        raise AVAssemblyAuthorityError("repair_false_execution")
    if not repair["complete_av_regression_required"] or repair["complete_av_regression_status"] != "not_run":
        raise AVAssemblyAuthorityError("repair_regression_boundary_failed")
    return {"repair_defect_class_count": len(defects)}


def validate_certification(authority: dict[str, Any]) -> dict[str, int]:
    package = authority["certification_package"]
    contents = package["required_contents"]
    if set(contents) != REQUIRED_PACKAGE_CONTENTS or len(contents) != len(REQUIRED_PACKAGE_CONTENTS):
        raise AVAssemblyAuthorityError("certification_content_exact_set_mismatch")
    gates = package["gate_results"]
    if {item["gate_id"] for item in gates} != REQUIRED_CERTIFICATION_GATES or len(gates) != len(REQUIRED_CERTIFICATION_GATES):
        raise AVAssemblyAuthorityError("certification_gate_exact_set_mismatch")
    if any(item["status"] != "not_run" or item["evidence_refs"] for item in gates):
        raise AVAssemblyAuthorityError("certification_false_gate_result")
    if package["package_ref"] is not None or package["promotion_transaction_ref"] is not None:
        raise AVAssemblyAuthorityError("certification_false_package_or_transaction")
    if not package["independent_review_required"] or not package["rollback_ready"] or not package["revocation_ready"]:
        raise AVAssemblyAuthorityError("certification_authority_or_recovery_missing")
    if package["certification_decision"] != "blocked":
        raise AVAssemblyAuthorityError("certification_false_decision")
    return {"certification_content_count": len(contents), "certification_gate_count": len(gates)}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema, "av_assembly_authority")
    validate_sources(root, authority)
    result: dict[str, Any] = {
        "status": "PASS", "classification": "WAVE64_AV_ASSEMBLY_AUTHORITY_SLICE_PASS",
        "rows_covered": [193, 194, 195, 196],
        "runtime_scope": "blocked_contract_validation_and_existing_technical_evidence_reuse_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "promotion_allowed": authority["promotion_allowed"],
    }
    result.update(validate_clock(authority))
    result.update(validate_mux(authority))
    result.update(validate_repair(authority))
    result.update(validate_certification(authority))
    if any(authority["boundaries"].values()):
        raise AVAssemblyAuthorityError("authority_false_completion_boundary")
    return result


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "evidence_type": "wave64_av_assembly_authority_slice_validation",
        **result,
        "authority": {
            "registry_path": registry_path.as_posix(), "registry_sha256": sha256_file(root / registry_path),
            "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_av_assembly_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_av_assembly_authority.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T081620217Z_wave64_rows193_196_av_assembly_authority_fb02d1e0",
            "result": "AI_WORKER_ADMISSION_REJECTED_UNTRACKED_PROSPECTIVE_SCOPE",
            "fallback": "bounded_codex_implementation_and_deterministic_validation",
        },
        "boundaries": {
            "media_remuxed": False, "media_regenerated": False, "accepted_inputs_claimed": False,
            "runtime_execution_claimed": False, "subjective_review_fabricated": False,
            "production_certification_claimed": False, "promotion_transaction_created": False,
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
