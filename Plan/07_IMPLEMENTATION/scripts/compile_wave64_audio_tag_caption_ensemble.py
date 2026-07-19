#!/usr/bin/env python3
"""Fail-closed Wave64 Row078 audio tag/caption ensemble contract slice.

Library ensemble refuses authority without accepted Row071 acoustic features,
Row075 defect/quality attributions, and Row077 semantic embeddings. Fixture mode
may emit deterministic schema-validated ensemble records that preserve conflicts,
abstain on unknowns, and prove captions never overwrite source metadata, without
promoting library completion or mutating source bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_tag_caption_ensemble_record.schema.json")
REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row078_audio_tag_caption_ensemble_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-078_audio_tag_caption_ensemble.json"
)
ROW071_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-071_WAVEFORM_FEATURE_EXTRACTION_CURRENT_DELTA_20260719.json"
)
ROW075_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
)
ROW077_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-077_SEMANTIC_AUDIO_EMBEDDING_CURRENT_DELTA_20260719.json"
)
COMPILER_REVISION = "wave64_row078_audio_tag_caption_ensemble_compiler_v0.1.0"
TAXONOMY_REVISION = "wave64_row078_audio_tag_caption_taxonomy_v0.1.0"
ENSEMBLE_POLICY_REVISION = "wave64_row078_ensemble_policy_v0.1.0"
TRACKER_ID = "TRK-W64-078"
ITEM_ID = "ITEM-W64-078"
SCHEMA_VERSION = "1.0.0"

REQUIRED_SIGNAL_FAMILIES = (
    "path_and_source_metadata",
    "deterministic_acoustic_features",
    "semantic_embeddings",
    "audio_tagging_models",
)
REQUIRED_TAG_FIELDS = (
    "event_family",
    "material",
    "intensity_band",
    "attack_characteristic",
    "room_environment",
)
UNKNOWN_SENTINEL = "unknown"
OUT_OF_TAXONOMY_SENTINEL = "out_of_taxonomy"
FIXTURE_TIMESTAMP = "2026-07-19T20:10:00Z"


class AudioTagCaptionEnsembleError(ValueError):
    """Raised when Row078 ensemble compilation violates fail-closed authority."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AudioTagCaptionEnsembleError(f"{label}_outside_project_root") from exc
    return path


def load_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, REGISTRY_PATH, "registry")
    payload = load_json(path)
    if payload.get("taxonomy_revision") != TAXONOMY_REVISION:
        raise AudioTagCaptionEnsembleError("taxonomy_registry_revision_mismatch")
    if payload.get("ensemble_policy_revision") != ENSEMBLE_POLICY_REVISION:
        raise AudioTagCaptionEnsembleError("ensemble_policy_revision_mismatch")
    if payload.get("compiler_revision") != COMPILER_REVISION:
        raise AudioTagCaptionEnsembleError("compiler_revision_mismatch")
    families = payload.get("required_signal_families")
    if not isinstance(families, list) or tuple(families) != REQUIRED_SIGNAL_FAMILIES:
        raise AudioTagCaptionEnsembleError("required_signal_families_mismatch")
    fields = payload.get("required_tag_fields")
    if not isinstance(fields, list) or tuple(fields) != REQUIRED_TAG_FIELDS:
        raise AudioTagCaptionEnsembleError("required_tag_fields_mismatch")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    acceptance_key: str,
    blocker_code: str,
    absent_code: str,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id.lower()}_delta")
    if not path.is_file():
        return {
            "tracker_id": tracker_id,
            "dependency_satisfied": False,
            "blocker_codes": [absent_code],
            "row_complete": False,
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        decision = payload.get("hold_decision") if isinstance(payload.get("hold_decision"), dict) else {}
    acceptance = str(decision.get(acceptance_key, "")).lower()
    if not acceptance and isinstance(payload.get("decision"), dict):
        acceptance = str(payload["decision"].get(acceptance_key, "")).lower()
    dependency_satisfied = row_complete and acceptance in {"accepted", "pass", "passed"}
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append(blocker_code)
    return {
        "tracker_id": tracker_id,
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def evaluate_row071_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW071_DELTA,
        tracker_id="TRK-W64-071",
        acceptance_key="row071_acceptance",
        blocker_code="ROW071_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW071_DELTA_ABSENT",
    )


def evaluate_row075_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW075_DELTA,
        tracker_id="TRK-W64-075",
        acceptance_key="row075_acceptance",
        blocker_code="ROW075_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW075_DELTA_ABSENT",
    )


