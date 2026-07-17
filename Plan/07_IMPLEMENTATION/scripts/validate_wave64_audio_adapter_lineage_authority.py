#!/usr/bin/env python3
"""Validate fail-closed Wave64 Rows189-192 audio adapter authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_audio_adapter_lineage_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_audio_adapter_lineage_authority.schema.json")
REQUIRED_SOURCES = {
    "functional_audio_index_registry", "audio_event_graph_schema", "audio_stem_manifest_schema",
    "audio_mix_manifest_schema", "human_playback_proof_schema", "room_spatial_runtime_evidence",
    "mmaudio_mux_evidence", "speech_control_evidence",
}
REQUIRED_INTENTS = {
    "voice_binding", "dialogue", "nonverbal_vocalization", "contact_force", "environment",
    "distance", "room", "timing", "character_owner",
}
REQUIRED_ADAPTERS = {
    "speech", "nonverbal_vocalization", "foley", "ambience", "music",
    "room", "spatial", "enhancement", "mix",
}
REQUIRED_LINEAGE_FIELDS = {
    "event_ref", "source_ref", "character_ref", "attempt_ref", "transform_ref", "mix_decision_ref",
}
REQUIRED_PROMOTION_GATES = {
    "identity", "prosody", "timing", "acoustics", "defect_scan", "full_audio",
    "continuity", "provenance", "stem_isolation", "full_duration_playback",
    "synchronization", "revocation",
}


class AudioAdapterAuthorityError(ValueError):
    """Raised when audio adapter authority crosses a fail-closed boundary."""


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
        raise AudioAdapterAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_bound(root: Path, reference: dict[str, str], label: str) -> dict[str, Any]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise AudioAdapterAuthorityError(f"bound_path_not_relative:{label}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise AudioAdapterAuthorityError(f"bound_file_missing_or_outside:{label}")
    if sha256_file(path) != reference["sha256"]:
        raise AudioAdapterAuthorityError(f"bound_hash_mismatch:{label}")
    return load_json(path)


def validate_sources(root: Path, authority: dict[str, Any]) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for reference in authority["source_authorities"]:
        name = reference["name"]
        if name in loaded:
            raise AudioAdapterAuthorityError("duplicate_source_authority_name")
        loaded[name] = load_bound(root, reference, name)
    if set(loaded) != REQUIRED_SOURCES:
        raise AudioAdapterAuthorityError("source_authority_exact_set_mismatch")
    index = loaded["functional_audio_index_registry"]
    if index["functional_index"]["audio_file_count"] != 39771 or index["functional_index"]["content_based_suppression"]:
        raise AudioAdapterAuthorityError("functional_index_boundary_mismatch")
    room = loaded["room_spatial_runtime_evidence"]
    if room["classification"] != "W64_ROWS029_030_056_FULL_MIX_TECHNICAL_RUNTIME_PASS_AUTHORITY_BLOCKED":
        raise AudioAdapterAuthorityError("room_spatial_source_classification_mismatch")
    if room["pass_like"] or room["row_complete"]:
        raise AudioAdapterAuthorityError("room_spatial_source_false_completion")
    mux = loaded["mmaudio_mux_evidence"]
    if mux["classification"] != "GENUINE_MMAUDIO_REVIEW_MUX_TECHNICAL_PASS":
        raise AudioAdapterAuthorityError("mmaudio_source_classification_mismatch")
    speech = loaded["speech_control_evidence"]
    if speech["row_complete"]:
        raise AudioAdapterAuthorityError("speech_source_false_completion")
    return loaded


def validate_intent_binding(authority: dict[str, Any]) -> dict[str, int]:
    binding = authority["shot_audio_intent_binding"]
    intents = {entry["intent_type"] for entry in binding["bindings"]}
    if intents != REQUIRED_INTENTS or len(binding["bindings"]) != len(REQUIRED_INTENTS):
        raise AudioAdapterAuthorityError("audio_intent_exact_set_mismatch")
    if any(entry["authority_ref"] is not None or entry["status"] != "unbound" for entry in binding["bindings"]):
        raise AudioAdapterAuthorityError("audio_intent_false_authority_binding")
    if binding["event_graph_emitted"] or binding["execution_allowed"]:
        raise AudioAdapterAuthorityError("audio_intent_false_execution")
    if binding["rows_067_148_reused"] is not True or binding["duplicate_generation_allowed"]:
        raise AudioAdapterAuthorityError("audio_reuse_boundary_failed")
    return {"audio_intent_binding_count": len(intents)}


def validate_adapters(authority: dict[str, Any]) -> dict[str, int]:
    adapters = authority["adapter_library"]
    ids = {entry["adapter_id"] for entry in adapters}
    if ids != REQUIRED_ADAPTERS or len(adapters) != len(REQUIRED_ADAPTERS):
        raise AudioAdapterAuthorityError("audio_adapter_exact_set_mismatch")
    stem_ids: set[str] = set()
    for adapter in adapters:
        if adapter["selected_stack_ref"] is not None or adapter["workflow_release_ref"] is not None:
            raise AudioAdapterAuthorityError(f"audio_adapter_false_runtime_binding:{adapter['adapter_id']}")
        if adapter["status"] != "blocked_missing_exact_stack_or_input" or adapter["execution_allowed"]:
            raise AudioAdapterAuthorityError(f"audio_adapter_false_execution:{adapter['adapter_id']}")
        if adapter["package_contract_version"] != "1.0.0" or not adapter["stack_requirements"]:
            raise AudioAdapterAuthorityError(f"audio_adapter_contract_incomplete:{adapter['adapter_id']}")
        if adapter["timebase"]["sample_rate_hz"] != 48000 or adapter["timebase"]["frame_rate_numerator"] != 24:
            raise AudioAdapterAuthorityError(f"audio_adapter_timebase_mismatch:{adapter['adapter_id']}")
        if not adapter["provenance_fields"] or not adapter["qa_gate_ids"]:
            raise AudioAdapterAuthorityError(f"audio_adapter_provenance_or_qa_missing:{adapter['adapter_id']}")
        stem_ids.add(adapter["output_stem_id"])
    if len(stem_ids) != len(adapters):
        raise AudioAdapterAuthorityError("audio_adapter_output_stems_not_unique")
    return {"audio_adapter_count": len(adapters), "declared_stem_count": len(stem_ids)}


def validate_lineage(authority: dict[str, Any]) -> dict[str, int]:
    pipeline = authority["sample_lineage_pipeline"]
    fields = set(pipeline["required_lineage_fields"])
    if fields != REQUIRED_LINEAGE_FIELDS:
        raise AudioAdapterAuthorityError("sample_lineage_field_exact_set_mismatch")
    if pipeline["sample_span_manifest_ref"] is not None or pipeline["execution_receipt_ref"] is not None:
        raise AudioAdapterAuthorityError("sample_lineage_false_runtime_record")
    if pipeline["status"] != "blocked_no_complete_sample_manifest" or pipeline["execution_allowed"]:
        raise AudioAdapterAuthorityError("sample_lineage_false_execution")
    replacements = pipeline["stem_replacement_policy"]
    if {entry["stem_id"] for entry in replacements} != {entry["output_stem_id"] for entry in authority["adapter_library"]}:
        raise AudioAdapterAuthorityError("stem_replacement_set_mismatch")
    if any(not entry["independently_replaceable"] or not entry["unaffected_stems_immutable"] for entry in replacements):
        raise AudioAdapterAuthorityError("stem_replacement_boundary_failed")
    return {"sample_lineage_field_count": len(fields), "replaceable_stem_count": len(replacements)}


def validate_promotion(authority: dict[str, Any]) -> dict[str, int]:
    gate = authority["promotion_revocation_gate"]
    gates = {entry["gate_id"] for entry in gate["gate_results"]}
    if gates != REQUIRED_PROMOTION_GATES or len(gate["gate_results"]) != len(REQUIRED_PROMOTION_GATES):
        raise AudioAdapterAuthorityError("audio_promotion_gate_exact_set_mismatch")
    if any(entry["status"] != "not_run" or entry["evidence_refs"] for entry in gate["gate_results"]):
        raise AudioAdapterAuthorityError("audio_promotion_false_gate_result")
    if gate["audio_package_ref"] is not None or gate["promotion_transaction_ref"] is not None:
        raise AudioAdapterAuthorityError("audio_promotion_false_package_or_transaction")
    if gate["complete_synchronized_package"] or gate["promotion_allowed"] or gate["decision"] != "blocked":
        raise AudioAdapterAuthorityError("audio_promotion_boundary_failed")
    if not gate["local_stem_gain_requires_global_regression_pass"] or not gate["revocation_ready"]:
        raise AudioAdapterAuthorityError("audio_global_regression_or_revocation_missing")
    return {"audio_promotion_gate_count": len(gates)}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema, "audio_adapter_lineage_authority")
    validate_sources(root, authority)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_AUDIO_ADAPTER_LINEAGE_AUTHORITY_SLICE_PASS",
        "rows_covered": [189, 190, 191, 192],
        "runtime_scope": "blocked_contract_validation_and_existing_evidence_reuse_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "promotion_allowed": authority["promotion_allowed"],
    }
    result.update(validate_intent_binding(authority))
    result.update(validate_adapters(authority))
    result.update(validate_lineage(authority))
    result.update(validate_promotion(authority))
    if any(authority["boundaries"].values()):
        raise AudioAdapterAuthorityError("authority_false_completion_boundary")
    return result


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "evidence_type": "wave64_audio_adapter_lineage_authority_slice_validation",
        **result,
        "authority": {
            "registry_path": registry_path.as_posix(), "registry_sha256": sha256_file(root / registry_path),
            "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_adapter_lineage_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_adapter_lineage_authority.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T080430963Z_wave64_rows189_192_audio_adapter_lineage_authority_f154973e",
            "result": "AI_WORKER_ADMISSION_REJECTED_UNTRACKED_PROSPECTIVE_SCOPE",
            "fallback": "bounded_codex_implementation_and_deterministic_validation",
        },
        "boundaries": {
            "audio_media_regenerated": False, "functional_index_rebuilt": False,
            "subjective_review_fabricated": False, "production_identity_claimed": False,
            "room_geometry_claimed": False, "runtime_execution_claimed": False,
            "complete_audio_package_claimed": False, "promotion_transaction_created": False,
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