def evaluate_row077_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW077_DELTA,
        tracker_id="TRK-W64-077",
        acceptance_key="row077_acceptance",
        blocker_code="ROW077_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW077_DELTA_ABSENT",
    )


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row078_fixture:{label}".encode("utf-8"))


def _observation(
    *,
    signal_family: str,
    identity: str,
    labels: dict[str, str],
    confidence: float,
    evidence_label: str,
) -> dict[str, Any]:
    return {
        "signal_family": signal_family,
        "pipeline_or_model_identity": identity,
        "labels": {field: labels[field] for field in REQUIRED_TAG_FIELDS},
        "confidence": confidence,
        "evidence_sha256": _stable_hash(f"evidence:{evidence_label}:{signal_family}"),
        "timestamp_utc": FIXTURE_TIMESTAMP,
    }


def _classify_value(value: str, allowed: set[str]) -> str:
    if value == UNKNOWN_SENTINEL:
        return "unknown"
    if value == OUT_OF_TAXONOMY_SENTINEL or value not in allowed:
        return "out_of_taxonomy"
    return "known"


def resolve_ensemble(
    observations: list[dict[str, Any]],
    registry: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    taxonomy = registry["taxonomy"]
    present_families = {obs["signal_family"] for obs in observations}
    missing = [family for family in REQUIRED_SIGNAL_FAMILIES if family not in present_families]

    structured_tags: dict[str, Any] = {}
    disagreements: list[dict[str, Any]] = []
    unknown_fields: list[str] = []
    out_of_taxonomy_fields: list[str] = []
    ambiguous_fields: list[str] = []

    for field in REQUIRED_TAG_FIELDS:
        allowed = set((taxonomy.get(field) or {}).get("allowed_values") or [])
        values_by_family: dict[str, str] = {}
        confidence_by_family: dict[str, float] = {}
        for obs in observations:
            family = obs["signal_family"]
            value = obs["labels"][field]
            values_by_family[family] = value
            confidence_by_family[family] = float(obs["confidence"])

        unique_values = sorted(set(values_by_family.values()))
        classifications = {_classify_value(value, allowed) for value in unique_values}

        if len(unique_values) > 1:
            disagreements.append(
                {
                    "field": field,
                    "values_by_signal_family": dict(sorted(values_by_family.items())),
                    "preserved": True,
                }
            )
            ambiguous_fields.append(field)
            classification = "ambiguous"
            resolved_value = "abstain"
        elif UNKNOWN_SENTINEL in unique_values or "unknown" in classifications:
            unknown_fields.append(field)
            classification = "unknown"
            resolved_value = UNKNOWN_SENTINEL
        elif "out_of_taxonomy" in classifications:
            out_of_taxonomy_fields.append(field)
            classification = "out_of_taxonomy"
            resolved_value = unique_values[0]
        else:
            classification = "known"
            resolved_value = unique_values[0]

        structured_tags[field] = {
            "value": resolved_value,
            "classification": classification,
            "supporting_signal_families": sorted(values_by_family.keys()),
            "per_source_confidence": {
                family: confidence_by_family[family] for family in sorted(confidence_by_family)
            },
        }

    accepted = sorted(present_families)
    abstention_reason: str | None = None
    status = "resolved"
    if missing:
        status = "blocked"
        abstention_reason = "missing_required_signal_families"
    elif disagreements or unknown_fields or out_of_taxonomy_fields or ambiguous_fields:
        status = "abstain"
        if disagreements:
            abstention_reason = "source_disagreement_preserved"
        elif unknown_fields:
            abstention_reason = "unknown_taxonomy_value"
        elif out_of_taxonomy_fields:
            abstention_reason = "out_of_taxonomy_value"
        else:
            abstention_reason = "ambiguous_field"

    resolution = {
        "status": status,
        "policy": "preserve_conflicts_and_fail_closed_on_unknown",
        "accepted_signal_families": accepted,
        "abstention_reason": abstention_reason,
        "conflict_preservation": True,
    }
    unknown_packet = {
        "unknown_fields": unknown_fields,
        "out_of_taxonomy_fields": out_of_taxonomy_fields,
        "ambiguous_fields": ambiguous_fields,
        "missing_signal_families": missing,
    }
    return structured_tags, disagreements, unknown_packet, resolution


def build_technical_caption(
    source_metadata: dict[str, str],
    structured_tags: dict[str, Any],
    *,
    caption_identity: str,
) -> dict[str, Any]:
    event = structured_tags["event_family"]["value"]
    material = structured_tags["material"]["value"]
    intensity = structured_tags["intensity_band"]["value"]
    attack = structured_tags["attack_characteristic"]["value"]
    room = structured_tags["room_environment"]["value"]
    text = (
        f"Advisory technical caption: {event} on {material}, "
        f"{intensity} intensity, {attack} attack, {room} room; "
        f"source event_type={source_metadata['event_type']} preserved."
    )
    return {
        "text": text,
        "authority": "advisory_derived_not_source_authority",
        "caption_identity": caption_identity,
        "entailed_source_fields": [
            "event_type",
            "material",
            "intensity_band",
            "attack_characteristic",
            "room_environment_suitability",
        ],
        "overwrites_source_metadata": False,
    }


def build_ensemble_record(
    root: Path,
    *,
    asset_id: str,
    source_sha256: str,
    source_metadata: dict[str, str],
    observations: list[dict[str, Any]],
    library_authority: bool = False,
    blocker_codes: list[str] | None = None,
    allow_caption_overwrite_attempt: bool = False,
) -> dict[str, Any]:
    registry = load_registry(root)
    required_meta = [
        "event_type",
        "material",
        "role",
        "intensity_band",
        "duration_band",
        "attack_characteristic",
        "sync_class",
        "room_environment_suitability",
    ]
    if set(source_metadata.keys()) != set(required_meta):
        raise AudioTagCaptionEnsembleError("source_metadata_fields_missing_or_extra")
    for key, value in source_metadata.items():
        if not isinstance(value, str) or not value.strip():
            raise AudioTagCaptionEnsembleError(f"empty_source_metadata:{key}")
        if value != value.strip():
            raise AudioTagCaptionEnsembleError(f"whitespace_source_metadata:{key}")

    snapshot = {key: source_metadata[key] for key in required_meta}
    snapshot_sha = canonical_json_sha256(snapshot)
    structured_tags, disagreements, unknown_packet, resolution = resolve_ensemble(
        observations, registry
    )
    caption = build_technical_caption(
        snapshot,
        structured_tags,
        caption_identity=f"{COMPILER_REVISION}:{asset_id}",
    )

    post_snapshot = dict(snapshot)
    if allow_caption_overwrite_attempt:
        # Explicit adversarial path: prove overwrite attempts are rejected.
        post_snapshot["material"] = "caption_overwrite_attempt"
        raise AudioTagCaptionEnsembleError("caption_overwrite_of_source_metadata_forbidden")

    post_sha = canonical_json_sha256(post_snapshot)
    if post_sha != snapshot_sha:
        raise AudioTagCaptionEnsembleError("source_metadata_mutated_after_caption")

    blockers = list(blocker_codes or [])
    if not library_authority and "LIBRARY_AUTHORITY_NOT_GRANTED" not in blockers:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")
    if unknown_packet["missing_signal_families"]:
        blockers.append("MISSING_REQUIRED_SIGNAL_FAMILIES")
    if disagreements:
        blockers.append("SOURCE_DISAGREEMENT_PRESERVED_ABSTAIN")
    if unknown_packet["unknown_fields"]:
        blockers.append("UNKNOWN_TAXONOMY_FAIL_CLOSED")
    if unknown_packet["out_of_taxonomy_fields"]:
        blockers.append("OUT_OF_TAXONOMY_FAIL_CLOSED")
    if resolution["status"] != "resolved":
        blockers.append("ENSEMBLE_NOT_RESOLVED")

    promotion_eligible = bool(
        library_authority
        and resolution["status"] == "resolved"
        and not disagreements
        and not unknown_packet["unknown_fields"]
        and not unknown_packet["out_of_taxonomy_fields"]
        and not unknown_packet["missing_signal_families"]
        and not blockers
    )
    status = "pass" if promotion_eligible else "blocked"

    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "taxonomy_revision": TAXONOMY_REVISION,
        "ensemble_policy_revision": ENSEMBLE_POLICY_REVISION,
        "asset_id": asset_id,
        "source_sha256": source_sha256,
        "source_metadata_snapshot_sha256": snapshot_sha,
        "source_metadata_snapshot": snapshot,
        "independent_source_observations": observations,
        "structured_tags": structured_tags,
        "technical_caption": caption,
        "source_disagreements": disagreements,
        "unknown_and_out_of_taxonomy": unknown_packet,
        "ensemble_resolution": resolution,
        "caption_non_overwrite_proof": {
            "source_metadata_snapshot_sha256": snapshot_sha,
            "post_caption_source_metadata_snapshot_sha256": post_sha,
            "source_bytes_unchanged": True,
            "caption_mutated_source_metadata": False,
        },
        "decision": {
            "status": status,
            "blocker_codes": blockers,
            "library_authority": bool(library_authority),
            "promotion_eligible": promotion_eligible,
            "advisory_only": True,
            "source_bytes_unchanged": True,
        },
    }


def validate_ensemble_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise AudioTagCaptionEnsembleError(
            f"schema_validation_failed:{location}:{first.message}"
        )
    proof = record["caption_non_overwrite_proof"]
    if (
        proof["source_metadata_snapshot_sha256"]
        != proof["post_caption_source_metadata_snapshot_sha256"]
    ):
        raise AudioTagCaptionEnsembleError("caption_non_overwrite_hash_mismatch")
    if proof["caption_mutated_source_metadata"] is not False:
        raise AudioTagCaptionEnsembleError("caption_mutated_source_metadata_not_false")
    if record["technical_caption"]["overwrites_source_metadata"] is not False:
        raise AudioTagCaptionEnsembleError("caption_overwrite_flag_not_false")
    recomputed = canonical_json_sha256(record["source_metadata_snapshot"])
    if recomputed != record["source_metadata_snapshot_sha256"]:
        raise AudioTagCaptionEnsembleError("source_metadata_snapshot_hash_mismatch")


def _base_metadata(**overrides: str) -> dict[str, str]:
    base = {
        "event_type": "footstep",
        "material": "hardwood",
        "role": "foley",
        "intensity_band": "medium",
        "duration_band": "short",
        "attack_characteristic": "transient",
        "sync_class": "hard_sync",
        "room_environment_suitability": "dry_close",
    }
    base.update(overrides)
    return base


def _four_family_observations(labels: dict[str, str], *, prefix: str) -> list[dict[str, Any]]:
    return [
        _observation(
            signal_family="path_and_source_metadata",
            identity="retained_index_metadata_v1",
            labels=labels,
            confidence=0.88,
            evidence_label=f"{prefix}:metadata",
        ),
        _observation(
            signal_family="deterministic_acoustic_features",
            identity="wave64_row071_acoustic_features_fixture_v0",
            labels=labels,
            confidence=0.81,
            evidence_label=f"{prefix}:acoustic",
        ),
        _observation(
            signal_family="semantic_embeddings",
            identity="wave64_row077_embedding_fixture_v0",
            labels=labels,
            confidence=0.79,
            evidence_label=f"{prefix}:embedding",
        ),
        _observation(
            signal_family="audio_tagging_models",
            identity="wave64_row078_tagger_fixture_v0",
            labels=labels,
            confidence=0.84,
            evidence_label=f"{prefix}:tagger",
        ),
    ]


FIXTURE_SPECS: dict[str, dict[str, Any]] = {
    "agreement_four_families": {
        "metadata": _base_metadata(),
        "labels": {
            "event_family": "footstep",
            "material": "hardwood",
            "intensity_band": "medium",
            "attack_characteristic": "transient",
            "room_environment": "dry_close",
        },
        "build": "agreement",
    },
    "disagreement_material_preserved": {
        "metadata": _base_metadata(material="hardwood"),
        "labels": {
            "event_family": "footstep",
            "material": "hardwood",
            "intensity_band": "medium",
            "attack_characteristic": "transient",
            "room_environment": "dry_close",
        },
        "build": "disagreement_material",
    },
    "unknown_intensity_fail_closed": {
        "metadata": _base_metadata(intensity_band="unknown"),
        "labels": {
            "event_family": "impact",
            "material": "metal",
            "intensity_band": "unknown",
            "attack_characteristic": "transient",
            "room_environment": "medium_room",
        },
        "build": "agreement",
    },
    "out_of_taxonomy_event_fail_closed": {
        "metadata": _base_metadata(event_type="footstep"),
        "labels": {
            "event_family": "laser_blaster",
            "material": "metal",
            "intensity_band": "hard",
            "attack_characteristic": "transient",
            "room_environment": "dry_close",
        },
        "build": "agreement",
    },
    "missing_embedding_family_blocked": {
        "metadata": _base_metadata(),
        "labels": {
            "event_family": "cloth",
            "material": "fabric",
            "intensity_band": "soft",
            "attack_characteristic": "sustained",
            "room_environment": "small_room",
        },
        "build": "missing_embedding",
    },
}


def _build_fixture_observations(spec: dict[str, Any], fixture_name: str) -> list[dict[str, Any]]:
    labels = dict(spec["labels"])
    build = spec["build"]
    if build == "agreement":
        return _four_family_observations(labels, prefix=fixture_name)
    if build == "disagreement_material":
        observations = _four_family_observations(labels, prefix=fixture_name)
        for obs in observations:
            if obs["signal_family"] == "audio_tagging_models":
                obs["labels"]["material"] = "concrete"
            if obs["signal_family"] == "semantic_embeddings":
                obs["labels"]["material"] = "tile"
        return observations
    if build == "missing_embedding":
        return [
            obs
            for obs in _four_family_observations(labels, prefix=fixture_name)
            if obs["signal_family"] != "semantic_embeddings"
        ]
    raise AudioTagCaptionEnsembleError(f"unknown_fixture_build:{build}")


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    if fixture_name not in FIXTURE_SPECS:
        raise AudioTagCaptionEnsembleError(f"unknown_fixture:{fixture_name}")
    spec = FIXTURE_SPECS[fixture_name]
    observations = _build_fixture_observations(spec, fixture_name)
    record = build_ensemble_record(
        root,
        asset_id=f"fixture:{fixture_name}",
        source_sha256=_stable_hash(f"source:{fixture_name}"),
        source_metadata=dict(spec["metadata"]),
        observations=observations,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    validate_ensemble_record(root, record)
    return record


def assert_caption_non_overwrite(root: Path, record: dict[str, Any]) -> None:
    validate_ensemble_record(root, record)
    if record["technical_caption"]["authority"] != "advisory_derived_not_source_authority":
        raise AudioTagCaptionEnsembleError("caption_authority_not_advisory")
    if record["decision"]["advisory_only"] is not True:
        raise AudioTagCaptionEnsembleError("decision_not_advisory_only")


def assert_promotion_fail_closed(root: Path, record: dict[str, Any]) -> list[str]:
    validate_ensemble_record(root, record)
    blockers: list[str] = []
    if record["decision"]["library_authority"] is not True:
        blockers.append("LIBRARY_AUTHORITY_NOT_GRANTED")
    if record["ensemble_resolution"]["status"] != "resolved":
        blockers.append("ENSEMBLE_NOT_RESOLVED")
    if record["source_disagreements"]:
        blockers.append("SOURCE_DISAGREEMENT_PRESERVED_ABSTAIN")
    if record["unknown_and_out_of_taxonomy"]["unknown_fields"]:
        blockers.append("UNKNOWN_TAXONOMY_FAIL_CLOSED")
    if record["unknown_and_out_of_taxonomy"]["out_of_taxonomy_fields"]:
        blockers.append("OUT_OF_TAXONOMY_FAIL_CLOSED")
    if record["unknown_and_out_of_taxonomy"]["missing_signal_families"]:
        blockers.append("MISSING_REQUIRED_SIGNAL_FAMILIES")
    if record["decision"]["promotion_eligible"] and blockers:
        raise AudioTagCaptionEnsembleError("promotion_eligible_despite_blockers")
    return sorted(set(blockers))


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row071 = evaluate_row071_admission(root)
    row075 = evaluate_row075_admission(root)
    row077 = evaluate_row077_admission(root)
    blocker_codes: list[str] = []
    for admission in (row071, row075, row077):
        blocker_codes.extend(admission["blocker_codes"])
    if not (
        row071["dependency_satisfied"]
        and row075["dependency_satisfied"]
        and row077["dependency_satisfied"]
    ):
        if "ROW071_ROW075_ROW077_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
            blocker_codes.append("ROW071_ROW075_ROW077_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_FULL_LIBRARY_ENSEMBLE_RUNTIME_ABSENT",
        "TAGGING_AND_CAPTION_MODEL_STACK_UNBOUND",
        "HELD_OUT_ENSEMBLE_METRICS_ABSENT",
        "FULL_LIBRARY_RECONCILIATION_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_names = list(FIXTURE_SPECS.keys())
    fixture_records = [extract_fixture_record(root, name) for name in fixture_names]
    registry = load_registry(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-078_audio_tag_caption_ensemble",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "taxonomy_revision": TAXONOMY_REVISION,
        "ensemble_policy_revision": ENSEMBLE_POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW071_ROW075_ROW077_DEPENDENCIES_AND_FULL_LIBRARY_ENSEMBLE_RUNTIME_ABSENT",
        "required_signal_families": list(REQUIRED_SIGNAL_FAMILIES),
        "required_tag_fields": list(REQUIRED_TAG_FIELDS),
        "row071_admission": row071,
        "row075_admission": row075,
        "row077_admission": row077,
        "ensemble_registry": {
            "path": str(REGISTRY_PATH).replace("\\", "/"),
            "taxonomy_revision": registry["taxonomy_revision"],
            "ensemble_policy_revision": registry["ensemble_policy_revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, REGISTRY_PATH, "registry")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove four-family attribution, conflict preservation, "
                "unknown/out-of-taxonomy fail-closed abstention, missing-family blocking, "
                "and caption non-overwrite; they do not accept Row078 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row078_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row071 deterministic acoustic features, Row075 attributable "
                "defect/quality observations, and Row077 embedding identity/index proof; "
                "bind license-qualified tagging and caption mechanisms; reconcile every "
                "retained library asset through this frozen ensemble policy with preserved "
                "conflicts and explicit unknowns; then replace this hold packet with "
                "full-library ensemble evidence and held-out metrics."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("library", "fixture"), default="library")
    parser.add_argument("--fixture", default="agreement_four_families")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise AudioTagCaptionEnsembleError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise AudioTagCaptionEnsembleError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload.get("row_complete") is True:
            raise AudioTagCaptionEnsembleError("library_mode_must_not_claim_row_complete")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
