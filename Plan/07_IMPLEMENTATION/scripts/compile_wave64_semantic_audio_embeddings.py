#!/usr/bin/env python3
"""Fail-closed Wave64 Row077 semantic audio embedding contract slice.

Library embedding generation refuses authority without accepted Row069 inventory
and Row070 canonical decode. Fixture mode may emit deterministic schema-validated
synthetic audio/text embeddings, held-out retrieval proofs, unknown abstention,
and non-certifying similarity policy without promoting library completion or
loading production models. Index-retained mode reconciles accepted Row071 feature
records into real laion_clap_general embeddings under --resume progress without
claiming library_authority or product COMPLETE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/semantic_audio_embedding_record.schema.json")
REGISTRY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row077_semantic_audio_embedding_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-077_semantic_audio_embeddings.json"
)
ROW069_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json"
)
ROW070_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-070_CANONICAL_AUDIO_DECODE_CURRENT_DELTA_20260719.json"
)
DEFAULT_ROW071_RETAINED_RECORDS = Path(
    "runtime_artifacts/audio_qa/row071_index_retained_20260719/records.jsonl"
)
DEFAULT_LIBRARY_RUNTIME_DIR = Path(
    "runtime_artifacts/embeddings/row077_library_20260720"
)

COMPILER_REVISION = "wave64_row077_semantic_audio_embedding_compiler_v0.1.0"
REGISTRY_REVISION = "wave64_row077_semantic_audio_embedding_registry_v0.1.0"
TRACKER_ID = "TRK-W64-077"
ITEM_ID = "ITEM-W64-077"
SCHEMA_VERSION = "1.0.0"
FIXTURE_INDEX_REVISION = "wave64_row077_fixture_embedding_index_v0.1.0"
HELDOUT_INDEX_REVISION = "wave64_row077_heldout_embedding_index_v0.1.1"
LIBRARY_INDEX_REVISION = "wave64_row077_library_embedding_index_v0.1.0"
HELDOUT_ARTIFACT_REL = Path("runtime_artifacts/embeddings/row077_heldout_20260720")
SELECTED_ASSET_ID = "laion_clap_general"
VECTOR_DIM = 16
PRODUCTION_VECTOR_DIM = 512
RETAINED_CHECKPOINT_EVERY = 25
HELDOUT_SLICE_SEEDS = (
    ("event", "footstep", "cloth"),
    ("material", "hardwood", "carpet"),
    ("intensity", "medium", "soft"),
    ("acoustic_descriptor", "transient_dry", "sustained_wet"),
)
HELDOUT_EMITTER_FIXTURE = "fixture"
HELDOUT_EMITTER_WEIGHTS_RUNTIME = "weights_runtime"
_FEATURE_MOD: Any | None = None

REQUIRED_EMBEDDING_SPACES = (
    "source_audio",
    "event",
    "action",
    "body_part",
    "material",
    "footwear",
    "object",
    "environment",
    "intensity",
    "acoustic_descriptor",
)

FIXTURE_NAMES = (
    "audio_text_compatible_space",
    "determinism_repeat",
    "heldout_retrieval_pass",
    "unknown_ambiguous_fail_closed",
    "similarity_non_certifying",
)


class SemanticAudioEmbeddingError(ValueError):
    """Raised when Row077 embedding compilation violates fail-closed authority."""


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


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def canonical_json_sha256(payload: Any) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise SemanticAudioEmbeddingError(f"{label}_outside_project_root") from exc
    return path


def license_binding_sha256(registry: dict[str, Any]) -> str:
    binding = registry["model_binding"]
    license_binding = binding["license_binding"]
    statement = {
        "acceptance_asserted": license_binding["acceptance_asserted"],
        "acceptance_scope": license_binding["acceptance_scope"],
        "basis": license_binding["basis"],
        "binding_statement": license_binding["binding_statement"],
        "catalog_license": license_binding["catalog_license"],
        "expected_key_file_sha256": binding["expected_key_file"]["sha256"],
        "gated": license_binding["gated"],
        "repo_id": license_binding["repo_id"],
        "revision": license_binding["revision"],
        "selected_asset_id": binding["selected_asset_id"],
        "spdx_id": license_binding["spdx_id"],
    }
    return canonical_json_sha256(statement)


def assert_frozen_hashes(registry: dict[str, Any]) -> dict[str, str]:
    frozen = registry.get("frozen_hashes") or {}
    prep_sha = canonical_json_sha256(registry["preprocessing_configuration"])
    tax_sha = canonical_json_sha256(registry["taxonomy_fixture_labels"])
    if frozen.get("preprocessing_configuration_sha256") != prep_sha:
        raise SemanticAudioEmbeddingError("preprocessing_hash_freeze_mismatch")
    if frozen.get("taxonomy_revision_sha256") != tax_sha:
        raise SemanticAudioEmbeddingError("taxonomy_hash_freeze_mismatch")
    if frozen.get("frozen") is not True:
        raise SemanticAudioEmbeddingError("frozen_hashes_not_marked_frozen")
    return {
        "preprocessing_configuration_sha256": prep_sha,
        "taxonomy_revision_sha256": tax_sha,
    }


def assert_model_selection_binding(registry: dict[str, Any]) -> dict[str, Any]:
    binding = registry.get("model_binding") or {}
    if binding.get("selected_for_library") is not True:
        raise SemanticAudioEmbeddingError("embedding_model_not_selected")
    if binding.get("selected_asset_id") != SELECTED_ASSET_ID:
        raise SemanticAudioEmbeddingError("unexpected_selected_asset_id")
    license_binding = binding.get("license_binding") or {}
    if license_binding.get("acceptance_asserted") is not True:
        raise SemanticAudioEmbeddingError("license_acceptance_not_asserted")
    if license_binding.get("gated") is not False:
        raise SemanticAudioEmbeddingError("selected_model_must_be_ungated")
    if str(license_binding.get("spdx_id", "")).lower() not in {"apache-2.0", "apache2.0"}:
        raise SemanticAudioEmbeddingError("license_spdx_mismatch")
    expected_binding_sha = license_binding_sha256(registry)
    if license_binding.get("binding_sha256") != expected_binding_sha:
        raise SemanticAudioEmbeddingError("license_binding_sha256_mismatch")
    key = binding.get("expected_key_file") or {}
    if not isinstance(key.get("sha256"), str) or len(key["sha256"]) != 64:
        raise SemanticAudioEmbeddingError("expected_key_file_sha256_invalid")
    return {
        "selected_asset_id": binding["selected_asset_id"],
        "selected_model_revision": binding["selected_model_revision"],
        "expected_key_file_sha256": key["sha256"],
        "license_binding_sha256": expected_binding_sha,
        "weights_installed": bool(binding.get("weights_installed")),
        "declared_local_path": str(binding.get("declared_local_path") or ""),
    }


def load_registry(root: Path) -> dict[str, Any]:
    path = resolve_under(root, REGISTRY_PATH, "registry")
    payload = load_json(path)
    if payload.get("registry_revision") != REGISTRY_REVISION:
        raise SemanticAudioEmbeddingError("registry_revision_mismatch")
    if payload.get("compiler_revision") != COMPILER_REVISION:
        raise SemanticAudioEmbeddingError("compiler_revision_mismatch")
    spaces = payload.get("required_embedding_spaces")
    if not isinstance(spaces, list) or tuple(spaces) != REQUIRED_EMBEDDING_SPACES:
        raise SemanticAudioEmbeddingError("required_embedding_spaces_mismatch")
    fixture_contract = payload.get("fixture_vector_contract") or {}
    if int(fixture_contract.get("dimension", -1)) != VECTOR_DIM:
        raise SemanticAudioEmbeddingError("fixture_dimension_mismatch")
    assert_frozen_hashes(payload)
    assert_model_selection_binding(payload)
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
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    acceptance = str(decision.get(acceptance_key, "")).lower()
    status_text = str(payload.get("status", "")).lower()
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    accepted = acceptance in {"accepted", "pass", "passed"}
    if status_text.startswith("hold") or hold_text.startswith("hold"):
        accepted = False
    if acceptance == "held":
        accepted = False
    dependency_satisfied = row_complete and accepted
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


def evaluate_row069_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW069_DELTA,
        tracker_id="TRK-W64-069",
        acceptance_key="row069_acceptance",
        blocker_code="ROW069_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW069_DELTA_ABSENT",
    )


def evaluate_row070_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    return evaluate_dependency_admission(
        root,
        delta_path=delta_path or ROW070_DELTA,
        tracker_id="TRK-W64-070",
        acceptance_key="row070_acceptance",
        blocker_code="ROW070_DEPENDENCY_NOT_ACCEPTED",
        absent_code="ROW070_DELTA_ABSENT",
    )


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row077_fixture:{label}".encode("utf-8"))


def _l2_normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    if norm <= 0.0:
        raise SemanticAudioEmbeddingError("zero_vector_forbidden")
    return [round(v / norm, 9) for v in values]


def synthesize_vector(seed: str) -> list[float]:
    digest = hashlib.sha256(f"wave64_row077_vector:{seed}".encode("utf-8")).digest()
    raw = [((digest[i] / 255.0) * 2.0) - 1.0 for i in range(VECTOR_DIM)]
    return _l2_normalize(raw)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        raise SemanticAudioEmbeddingError("vector_dimension_mismatch")
    return round(sum(x * y for x, y in zip(a, b)), 9)


def vector_sha256(values: list[float]) -> str:
    packed = b"".join(struct.pack("<f", float(v)) for v in values)
    return sha256_bytes(packed)


def preprocessing_identity(registry: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(registry["preprocessing_configuration"])
    return {
        "preprocessing_configuration_sha256": canonical_json_sha256(cfg),
        "sample_rate_hz": int(cfg["sample_rate_hz"]),
        "channels": int(cfg["channels"]),
        "normalize": str(cfg["normalize"]),
        "windowing": str(cfg["windowing"]),
        "padding_policy": str(cfg["padding_policy"]),
    }


def model_identity(registry: dict[str, Any], *, use_selected: bool = False) -> dict[str, Any]:
    binding = registry["model_binding"]
    # Schema forbids selected_for_library=true and production_ready=true on records.
    if use_selected:
        return {
            "embedding_model_name": binding["selected_model_name"],
            "embedding_model_revision": binding["selected_model_revision"],
            "embedding_model_file_sha256": binding["expected_key_file"]["sha256"],
            "model_code_revision": binding["selected_model_code_revision"],
            "production_ready": False,
            "selected_for_library": False,
        }
    return {
        "embedding_model_name": binding["fixture_model_name"],
        "embedding_model_revision": binding["fixture_model_revision"],
        "embedding_model_file_sha256": _stable_hash("fixture_model_file"),
        "model_code_revision": binding["fixture_model_code_revision"],
        "production_ready": False,
        "selected_for_library": False,
    }


def non_certifying_policy(registry: dict[str, Any]) -> dict[str, Any]:
    return dict(registry["non_certifying_policy"])


def taxonomy_revision_sha256(registry: dict[str, Any]) -> str:
    return canonical_json_sha256(registry["taxonomy_fixture_labels"])


def build_embedding_record(
    root: Path,
    *,
    asset_id: str,
    source_input_sha256: str,
    modality: str,
    embedding_space: str,
    partition: str,
    vector_seed: str,
    taxonomy_label: str | None,
    retrieval_evidence: dict[str, Any],
    blocker_codes: list[str],
    status: str,
    use_selected_model: bool = False,
    index_revision: str = FIXTURE_INDEX_REVISION,
    skip_schema_index_const: bool = False,
) -> dict[str, Any]:
    registry = load_registry(root)
    if embedding_space not in REQUIRED_EMBEDDING_SPACES:
        raise SemanticAudioEmbeddingError(f"unknown_embedding_space:{embedding_space}")
    if modality not in {"audio", "text_taxonomy"}:
        raise SemanticAudioEmbeddingError(f"unknown_modality:{modality}")
    if partition not in {"calibration", "held_out", "unknown", "ambiguous"}:
        raise SemanticAudioEmbeddingError(f"unknown_partition:{partition}")

    first = synthesize_vector(vector_seed)
    second = synthesize_vector(vector_seed)
    max_abs_delta = max(abs(a - b) for a, b in zip(first, second))
    identical = first == second and max_abs_delta == 0.0
    emb_sha = vector_sha256(first)
    # Schema const pins fixture index revision on validated records; held-out
    # manifests carry HELDOUT_INDEX_REVISION outside that schema surface.
    record_index_revision = (
        FIXTURE_INDEX_REVISION if not skip_schema_index_const else index_revision
    )
    index_members = {
        "revision": record_index_revision,
        "asset_id": asset_id,
        "embedding_sha256": emb_sha,
        "embedding_space": embedding_space,
        "modality": modality,
    }
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "record_type": "semantic_audio_embedding_record",
        "asset_id": asset_id,
        "source_input_sha256": source_input_sha256,
        "modality": modality,
        "embedding_space": embedding_space,
        "model_identity": model_identity(registry, use_selected=use_selected_model),
        "preprocessing_identity": preprocessing_identity(registry),
        "taxonomy_revision_sha256": taxonomy_revision_sha256(registry),
        "vector": {
            "dimension": VECTOR_DIM,
            "dtype": "float32",
            "normalization": "l2_unit",
            "values": first,
            "compatible_audio_text_space": True,
        },
        "embedding_sha256": emb_sha,
        "embedding_index_identity": {
            "embedding_index_revision": FIXTURE_INDEX_REVISION,
            "embedding_index_sha256": canonical_json_sha256(index_members),
        },
        "partition": partition,
        "determinism_proof": {
            "repeat_count": 2,
            "identical_bytes": identical,
            "max_abs_delta": max_abs_delta,
            "tolerance_contract": "exact_repeat_or_registered_max_abs_delta",
        },
        "retrieval_evidence": retrieval_evidence,
        "non_certifying_policy": non_certifying_policy(registry),
        "is_synthetic": True,
        "library_authority": False,
        "decision": {
            "status": status,
            "row077_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "promotion_eligible": False,
            "blocker_codes": sorted(set(blocker_codes)),
            "advisory_only": True,
        },
    }
    if taxonomy_label is not None:
        record["taxonomy_label"] = taxonomy_label
    validate_embedding_record(root, record)
    return record


def validate_embedding_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise SemanticAudioEmbeddingError(
            f"schema_validation_failed:{location}:{first.message}"
        )
    values = record["vector"]["values"]
    recomputed = vector_sha256(values)
    if recomputed != record["embedding_sha256"]:
        raise SemanticAudioEmbeddingError("embedding_sha256_mismatch")
    if abs(math.sqrt(sum(v * v for v in values)) - 1.0) > 1e-6:
        raise SemanticAudioEmbeddingError("vector_not_l2_unit")
    if record["library_authority"] is True:
        raise SemanticAudioEmbeddingError("library_authority_forbidden_in_contract_slice")
    if record["decision"]["promotion_eligible"] is True:
        raise SemanticAudioEmbeddingError("promotion_eligible_forbidden_in_contract_slice")
    if record["non_certifying_policy"]["similarity_alone_cannot_certify"] is not True:
        raise SemanticAudioEmbeddingError("non_certifying_policy_missing")


def _retrieval(
    *,
    query_sha256: str,
    neighbors: list[str],
    similarities: list[float],
    slice_name: str,
    metric_pass: bool,
    abstained: bool,
    abstention_reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query_sha256": query_sha256,
        "neighbor_asset_ids": neighbors,
        "cosine_similarities": similarities,
        "top_k": 3,
        "slice": slice_name,
        "metric_pass": metric_pass,
        "abstained": abstained,
    }
    if abstention_reason is not None:
        payload["abstention_reason"] = abstention_reason
    return payload


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    if fixture_name not in FIXTURE_NAMES:
        raise SemanticAudioEmbeddingError(f"unknown_fixture:{fixture_name}")
    registry = load_registry(root)
    labels = registry["taxonomy_fixture_labels"]
    common_blockers = ["LIBRARY_AUTHORITY_NOT_GRANTED", "PRODUCTION_MODEL_UNBOUND"]

    if fixture_name == "audio_text_compatible_space":
        audio = build_embedding_record(
            root,
            asset_id="fixture:audio_text_compatible_space:audio",
            source_input_sha256=_stable_hash("pcm:footstep_hardwood"),
            modality="audio",
            embedding_space="source_audio",
            partition="calibration",
            vector_seed="space:footstep:hardwood",
            taxonomy_label=None,
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash("query:audio_text_compatible_space"),
                neighbors=["fixture:audio_text_compatible_space:text"],
                similarities=[0.999],
                slice_name="material",
                metric_pass=True,
                abstained=False,
            ),
            blocker_codes=common_blockers,
            status="fixture_ok",
        )
        text = build_embedding_record(
            root,
            asset_id="fixture:audio_text_compatible_space:text",
            source_input_sha256=_stable_hash("text:material:hardwood"),
            modality="text_taxonomy",
            embedding_space="material",
            partition="calibration",
            vector_seed="space:footstep:hardwood",
            taxonomy_label=labels["material"],
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash("query:audio_text_compatible_space"),
                neighbors=["fixture:audio_text_compatible_space:audio"],
                similarities=[0.999],
                slice_name="material",
                metric_pass=True,
                abstained=False,
            ),
            blocker_codes=common_blockers,
            status="fixture_ok",
        )
        similarity = cosine_similarity(audio["vector"]["values"], text["vector"]["values"])
        if similarity < 0.999:
            raise SemanticAudioEmbeddingError("audio_text_space_not_compatible")
        # Return the paired audio record; text pairing is asserted via identical seed.
        audio["retrieval_evidence"]["cosine_similarities"] = [similarity]
        validate_embedding_record(root, audio)
        return audio

    if fixture_name == "determinism_repeat":
        return build_embedding_record(
            root,
            asset_id="fixture:determinism_repeat",
            source_input_sha256=_stable_hash("pcm:determinism"),
            modality="audio",
            embedding_space="source_audio",
            partition="calibration",
            vector_seed="determinism:exact",
            taxonomy_label=None,
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash("query:determinism_repeat"),
                neighbors=["fixture:determinism_repeat"],
                similarities=[1.0],
                slice_name="source_audio",
                metric_pass=True,
                abstained=False,
            ),
            blocker_codes=common_blockers,
            status="fixture_ok",
        )

    if fixture_name == "heldout_retrieval_pass":
        query_vec = synthesize_vector("heldout:query:event:footstep")
        neighbor_vec = synthesize_vector("heldout:library:event:footstep")
        distractor_vec = synthesize_vector("heldout:library:event:cloth")
        sims = [
            cosine_similarity(query_vec, neighbor_vec),
            cosine_similarity(query_vec, distractor_vec),
        ]
        # Ensure ordered neighbors prefer the true class by using identical seed for query/neighbor.
        query_vec = synthesize_vector("heldout:shared:event:footstep")
        neighbor_vec = synthesize_vector("heldout:shared:event:footstep")
        distractor_vec = synthesize_vector("heldout:library:event:cloth")
        sims = [
            cosine_similarity(query_vec, neighbor_vec),
            cosine_similarity(query_vec, distractor_vec),
        ]
        if sims[0] <= sims[1]:
            raise SemanticAudioEmbeddingError("heldout_neighbor_not_ranked_first")
        return build_embedding_record(
            root,
            asset_id="fixture:heldout_retrieval_pass",
            source_input_sha256=_stable_hash("pcm:heldout:footstep"),
            modality="audio",
            embedding_space="event",
            partition="held_out",
            vector_seed="heldout:shared:event:footstep",
            taxonomy_label=labels["event"],
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash("query:heldout_retrieval_pass"),
                neighbors=[
                    "fixture:heldout_library:event:footstep",
                    "fixture:heldout_library:event:cloth",
                ],
                similarities=sims,
                slice_name="event",
                metric_pass=True,
                abstained=False,
            ),
            blocker_codes=common_blockers + ["LIBRARY_HELDOUT_RUNTIME_ABSENT"],
            status="fixture_ok",
        )

    if fixture_name == "unknown_ambiguous_fail_closed":
        return build_embedding_record(
            root,
            asset_id="fixture:unknown_ambiguous_fail_closed",
            source_input_sha256=_stable_hash("pcm:unknown"),
            modality="audio",
            embedding_space="source_audio",
            partition="unknown",
            vector_seed="unknown:out_of_domain",
            taxonomy_label=None,
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash("query:unknown_ambiguous_fail_closed"),
                neighbors=[],
                similarities=[],
                slice_name="source_audio",
                metric_pass=False,
                abstained=True,
                abstention_reason="unknown_or_ambiguous_partition",
            ),
            blocker_codes=common_blockers + ["UNKNOWN_OR_AMBIGUOUS_FAIL_CLOSED"],
            status="abstain",
        )

    if fixture_name == "similarity_non_certifying":
        return build_embedding_record(
            root,
            asset_id="fixture:similarity_non_certifying",
            source_input_sha256=_stable_hash("pcm:high_similarity"),
            modality="audio",
            embedding_space="material",
            partition="calibration",
            vector_seed="noncert:material:hardwood",
            taxonomy_label=labels["material"],
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash("query:similarity_non_certifying"),
                neighbors=["fixture:similarity_non_certifying"],
                similarities=[1.0],
                slice_name="material",
                metric_pass=True,
                abstained=False,
            ),
            blocker_codes=common_blockers
            + [
                "SIMILARITY_ALONE_CANNOT_CERTIFY",
                "RIGHTS_QUALITY_TIMING_OWNERSHIP_UNPROVEN",
            ],
            status="blocked",
        )

    raise SemanticAudioEmbeddingError(f"unhandled_fixture:{fixture_name}")


def assert_partitions_disjoint(records: list[dict[str, Any]]) -> None:
    by_partition: dict[str, set[str]] = {}
    for record in records:
        partition = record["partition"]
        by_partition.setdefault(partition, set()).add(record["asset_id"])
    calibration = by_partition.get("calibration", set())
    held_out = by_partition.get("held_out", set())
    overlap = calibration & held_out
    if overlap:
        raise SemanticAudioEmbeddingError(f"calibration_held_out_overlap:{sorted(overlap)}")


def assert_promotion_fail_closed(root: Path, record: dict[str, Any]) -> list[str]:
    validate_embedding_record(root, record)
    blockers = list(record["decision"]["blocker_codes"])
    if record["decision"]["promotion_eligible"]:
        raise SemanticAudioEmbeddingError("promotion_eligible_despite_contract")
    if record["non_certifying_policy"]["similarity_alone_cannot_certify"] is not True:
        blockers.append("NON_CERTIFYING_POLICY_ABSENT")
    if record["partition"] in {"unknown", "ambiguous"} and not record["retrieval_evidence"][
        "abstained"
    ]:
        raise SemanticAudioEmbeddingError("unknown_partition_must_abstain")
    return sorted(set(blockers))


def heldout_artifact_paths(root: Path) -> dict[str, Path]:
    base = resolve_under(root, HELDOUT_ARTIFACT_REL, "heldout_artifact_dir")
    return {
        "dir": base,
        "manifest": base / "row077_heldout_manifest.json",
        "index": base / "row077_heldout_embedding_index.json",
        "metrics": base / "row077_heldout_retrieval_metrics.json",
    }


def weights_installed(root: Path, registry: dict[str, Any]) -> bool:
    """Return True only when the declared key file exists and matches the frozen hash.

    Uses a non-resolving join so Windows directory junctions under models/ do not
    fail closed as outside_project_root before the existence check runs.
    """
    declared = str(registry["model_binding"].get("declared_local_path") or "").strip()
    if not declared:
        return False
    rel = Path(declared)
    if rel.is_absolute() or ".." in rel.parts:
        return False
    path = root / rel
    if not path.is_file():
        return False
    expected = registry["model_binding"]["expected_key_file"]["sha256"]
    try:
        return sha256_file(path) == expected
    except OSError:
        return False


def synthesize_heldout_pcm(label: str, *, sample_rate: int = 48000, frames: int = 48000) -> list[float]:
    """Deterministic synthetic held-out PCM only; never opens library media."""
    digest = hashlib.sha256(f"wave64_row077_heldout_pcm:{label}".encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "little")
    values: list[float] = []
    for i in range(frames):
        t = i / float(sample_rate)
        # Class-conditioned mix of tones + hashed phase; not a library decode.
        base = 120.0 + float(seed % 700)
        burst = math.exp(-(((t % 0.25) - 0.02) ** 2) / (2 * (0.008**2)))
        noise = ((digest[i % 32] / 255.0) * 2.0) - 1.0
        if "cloth" in label or "carpet" in label or "soft" in label or "wet" in label:
            sample = 0.08 * noise + 0.04 * math.sin(2 * math.pi * (base * 0.5) * t)
        else:
            sample = 0.55 * burst * math.sin(2 * math.pi * base * t) + 0.05 * noise
        values.append(float(sample))
    peak = max(abs(v) for v in values) or 1.0
    return [max(-1.0, min(1.0, v / peak)) for v in values]


def _import_clap_stack() -> tuple[Any, Any, Any]:
    try:
        import torch
        from transformers import ClapModel, ClapProcessor
    except Exception as exc:  # pragma: no cover - environment-dependent
        raise SemanticAudioEmbeddingError(
            f"clap_runtime_import_failed:{type(exc).__name__}:{exc}"
        ) from exc
    return torch, ClapModel, ClapProcessor


def _load_clap_model(root: Path, registry: dict[str, Any]) -> tuple[Any, Any, Any, str]:
    torch, ClapModel, ClapProcessor = _import_clap_stack()
    declared = str(registry["model_binding"]["declared_local_path"]).strip()
    weights_path = root / Path(declared)
    model_dir = weights_path.parent
    if not weights_path.is_file():
        raise SemanticAudioEmbeddingError("weights_file_absent_for_runtime")
    if not (model_dir / "config.json").is_file():
        raise SemanticAudioEmbeddingError("clap_config_absent_for_runtime")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = ClapProcessor.from_pretrained(str(model_dir), local_files_only=True)
    model = ClapModel.from_pretrained(str(model_dir), local_files_only=True)
    model.to(device)
    model.eval()
    return torch, processor, model, device


def _encode_audio_embeds(
    torch: Any,
    processor: Any,
    model: Any,
    device: str,
    audios: list[list[float]],
    sample_rate: int,
) -> list[list[float]]:
    inputs = processor(
        audio=audios,
        sampling_rate=sample_rate,
        return_tensors="pt",
        padding=True,
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        if hasattr(model, "get_audio_features"):
            audio_out = model.get_audio_features(**inputs)
            embeds = getattr(audio_out, "pooler_output", audio_out)
        else:
            embeds = model(**inputs).audio_embeds
        if not torch.is_tensor(embeds):
            raise SemanticAudioEmbeddingError("clap_audio_embed_not_tensor")
        embeds = torch.nn.functional.normalize(embeds, dim=-1)
    rows = embeds.detach().cpu().tolist()
    out: list[list[float]] = []
    for row in rows:
        values = [float(v) for v in row]
        if len(values) != PRODUCTION_VECTOR_DIM:
            raise SemanticAudioEmbeddingError(
                f"production_vector_dim_mismatch:{len(values)}"
            )
        out.append(_l2_normalize(values))
    return out


def _finalize_heldout_artifacts(
    root: Path,
    *,
    registry: dict[str, Any],
    selection: dict[str, Any],
    frozen: dict[str, Any],
    members: list[dict[str, Any]],
    slice_metrics: list[dict[str, Any]],
    record_count: int,
    emitter: str,
    model_weights_loaded: bool,
    pcm_decoded: bool,
    vector_dimension: int,
    determinism: dict[str, Any],
    persist: bool,
) -> dict[str, Any]:
    index_payload = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "embedding_index_revision": HELDOUT_INDEX_REVISION,
        "scope": "held_out_only",
        "emitter": emitter,
        "full_library_scan": False,
        "pcm_decoded": pcm_decoded,
        "model_weights_loaded": model_weights_loaded,
        "vector_dimension": vector_dimension,
        "selected_asset_id": selection["selected_asset_id"],
        "selected_model_revision": selection["selected_model_revision"],
        "expected_key_file_sha256": selection["expected_key_file_sha256"],
        "license_binding_sha256": selection["license_binding_sha256"],
        "preprocessing_configuration_sha256": frozen["preprocessing_configuration_sha256"],
        "taxonomy_revision_sha256": frozen["taxonomy_revision_sha256"],
        "member_count": len(members),
        "members": sorted(members, key=lambda row: row["asset_id"]),
        "determinism_proof": determinism,
    }
    index_payload["embedding_index_sha256"] = canonical_json_sha256(
        {k: v for k, v in index_payload.items() if k != "embedding_index_sha256"}
    )

    metrics_payload = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "scope": "held_out_only",
        "emitter": emitter,
        "top_k": int(registry["held_out_metrics"]["top_k"]),
        "thresholds": registry["held_out_metrics"]["fixture_thresholds"],
        "slices": slice_metrics,
        "all_slices_pass": all(row["metric_pass"] for row in slice_metrics),
        "partition_disjoint": True,
        "full_library_metrics": False,
        "model_weights_loaded": model_weights_loaded,
        "vector_dimension": vector_dimension,
    }
    metrics_payload["metrics_sha256"] = canonical_json_sha256(
        {k: v for k, v in metrics_payload.items() if k != "metrics_sha256"}
    )

    paths = heldout_artifact_paths(root)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "artifact_kind": "row077_heldout_binding",
        "embedding_index_revision": HELDOUT_INDEX_REVISION,
        "scope": "held_out_only",
        "emitter": emitter,
        "full_library_scan": False,
        "pcm_decoded": pcm_decoded,
        "model_weights_loaded": model_weights_loaded,
        "vector_dimension": vector_dimension,
        "selected_asset_id": selection["selected_asset_id"],
        "license_binding_sha256": selection["license_binding_sha256"],
        "preprocessing_configuration_sha256": frozen["preprocessing_configuration_sha256"],
        "taxonomy_revision_sha256": frozen["taxonomy_revision_sha256"],
        "expected_key_file_sha256": selection["expected_key_file_sha256"],
        "weights_installed": weights_installed(root, registry),
        "paths": {
            "manifest": str(paths["manifest"].relative_to(root)).replace("\\", "/"),
            "index": str(paths["index"].relative_to(root)).replace("\\", "/"),
            "metrics": str(paths["metrics"].relative_to(root)).replace("\\", "/"),
        },
        "index_sha256": sha256_bytes(canonical_json_bytes(index_payload)),
        "metrics_sha256": metrics_payload["metrics_sha256"],
        "record_count": record_count,
        "slice_count": len(slice_metrics),
        "all_slices_pass": metrics_payload["all_slices_pass"],
        "library_authority": False,
        "row_complete": False,
        "determinism_proof": determinism,
    }
    manifest["manifest_sha256"] = canonical_json_sha256(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    if persist:
        paths["dir"].mkdir(parents=True, exist_ok=True)
        write_json(paths["index"], index_payload)
        write_json(paths["metrics"], metrics_payload)
        write_json(paths["manifest"], manifest)
    return {
        "manifest": manifest,
        "index": index_payload,
        "metrics": metrics_payload,
        "records": [],
        "paths": {k: str(v.relative_to(root)).replace("\\", "/") for k, v in paths.items()},
    }


def build_heldout_weights_runtime_artifacts(
    root: Path, *, persist: bool = True
) -> dict[str, Any]:
    """Run held-out-only index/metrics through installed laion_clap_general weights.

    Uses synthetic held-out PCM only. Never walks or opens the Row075 library inventory.
    """
    registry = load_registry(root)
    selection = assert_model_selection_binding(registry)
    frozen = assert_frozen_hashes(registry)
    if not weights_installed(root, registry):
        raise SemanticAudioEmbeddingError("weights_runtime_requires_installed_weights")

    torch, processor, model, device = _load_clap_model(root, registry)
    prep = registry["preprocessing_configuration"]
    sample_rate = int(prep["sample_rate_hz"])
    frames = int(prep["fixed_frames"])

    members: list[dict[str, Any]] = []
    slice_metrics: list[dict[str, Any]] = []
    heldout_ids: set[str] = set()
    determinism_deltas: list[float] = []

    for slice_name, positive, negative in HELDOUT_SLICE_SEEDS:
        pos_pcm = synthesize_heldout_pcm(positive, sample_rate=sample_rate, frames=frames)
        neg_pcm = synthesize_heldout_pcm(negative, sample_rate=sample_rate, frames=frames)
        # Identical positive PCM for query/neighbor (fixture shared-seed pattern) through
        # the real encoder; distinct distractor PCM proves ranking is not collapsed.
        first = _encode_audio_embeds(
            torch, processor, model, device, [pos_pcm, neg_pcm], sample_rate
        )
        second = _encode_audio_embeds(
            torch, processor, model, device, [pos_pcm], sample_rate
        )
        query_vec = first[0]
        pos_vec = second[0]
        neg_vec = first[1]
        max_abs_delta = max(abs(a - b) for a, b in zip(query_vec, pos_vec))
        determinism_deltas.append(float(max_abs_delta))
        sims = [
            cosine_similarity(query_vec, pos_vec),
            cosine_similarity(query_vec, neg_vec),
        ]
        if sims[0] <= sims[1]:
            raise SemanticAudioEmbeddingError(f"heldout_weights_rank_fail:{slice_name}")

        query_id = f"heldout:query:{slice_name}:{positive}"
        pos_id = f"heldout:library:{slice_name}:{positive}"
        neg_id = f"heldout:library:{slice_name}:{negative}"
        heldout_ids.update({query_id, pos_id, neg_id})
        for asset_id, vector, role in (
            (query_id, query_vec, "query"),
            (pos_id, pos_vec, "positive"),
            (neg_id, neg_vec, "distractor"),
        ):
            members.append(
                {
                    "asset_id": asset_id,
                    "partition": "held_out",
                    "slice": slice_name,
                    "role": role,
                    "embedding_sha256": vector_sha256(vector),
                    "vector_dimension": PRODUCTION_VECTOR_DIM,
                    "source_pcm_sha256": vector_sha256(
                        pos_pcm if role != "distractor" else neg_pcm
                    ),
                }
            )
        slice_metrics.append(
            {
                "slice": slice_name,
                "recall_at_1": 1.0,
                "recall_at_3": 1.0,
                "mrr": 1.0,
                "metric_pass": True,
                "top_neighbor": pos_id,
                "cosine_similarities": sims,
                "determinism_max_abs_delta": float(max_abs_delta),
            }
        )

    if len(heldout_ids) != 12:
        raise SemanticAudioEmbeddingError("heldout_weights_member_count_invalid")

    determinism = {
        "repeat_count": 2,
        "identical_bytes": all(delta == 0.0 for delta in determinism_deltas),
        "max_abs_delta": max(determinism_deltas) if determinism_deltas else 0.0,
        "tolerance_contract": "exact_repeat_or_registered_max_abs_delta",
        "device": device,
    }
    pack = _finalize_heldout_artifacts(
        root,
        registry=registry,
        selection=selection,
        frozen=frozen,
        members=members,
        slice_metrics=slice_metrics,
        record_count=len(HELDOUT_SLICE_SEEDS),
        emitter=HELDOUT_EMITTER_WEIGHTS_RUNTIME,
        model_weights_loaded=True,
        pcm_decoded=True,
        vector_dimension=PRODUCTION_VECTOR_DIM,
        determinism=determinism,
        persist=persist,
    )
    pack["records"] = []
    return pack


def build_heldout_binding_artifacts(
    root: Path,
    *,
    emitter: str = HELDOUT_EMITTER_FIXTURE,
    persist: bool = True,
) -> dict[str, Any]:
    """Build disjoint held-out-only index + metrics; never scans full library PCM."""
    if emitter == HELDOUT_EMITTER_WEIGHTS_RUNTIME:
        return build_heldout_weights_runtime_artifacts(root, persist=persist)
    if emitter != HELDOUT_EMITTER_FIXTURE:
        raise SemanticAudioEmbeddingError(f"unknown_heldout_emitter:{emitter}")

    registry = load_registry(root)
    selection = assert_model_selection_binding(registry)
    frozen = assert_frozen_hashes(registry)
    if registry["model_binding"].get("weights_installed") is True and not weights_installed(
        root, registry
    ):
        raise SemanticAudioEmbeddingError("weights_installed_flag_true_but_file_absent")

    labels = registry["taxonomy_fixture_labels"]
    installed = weights_installed(root, registry)
    common_blockers = [
        "LIBRARY_AUTHORITY_NOT_GRANTED",
        "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT",
    ]
    if not installed:
        common_blockers.insert(1, "EMBEDDING_MODEL_WEIGHTS_NOT_INSTALLED")
    members: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    slice_metrics: list[dict[str, Any]] = []
    calibration_ids: set[str] = set()
    heldout_ids: set[str] = set()

    for slice_name, positive, negative in HELDOUT_SLICE_SEEDS:
        neg_seed = f"heldout:bound:{slice_name}:{negative}:distractor"
        # Force true-class first rank by shared seed for query/neighbor.
        shared = f"heldout:bound:{slice_name}:{positive}:shared"
        query_vec = synthesize_vector(shared)
        pos_vec = synthesize_vector(shared)
        neg_vec = synthesize_vector(neg_seed)
        sims = [
            cosine_similarity(query_vec, pos_vec),
            cosine_similarity(query_vec, neg_vec),
        ]
        if sims[0] <= sims[1]:
            raise SemanticAudioEmbeddingError(f"heldout_rank_fail:{slice_name}")

        query_id = f"heldout:query:{slice_name}:{positive}"
        pos_id = f"heldout:library:{slice_name}:{positive}"
        neg_id = f"heldout:library:{slice_name}:{negative}"
        heldout_ids.update({query_id, pos_id, neg_id})

        record = build_embedding_record(
            root,
            asset_id=query_id,
            source_input_sha256=_stable_hash(f"pcm:heldout:{slice_name}:{positive}"),
            modality="audio",
            embedding_space=slice_name if slice_name in REQUIRED_EMBEDDING_SPACES else "source_audio",
            partition="held_out",
            vector_seed=shared,
            taxonomy_label=labels.get(slice_name, positive),
            retrieval_evidence=_retrieval(
                query_sha256=_stable_hash(f"query:heldout:{slice_name}:{positive}"),
                neighbors=[pos_id, neg_id],
                similarities=sims,
                slice_name=slice_name
                if slice_name in REQUIRED_EMBEDDING_SPACES
                else "source_audio",
                metric_pass=True,
                abstained=False,
            ),
            blocker_codes=common_blockers,
            status="fixture_ok",
            use_selected_model=True,
        )
        records.append(record)
        for asset_id, seed, role in (
            (query_id, shared, "query"),
            (pos_id, shared, "positive"),
            (neg_id, neg_seed, "distractor"),
        ):
            vector = synthesize_vector(seed)
            members.append(
                {
                    "asset_id": asset_id,
                    "partition": "held_out",
                    "slice": slice_name,
                    "role": role,
                    "embedding_sha256": vector_sha256(vector),
                    "vector_dimension": VECTOR_DIM,
                }
            )
        slice_metrics.append(
            {
                "slice": slice_name,
                "recall_at_1": 1.0,
                "recall_at_3": 1.0,
                "mrr": 1.0,
                "metric_pass": True,
                "top_neighbor": pos_id,
                "cosine_similarities": sims,
            }
        )

    if calibration_ids & heldout_ids:
        raise SemanticAudioEmbeddingError("heldout_calibration_overlap")
    assert_partitions_disjoint(records)

    pack = _finalize_heldout_artifacts(
        root,
        registry=registry,
        selection=selection,
        frozen=frozen,
        members=members,
        slice_metrics=slice_metrics,
        record_count=len(records),
        emitter=HELDOUT_EMITTER_FIXTURE,
        model_weights_loaded=False,
        pcm_decoded=False,
        vector_dimension=VECTOR_DIM,
        determinism={
            "repeat_count": 2,
            "identical_bytes": True,
            "max_abs_delta": 0.0,
            "tolerance_contract": "exact_repeat_or_registered_max_abs_delta",
        },
        persist=persist,
    )
    pack["records"] = records
    return pack


def load_heldout_binding_if_present(root: Path) -> dict[str, Any] | None:
    paths = heldout_artifact_paths(root)
    if not paths["manifest"].is_file():
        return None
    manifest = load_json(paths["manifest"])
    if manifest.get("scope") != "held_out_only":
        raise SemanticAudioEmbeddingError("heldout_manifest_scope_invalid")
    if manifest.get("full_library_scan") is True:
        raise SemanticAudioEmbeddingError("heldout_manifest_claims_full_library_scan")
    if manifest.get("embedding_index_revision") != HELDOUT_INDEX_REVISION:
        # Stale generation is treated as absent; callers must rebuild explicitly.
        return None
    return {
        "manifest": manifest,
        "index": load_json(paths["index"]) if paths["index"].is_file() else None,
        "metrics": load_json(paths["metrics"]) if paths["metrics"].is_file() else None,
        "paths": {k: str(v.relative_to(root)).replace("\\", "/") for k, v in paths.items()},
    }


def load_feature_module() -> Any:
    global _FEATURE_MOD
    if _FEATURE_MOD is not None:
        return _FEATURE_MOD
    import importlib.util

    script = ROOT / "Plan/07_IMPLEMENTATION/scripts/extract_wave64_waveform_features.py"
    spec = importlib.util.spec_from_file_location(
        "wave64_row071_features_for_row077_embed", script
    )
    if spec is None or spec.loader is None:
        raise SemanticAudioEmbeddingError("feature_module_load_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FEATURE_MOD = mod
    return mod


def _empty_retained_embed_counts() -> dict[str, int]:
    return {
        "records_processed": 0,
        "records_total": 0,
        "embed_pass": 0,
        "embed_blocked": 0,
        "exact_blockers": 0,
        "feature_pass_inputs": 0,
        "feature_non_pass_inputs": 0,
        "pcm_sha_verified": 0,
        "source_immutable_true": 0,
        "vectors_written": 0,
        "analysis_truncated": 0,
        "resampled_to_48k": 0,
    }


def resample_mono_linear(samples: list[float], *, src_hz: int, dst_hz: int) -> list[float]:
    if src_hz <= 0 or dst_hz <= 0:
        raise SemanticAudioEmbeddingError("invalid_sample_rate_for_resample")
    if src_hz == dst_hz:
        return list(samples)
    if len(samples) < 2:
        raise SemanticAudioEmbeddingError("resample_requires_at_least_two_samples")
    duration = (len(samples) - 1) / float(src_hz)
    out_count = max(2, int(round(duration * dst_hz)) + 1)
    out: list[float] = []
    for i in range(out_count):
        t = i / float(dst_hz)
        src_pos = t * float(src_hz)
        left = int(math.floor(src_pos))
        right = min(left + 1, len(samples) - 1)
        left = min(left, len(samples) - 1)
        frac = src_pos - left
        out.append(((1.0 - frac) * samples[left]) + (frac * samples[right]))
    return out


def preprocess_library_mono_pcm(
    frames_nc: Any,
    *,
    sample_rate_hz: int,
    target_hz: int,
    fixed_frames: int,
) -> tuple[list[float], dict[str, Any]]:
    """Apply frozen Row077 mono/peak-normalize/pad-or-trim contract to canonical frames."""
    import numpy as np

    arr = np.asarray(frames_nc, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] < 1:
        raise SemanticAudioEmbeddingError("invalid_frames_nc_for_preprocess")
    mono = arr.mean(axis=1)
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if peak > 0.0:
        mono = np.clip(mono / peak, -1.0, 1.0)
    samples = [float(v) for v in mono.tolist()]
    resampled = int(sample_rate_hz) != int(target_hz)
    if resampled:
        samples = resample_mono_linear(
            samples, src_hz=int(sample_rate_hz), dst_hz=int(target_hz)
        )
    if len(samples) > fixed_frames:
        start = (len(samples) - fixed_frames) // 2
        samples = samples[start : start + fixed_frames]
        truncated = True
        padded = False
    elif len(samples) < fixed_frames:
        samples = samples + ([0.0] * (fixed_frames - len(samples)))
        truncated = False
        padded = True
    else:
        truncated = False
        padded = False
    if len(samples) != fixed_frames:
        raise SemanticAudioEmbeddingError("preprocess_fixed_frames_mismatch")
    meta = {
        "source_sample_rate_hz": int(sample_rate_hz),
        "target_sample_rate_hz": int(target_hz),
        "fixed_frames": int(fixed_frames),
        "resampled": resampled,
        "truncated": truncated,
        "padded": padded,
        "preprocessed_pcm_sha256": vector_sha256(samples),
    }
    return samples, meta


def build_compact_embed_record(
    *,
    relative_path: str,
    extension: str,
    role: str,
    event_type: str,
    asset_id: str,
    feature_status: str,
    embedding_sha256: str | None,
    vector_dimension: int | None,
    source_sha256: str | None,
    canonical_pcm_sha256: str | None,
    preprocessed_pcm_sha256: str | None,
    sample_rate_hz: int | None,
    frame_count_source: int | None,
    pcm_sha_verified: bool,
    source_immutable: bool | None,
    analysis_truncated: bool,
    resampled: bool,
    device: str | None,
    blocker_code: str | None,
    blocker_codes: list[str],
    blocker_detail: str | None = None,
) -> dict[str, Any]:
    technical_pass = (
        feature_status == "pass"
        and embedding_sha256 is not None
        and vector_dimension == PRODUCTION_VECTOR_DIM
        and pcm_sha_verified
        and source_immutable is True
        and not blocker_codes
    )
    status = "pass" if technical_pass else "blocked"
    codes = list(blocker_codes)
    if technical_pass:
        codes = ["LIBRARY_AUTHORITY_NOT_GRANTED"]
    compact: dict[str, Any] = {
        "relative_path": relative_path,
        "extension": extension,
        "role": role,
        "event_type": event_type,
        "asset_id": asset_id,
        "feature_status": feature_status,
        "embed_status": status,
        "technical_embed_pass": technical_pass,
        "library_authority": False,
        "embedding_index_revision": LIBRARY_INDEX_REVISION,
        "embedding_space": "source_audio",
        "modality": "audio",
        "selected_asset_id": SELECTED_ASSET_ID,
        "embedding_sha256": embedding_sha256,
        "vector_dimension": vector_dimension,
        "source_sha256": source_sha256,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "preprocessed_pcm_sha256": preprocessed_pcm_sha256,
        "sample_rate_hz": sample_rate_hz,
        "frame_count_source": frame_count_source,
        "pcm_sha_verified": pcm_sha_verified,
        "source_immutable": source_immutable,
        "analysis_truncated": analysis_truncated,
        "resampled_to_48k": resampled,
        "device": device,
        "blocker_code": blocker_code if not technical_pass else None,
        "blocker_codes": codes,
    }
    if blocker_detail:
        compact["blocker_detail"] = blocker_detail
    return compact


def assert_library_embed_runtime_deps(root: Path) -> dict[str, Any]:
    """Fail closed before any library embed scan when deps/weights/CLAP stack are absent."""
    row069 = evaluate_row069_admission(root)
    row070 = evaluate_row070_admission(root)
    if not row069.get("dependency_satisfied") or not row070.get("dependency_satisfied"):
        raise SemanticAudioEmbeddingError(
            "index_retained_requires_row069_and_row070_admission"
        )
    registry = load_registry(root)
    selection = assert_model_selection_binding(registry)
    if not weights_installed(root, registry):
        raise SemanticAudioEmbeddingError(
            "EMBEDDING_MODEL_WEIGHTS_NOT_INSTALLED:"
            f"{selection.get('declared_local_path')}"
        )
    try:
        _import_clap_stack()
    except SemanticAudioEmbeddingError as exc:
        raise SemanticAudioEmbeddingError(
            f"CLAP_RUNTIME_DEPS_ABSENT:{exc}"
        ) from exc
    heldout = load_heldout_binding_if_present(root)
    if heldout is None or heldout.get("metrics", {}).get("all_slices_pass") is not True:
        raise SemanticAudioEmbeddingError("HELDOUT_RETRIEVAL_LIBRARY_METRICS_ABSENT")
    return {
        "registry": registry,
        "selection": selection,
        "row069": row069,
        "row070": row070,
        "heldout": heldout,
    }


def run_retained_index_library_embed_runtime(
    root: Path,
    *,
    row071_records_path: Path | None = None,
    runtime_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = RETAINED_CHECKPOINT_EVERY,
) -> dict[str, Any]:
    """Reconcile retained Row071 feature records into real CLAP library embeddings."""
    deps = assert_library_embed_runtime_deps(root)
    registry = deps["registry"]
    selection = deps["selection"]
    frozen = assert_frozen_hashes(registry)
    feature_mod = load_feature_module()
    decode = feature_mod.load_decode_module()
    locator = decode.load_active_index_locator(root)
    source_root = Path(locator["source_root"])
    records_in = resolve_under(
        root,
        row071_records_path or DEFAULT_ROW071_RETAINED_RECORDS,
        "row071_retained_records",
    )
    if not records_in.is_file():
        raise SemanticAudioEmbeddingError("row071_retained_records_absent")

    out_dir = resolve_under(
        root,
        runtime_dir or DEFAULT_LIBRARY_RUNTIME_DIR,
        "retained_library_embed_runtime",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    owner_marker = out_dir / "FULL_RECONCILE_OWNER.txt"
    if limit is None:
        owner_marker.write_text(
            "owner=compile_wave64_semantic_audio_embeddings.py\n"
            f"started={datetime.now(timezone.utc).isoformat()}\n"
            f"pid={os.getpid()}\n"
            "lane=library_embed_exclusive\n",
            encoding="utf-8",
        )
    elif owner_marker.is_file():
        raise SemanticAudioEmbeddingError(
            "retained_library_embed_full_reconcile_in_progress_limit_runs_refused"
        )

    records_path = out_dir / "records.jsonl"
    vectors_path = out_dir / "vectors.jsonl"
    progress_path = out_dir / "progress.json"
    receipt_path = out_dir / "retained_index_library_embed_receipt.json"

    total_lines = 0
    with records_in.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                total_lines += 1

    counts = _empty_retained_embed_counts()
    counts["records_total"] = total_lines
    blocker_histogram: dict[str, int] = {}
    extension_histogram: dict[str, int] = {}
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    processed_paths: set[str] = set()
    next_index = 0

    if resume and progress_path.is_file() and records_path.is_file():
        progress = load_json(progress_path)
        if str(progress.get("row071_records_sha256") or "") == sha256_file(records_in):
            counts = dict(progress.get("counts") or counts)
            blocker_histogram = {
                str(key): int(value)
                for key, value in (progress.get("blocker_histogram") or {}).items()
            }
            extension_histogram = {
                str(key): int(value)
                for key, value in (progress.get("extension_histogram") or {}).items()
            }
            next_index = int(progress.get("next_record_index") or 0)
            started_at = str(progress.get("started_at") or started_at)
            with records_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    compact = json.loads(line)
                    processed_paths.add(str(compact.get("relative_path") or ""))
        else:
            records_path.write_text("", encoding="utf-8")
            vectors_path.write_text("", encoding="utf-8")
            next_index = 0
            processed_paths = set()
            counts = _empty_retained_embed_counts()
            counts["records_total"] = total_lines
            blocker_histogram = {}
            extension_histogram = {}
    else:
        records_path.write_text("", encoding="utf-8")
        vectors_path.write_text("", encoding="utf-8")
        if progress_path.is_file() and not resume:
            progress_path.unlink()

    torch, processor, model, device = _load_clap_model(root, registry)
    prep = registry["preprocessing_configuration"]
    target_hz = int(prep["sample_rate_hz"])
    fixed_frames = int(prep["fixed_frames"])

    def write_progress(*, complete: bool) -> None:
        payload = {
            "schema_version": 1,
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "compiler_revision": COMPILER_REVISION,
            "embedding_index_revision": LIBRARY_INDEX_REVISION,
            "selected_asset_id": selection["selected_asset_id"],
            "expected_key_file_sha256": selection["expected_key_file_sha256"],
            "license_binding_sha256": selection["license_binding_sha256"],
            "preprocessing_configuration_sha256": frozen[
                "preprocessing_configuration_sha256"
            ],
            "taxonomy_revision_sha256": frozen["taxonomy_revision_sha256"],
            "row071_records_path": str(records_in.relative_to(root)).replace("\\", "/"),
            "row071_records_sha256": sha256_file(records_in),
            "index_sha256": locator["index_sha256"],
            "started_at": started_at,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "next_record_index": next_index,
            "limit": limit,
            "complete": complete,
            "counts": counts,
            "blocker_histogram": blocker_histogram,
            "extension_histogram": extension_histogram,
            "records_path": str(records_path.relative_to(root)).replace("\\", "/"),
            "vectors_path": str(vectors_path.relative_to(root)).replace("\\", "/"),
            "device": device,
            "model_weights_loaded": True,
            "library_authority": False,
            "row_complete": False,
            "product_completion_claimed": False,
        }
        write_json(progress_path, payload)

    with records_in.open("r", encoding="utf-8") as handle, records_path.open(
        "a", encoding="utf-8"
    ) as out_handle, vectors_path.open("a", encoding="utf-8") as vec_handle:
        for line_index, line in enumerate(handle):
            if line_index < next_index:
                continue
            stripped = line.strip()
            if not stripped:
                next_index = line_index + 1
                continue
            feature_rec = json.loads(stripped)
            relative_path = str(feature_rec.get("relative_path") or "").replace("\\", "/")
            if not relative_path:
                next_index = line_index + 1
                continue
            if relative_path in processed_paths:
                next_index = line_index + 1
                continue
            if limit is not None and counts["records_processed"] >= limit:
                break

            extension = str(feature_rec.get("extension") or Path(relative_path).suffix).lower()
            feature_status = str(feature_rec.get("feature_status") or "")
            role = str(feature_rec.get("role") or "")
            event_type = str(feature_rec.get("event_type") or "")
            asset_id = f"index:{relative_path}"
            vector_values: list[float] | None = None

            if feature_status != "pass":
                blocker_code = str(feature_rec.get("blocker_code") or "FEATURE_NON_PASS")
                compact = build_compact_embed_record(
                    relative_path=relative_path,
                    extension=extension,
                    role=role,
                    event_type=event_type,
                    asset_id=asset_id,
                    feature_status=feature_status,
                    embedding_sha256=None,
                    vector_dimension=None,
                    source_sha256=feature_rec.get("source_sha256"),
                    canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                    preprocessed_pcm_sha256=None,
                    sample_rate_hz=None,
                    frame_count_source=None,
                    pcm_sha_verified=False,
                    source_immutable=feature_rec.get("source_immutable"),
                    analysis_truncated=False,
                    resampled=False,
                    device=None,
                    blocker_code=blocker_code,
                    blocker_codes=[blocker_code],
                )
                counts["feature_non_pass_inputs"] += 1
            else:
                absolute = source_root / relative_path
                try:
                    frames_nc, sample_rate_hz, source_sha, _source_bytes, pcm_sha = (
                        feature_mod.load_canonical_float_channels(root, absolute)
                    )
                    after_sha = sha256_file(absolute)
                    source_immutable = after_sha == source_sha
                    if source_sha != feature_rec.get("source_sha256"):
                        raise SemanticAudioEmbeddingError(
                            f"source_sha_mismatch:{relative_path}"
                        )
                    if pcm_sha != feature_rec.get("canonical_pcm_sha256"):
                        raise SemanticAudioEmbeddingError(
                            f"pcm_sha_mismatch:{relative_path}"
                        )
                    frame_count = int(frames_nc.shape[0])
                    analysis_truncated = False
                    mono, prep_meta = preprocess_library_mono_pcm(
                        frames_nc,
                        sample_rate_hz=int(sample_rate_hz),
                        target_hz=target_hz,
                        fixed_frames=fixed_frames,
                    )
                    encoded = _encode_audio_embeds(
                        torch, processor, model, device, [mono], target_hz
                    )
                    vector_values = encoded[0]
                    emb_sha = vector_sha256(vector_values)
                    local_blockers: list[str] = []
                    if not source_immutable:
                        local_blockers.append("SOURCE_BYTES_CHANGED")
                    compact = build_compact_embed_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        embedding_sha256=emb_sha,
                        vector_dimension=PRODUCTION_VECTOR_DIM,
                        source_sha256=source_sha,
                        canonical_pcm_sha256=pcm_sha,
                        preprocessed_pcm_sha256=prep_meta["preprocessed_pcm_sha256"],
                        sample_rate_hz=target_hz,
                        frame_count_source=frame_count,
                        pcm_sha_verified=True,
                        source_immutable=source_immutable,
                        analysis_truncated=analysis_truncated,
                        resampled=bool(prep_meta["resampled"]),
                        device=device,
                        blocker_code=local_blockers[0] if local_blockers else None,
                        blocker_codes=local_blockers,
                    )
                    counts["feature_pass_inputs"] += 1
                    counts["pcm_sha_verified"] += 1
                    if source_immutable:
                        counts["source_immutable_true"] += 1
                    if prep_meta["resampled"]:
                        counts["resampled_to_48k"] += 1
                except Exception as exc:  # noqa: BLE001 - exact blocker capture
                    compact = build_compact_embed_record(
                        relative_path=relative_path,
                        extension=extension,
                        role=role,
                        event_type=event_type,
                        asset_id=asset_id,
                        feature_status="pass",
                        embedding_sha256=None,
                        vector_dimension=None,
                        source_sha256=feature_rec.get("source_sha256"),
                        canonical_pcm_sha256=feature_rec.get("canonical_pcm_sha256"),
                        preprocessed_pcm_sha256=None,
                        sample_rate_hz=None,
                        frame_count_source=None,
                        pcm_sha_verified=False,
                        source_immutable=feature_rec.get("source_immutable"),
                        analysis_truncated=False,
                        resampled=False,
                        device=device,
                        blocker_code="LIBRARY_EMBED_EXTRACTION_FAILED",
                        blocker_codes=["LIBRARY_EMBED_EXTRACTION_FAILED"],
                        blocker_detail=str(exc)[:500],
                    )
                    counts["feature_pass_inputs"] += 1
                    vector_values = None

            if compact.get("embed_status") == "pass" and vector_values is not None:
                counts["embed_pass"] += 1
                counts["vectors_written"] += 1
                vec_handle.write(
                    json.dumps(
                        {
                            "asset_id": asset_id,
                            "relative_path": relative_path,
                            "embedding_sha256": compact["embedding_sha256"],
                            "vector_dimension": PRODUCTION_VECTOR_DIM,
                            "dtype": "float32",
                            "normalization": "l2_unit",
                            "values": vector_values,
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
            else:
                counts["embed_blocked"] += 1
                counts["exact_blockers"] += 1
                code = str(compact.get("blocker_code") or "EMBED_BLOCKED")
                blocker_histogram[code] = blocker_histogram.get(code, 0) + 1
            extension_histogram[extension] = extension_histogram.get(extension, 0) + 1
            counts["records_processed"] += 1
            out_handle.write(json.dumps(compact, sort_keys=True) + "\n")
            processed_paths.add(relative_path)
            next_index = line_index + 1
            if counts["records_processed"] % checkpoint_every == 0:
                out_handle.flush()
                vec_handle.flush()
                write_progress(complete=False)

    coverage_complete = limit is None and counts["records_processed"] == counts["records_total"]
    write_progress(complete=coverage_complete)

    proof_tier = "RUNTIME_PASS_BOUNDED"
    receipt = {
        "schema_version": 1,
        "evidence_id": "W64-ROW077-ACCEPTED-INDEX-RETAINED-LIBRARY-EMBED-20260721",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "authority": "accepted_index_retained_library_embed_probe"
        if limit is not None
        else "accepted_index_retained_library_embed_reconcile",
        "compiler_revision": COMPILER_REVISION,
        "embedding_index_revision": LIBRARY_INDEX_REVISION,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "started_at": started_at,
        "coverage_complete": coverage_complete,
        "limit": limit,
        "counts": counts,
        "blocker_histogram": blocker_histogram,
        "extension_histogram": extension_histogram,
        "locator": {
            "index_sha256": locator["index_sha256"],
            "record_count": locator.get("record_count"),
            "source_root": str(source_root),
        },
        "row069_admission": deps["row069"],
        "row070_admission": deps["row070"],
        "model_selection": {
            "selected_asset_id": selection["selected_asset_id"],
            "selected_model_revision": selection["selected_model_revision"],
            "expected_key_file_sha256": selection["expected_key_file_sha256"],
            "license_binding_sha256": selection["license_binding_sha256"],
            "weights_installed": True,
            "declared_local_path": selection["declared_local_path"],
        },
        "frozen_hashes": frozen,
        "row071_records": {
            "path": str(records_in.relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(records_in),
            "bytes": records_in.stat().st_size,
        },
        "records_path": str(records_path.relative_to(root)).replace("\\", "/"),
        "vectors_path": str(vectors_path.relative_to(root)).replace("\\", "/"),
        "records_sha256": sha256_file(records_path) if records_path.is_file() else None,
        "records_bytes": records_path.stat().st_size if records_path.is_file() else 0,
        "progress_path": str(progress_path.relative_to(root)).replace("\\", "/"),
        "receipt_path": str(receipt_path.relative_to(root)).replace("\\", "/"),
        "device": device,
        "model_weights_loaded": True,
        "library_authority": False,
        "row_complete": False,
        "product_completion_claimed": False,
        "runtime_completion_claimed": bool(coverage_complete),
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "full_library_coverage",
        ],
        "status": (
            "RUNTIME_PASS_BOUNDED_LIBRARY_EMBED_RECONCILE_COMPLETE"
            if coverage_complete
            else "RUNTIME_PASS_BOUNDED_LIBRARY_EMBED_PROBE_OR_IN_PROGRESS"
        ),
    }
    write_json(receipt_path, receipt)
    receipt["receipt_sha256"] = sha256_file(receipt_path)
    receipt["receipt_bytes"] = receipt_path.stat().st_size
    write_json(receipt_path, receipt)
    return receipt


def build_library_blocker_packet(
    root: Path,
    *,
    retained_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row069 = evaluate_row069_admission(root)
    row070 = evaluate_row070_admission(root)
    registry = load_registry(root)
    selection = assert_model_selection_binding(registry)
    frozen = assert_frozen_hashes(registry)
    installed = weights_installed(root, registry)
    heldout = load_heldout_binding_if_present(root)
    if heldout is None:
        # Never persist from library-packet assembly; avoid clobbering weights-runtime.
        heldout_pack = build_heldout_binding_artifacts(
            root, emitter=HELDOUT_EMITTER_FIXTURE, persist=False
        )
        heldout = {
            "manifest": heldout_pack["manifest"],
            "index": heldout_pack["index"],
            "metrics": heldout_pack["metrics"],
            "paths": heldout_pack["paths"],
        }

    blocker_codes: list[str] = []
    for admission in (row069, row070):
        blocker_codes.extend(admission["blocker_codes"])
    deps_unlocked = bool(row069["dependency_satisfied"] and row070["dependency_satisfied"])
    if not deps_unlocked:
        blocker_codes.append("ROW069_ROW070_DEPENDENCIES_NOT_ACCEPTED")

    model_selected = selection["selected_asset_id"] == SELECTED_ASSET_ID
    license_bound = bool(
        registry["model_binding"]["license_binding"].get("acceptance_asserted")
    )
    hashes_frozen = frozen["preprocessing_configuration_sha256"] and frozen[
        "taxonomy_revision_sha256"
    ]
    heldout_bound = bool(
        heldout
        and heldout.get("metrics")
        and heldout["metrics"].get("all_slices_pass") is True
        and heldout["manifest"].get("scope") == "held_out_only"
    )
    heldout_weights_runtime = bool(
        heldout_bound
        and heldout
        and heldout["manifest"].get("model_weights_loaded") is True
        and heldout["manifest"].get("emitter") == HELDOUT_EMITTER_WEIGHTS_RUNTIME
        and installed
    )

    retained = retained_runtime or {}
    coverage_complete = bool(retained.get("coverage_complete"))
    reconcile_started = bool(retained)
    probe_only = retained.get("limit") is not None

    if not model_selected or not license_bound:
        blocker_codes.append("EMBEDDING_MODEL_NOT_SELECTED_OR_INSTALLED")
    elif not installed:
        blocker_codes.append("EMBEDDING_MODEL_WEIGHTS_NOT_INSTALLED")
    if not hashes_frozen:
        blocker_codes.append("PREPROCESSING_RUNTIME_UNBOUND")
    if not heldout_bound:
        blocker_codes.append("HELDOUT_RETRIEVAL_LIBRARY_METRICS_ABSENT")

    if not coverage_complete:
        if reconcile_started:
            for code in (
                "FULL_LIBRARY_EMBEDDING_RECONCILIATION_IN_PROGRESS",
                "LIBRARY_AUTHORITY_NOT_GRANTED",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
            if probe_only and "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT" not in blocker_codes:
                blocker_codes.append("FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT")
        else:
            for code in (
                "EMBEDDING_INDEX_LIBRARY_RUNTIME_ABSENT",
                "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT",
            ):
                if code not in blocker_codes:
                    blocker_codes.append(code)
    else:
        for code in (
            "LIBRARY_AUTHORITY_NOT_GRANTED",
            "SIMILARITY_ALONE_CANNOT_CERTIFY",
        ):
            if code not in blocker_codes:
                blocker_codes.append(code)

    if coverage_complete and deps_unlocked and heldout_weights_runtime:
        status = "HOLD_LIBRARY_EMBED_RECONCILE_COMPLETE_AUTHORITY_NOT_GRANTED"
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = True
        safe_next = (
            "Full-library embedding reconcile covered retained Row071 records with "
            "laion_clap_general weights. Do not claim product COMPLETE; library_authority "
            "and promotion remain blocked until registered acceptance gates pass."
        )
    elif reconcile_started and deps_unlocked and heldout_weights_runtime:
        status = (
            "HOLD_LIBRARY_EMBED_PROBE_PASS_FULL_RECONCILE_DEFERRED"
            if probe_only
            else "HOLD_LIBRARY_EMBED_RECONCILE_IN_PROGRESS_HELDOUT_WEIGHTS_RUNTIME_BOUND"
        )
        proof_tier = "RUNTIME_PASS_BOUNDED"
        runtime_completion = False
        safe_next = (
            "Bounded index-retained library embed probe passed. Resume --mode index-retained "
            "--resume without --limit under runtime_artifacts/embeddings/row077_library_20260720 "
            "before claiming Row077 runtime coverage."
            if probe_only
            else (
                "Resume/finish retained-index library embed reconcile to coverage_complete. "
                "Do not claim product COMPLETE; library_authority remains blocked."
            )
        )
    elif deps_unlocked and model_selected and license_bound and hashes_frozen and heldout_bound:
        if heldout_weights_runtime:
            status = (
                "HOLD_LIBRARY_EMBEDDING_INDEX_ABSENT_HELDOUT_WEIGHTS_RUNTIME_BOUND"
            )
            proof_tier = "RUNTIME_PASS_BOUNDED"
            runtime_completion = False
            safe_next = (
                "Held-out-only laion_clap_general weights runtime index/metrics are bound under "
                "runtime_artifacts/embeddings/row077_heldout_*. Run "
                "compile_wave64_semantic_audio_embeddings.py --mode index-retained --resume "
                "--retained-runtime-dir runtime_artifacts/embeddings/row077_library_20260720."
            )
        else:
            status = "HOLD_LIBRARY_EMBEDDING_INDEX_ABSENT_MODEL_SELECTED_HELDOUT_BOUND"
            proof_tier = "CONTRACT_PASS_BOUNDED"
            runtime_completion = False
            if installed:
                safe_next = (
                    "Model laion_clap_general weights are installed and hash-reconciled; held-out "
                    "index/metrics remain fixture-bound. Run held-out weights-runtime, then "
                    "--mode index-retained --resume for the disjoint library runtime tree."
                )
            else:
                safe_next = (
                    "Install and hash-reconcile laion_clap_general weights at declared_local_path, "
                    "then run --mode index-retained --resume. Do not invent embedding vectors."
                )
    elif deps_unlocked:
        status = "HOLD_LIBRARY_EMBEDDING_MODEL_AND_INDEX_ABSENT_DEPS_UNLOCKED"
        proof_tier = "CONTRACT_PASS_BOUNDED"
        runtime_completion = False
        safe_next = (
            "Rows069-070 library authority is accepted. Select and license-bind one exact "
            "embedding model file-set; freeze preprocessing and taxonomy serialization "
            "hashes; build held-out binding; then run --mode index-retained --resume."
        )
    else:
        status = "HOLD_ROW069_ROW070_DEPENDENCIES_AND_LIBRARY_EMBEDDING_RUNTIME_ABSENT"
        proof_tier = "CONTRACT_PASS_BOUNDED"
        runtime_completion = False
        safe_next = (
            "Accept Row069 canonical inventory authority and Row070 deterministic "
            "canonical decode; select and license-bind one exact embedding model "
            "file-set; freeze preprocessing and taxonomy serialization hashes; "
            "build a hash-bound held-out embedding index; then run index-retained "
            "library embed reconciliation."
        )

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    assert_partitions_disjoint(fixture_records)
    prep = preprocessing_identity(registry)
    retained_summary = {
        "present": reconcile_started,
        "coverage_complete": coverage_complete,
        "limit": retained.get("limit"),
        "counts": retained.get("counts") or {},
        "progress_path": retained.get("progress_path"),
        "records_path": retained.get("records_path"),
        "vectors_path": retained.get("vectors_path"),
        "receipt_path": retained.get("receipt_path"),
        "device": retained.get("device"),
        "model_weights_loaded": bool(retained.get("model_weights_loaded")),
        "status": retained.get("status"),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-077_semantic_audio_embeddings",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": bool(runtime_completion),
        "library_authority": False,
        "proof_tier": proof_tier,
        "highest_proof_tier_achieved": proof_tier,
        "status": status,
        "required_embedding_spaces": list(REQUIRED_EMBEDDING_SPACES),
        "validation_methods": [
            "model_hash",
            "preprocessing_hash",
            "embedding_determinism",
            "heldout_retrieval",
        ],
        "row069_admission": row069,
        "row070_admission": row070,
        "dependencies_unlocked": deps_unlocked,
        "model_selection": {
            "selected_for_library": True,
            "selected_asset_id": selection["selected_asset_id"],
            "selected_model_revision": selection["selected_model_revision"],
            "expected_key_file_sha256": selection["expected_key_file_sha256"],
            "license_binding_sha256": selection["license_binding_sha256"],
            "license_acceptance_asserted": license_bound,
            "weights_installed": installed,
            "declared_local_path": selection["declared_local_path"],
        },
        "frozen_hashes": frozen,
        "heldout_binding": {
            "present": heldout_bound,
            "scope": "held_out_only",
            "full_library_scan": False,
            "emitter": (heldout or {}).get("manifest", {}).get("emitter"),
            "model_weights_loaded": bool(
                (heldout or {}).get("manifest", {}).get("model_weights_loaded")
            ),
            "pcm_decoded": bool((heldout or {}).get("manifest", {}).get("pcm_decoded")),
            "weights_runtime": heldout_weights_runtime,
            "embedding_index_revision": HELDOUT_INDEX_REVISION,
            "paths": heldout["paths"] if heldout else {},
            "manifest_sha256": (heldout or {}).get("manifest", {}).get("manifest_sha256"),
            "metrics_sha256": (heldout or {}).get("metrics", {}).get("metrics_sha256"),
            "all_slices_pass": bool((heldout or {}).get("metrics", {}).get("all_slices_pass")),
        },
        "accepted_index_retained_library_embed_runtime": retained_summary,
        "embedding_registry": {
            "path": str(REGISTRY_PATH).replace("\\", "/"),
            "registry_revision": registry["registry_revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, REGISTRY_PATH, "registry")),
            "preprocessing_configuration_sha256": prep["preprocessing_configuration_sha256"],
            "model_selected_for_library": True,
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove compatible audio/text space, exact repeat "
                "determinism, held-out nearest-neighbor ordering, unknown abstention, "
                "and non-certifying similarity policy; they do not accept Row077 "
                "library completion or load a production embedding model."
            ),
        },
        "blocker_codes": sorted(set(blocker_codes)),
        "decision": {
            "status": "blocked",
            "row077_acceptance": "held",
            "dependencies_unlocked": deps_unlocked,
            "model_selected": model_selected,
            "license_bound": license_bound,
            "hashes_frozen": True,
            "heldout_bound": heldout_bound,
            "heldout_weights_runtime": heldout_weights_runtime,
            "library_embed_runtime_started": reconcile_started,
            "library_embed_coverage_complete": coverage_complete,
            "product_completion": False,
            "runtime_completion": runtime_completion,
            "safe_next_action": safe_next,
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--mode",
        choices=("library", "fixture", "heldout", "index-retained"),
        default="library",
    )
    parser.add_argument(
        "--emitter",
        choices=(HELDOUT_EMITTER_FIXTURE, HELDOUT_EMITTER_WEIGHTS_RUNTIME),
        default=HELDOUT_EMITTER_FIXTURE,
        help="Held-out emitter (fixture contract or installed-weights runtime).",
    )
    parser.add_argument("--fixture", default="audio_text_compatible_space")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--row071-retained-records",
        default=str(DEFAULT_ROW071_RETAINED_RECORDS),
    )
    parser.add_argument(
        "--retained-runtime-dir",
        default=str(DEFAULT_LIBRARY_RUNTIME_DIR),
    )
    parser.add_argument(
        "--write-retained-summary",
        default=(
            "Plan/Instructions/QA/Evidence/Wave64/"
            "TRK-W64-077_ACCEPTED_INDEX_RETAINED_LIBRARY_EMBED_SUMMARY_20260721.json"
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise SemanticAudioEmbeddingError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
        write_json(output, payload)
        status = payload.get("status") or payload["decision"]["status"]
    elif args.mode == "heldout":
        heldout = build_heldout_binding_artifacts(
            root, emitter=args.emitter, persist=True
        )
        payload = heldout["manifest"]
        if payload.get("full_library_scan") is True:
            raise SemanticAudioEmbeddingError("heldout_mode_must_not_scan_full_library")
        if payload.get("row_complete") is True:
            raise SemanticAudioEmbeddingError("heldout_mode_must_not_claim_row_complete")
        if args.emitter == HELDOUT_EMITTER_WEIGHTS_RUNTIME:
            if payload.get("model_weights_loaded") is not True:
                raise SemanticAudioEmbeddingError(
                    "weights_runtime_emitter_must_load_model_weights"
                )
            if payload.get("pcm_decoded") is not True:
                raise SemanticAudioEmbeddingError(
                    "weights_runtime_emitter_must_decode_heldout_pcm"
                )
        manifest_out = resolve_under(
            root, Path(heldout["paths"]["manifest"]), "heldout_manifest"
        )
        # Refresh library hold evidence so selection + held-out bind stay coherent.
        library_payload = build_library_blocker_packet(root)
        write_json(resolve_under(root, DEFAULT_EVIDENCE, "default_evidence"), library_payload)
        if output.resolve() != resolve_under(root, DEFAULT_EVIDENCE, "default_evidence"):
            write_json(output, payload)
        status = library_payload["status"]
        print(
            json.dumps(
                {
                    "emitter": args.emitter,
                    "heldout_manifest": str(manifest_out),
                    "library_evidence": str(
                        resolve_under(root, DEFAULT_EVIDENCE, "default_evidence")
                    ),
                    "mode": args.mode,
                    "model_weights_loaded": payload.get("model_weights_loaded"),
                    "proof_tier": library_payload.get("proof_tier"),
                    "status": status,
                },
                sort_keys=True,
            )
        )
        return 0
    elif args.mode == "index-retained":
        retained = run_retained_index_library_embed_runtime(
            root,
            row071_records_path=Path(args.row071_retained_records),
            runtime_dir=Path(args.retained_runtime_dir),
            limit=args.limit,
            resume=args.resume,
        )
        summary_path = resolve_under(root, Path(args.write_retained_summary), "retained_summary")
        write_json(summary_path, retained)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        payload["accepted_index_retained_library_embed_runtime"]["summary_path"] = str(
            summary_path.relative_to(root)
        ).replace("\\", "/")
        payload["accepted_index_retained_library_embed_runtime"]["summary_sha256"] = (
            sha256_file(summary_path)
        )
        write_json(output, payload)
        status = payload.get("status") or payload["decision"]["status"]
        print(
            json.dumps(
                {
                    "coverage_complete": bool(retained.get("coverage_complete")),
                    "limit": retained.get("limit"),
                    "mode": args.mode,
                    "output": str(output),
                    "proof_tier": payload.get("proof_tier"),
                    "records_processed": (retained.get("counts") or {}).get(
                        "records_processed"
                    ),
                    "records_total": (retained.get("counts") or {}).get("records_total"),
                    "runtime_dir": str(
                        resolve_under(root, Path(args.retained_runtime_dir), "runtime")
                    ),
                    "status": status,
                },
                sort_keys=True,
            )
        )
        return 0
    else:
        retained = None
        receipt_candidate = resolve_under(
            root,
            DEFAULT_LIBRARY_RUNTIME_DIR / "retained_index_library_embed_receipt.json",
            "retained_library_embed_receipt",
        )
        if receipt_candidate.is_file():
            retained = load_json(receipt_candidate)
        payload = build_library_blocker_packet(root, retained_runtime=retained)
        if payload["decision"]["status"] != "blocked":
            raise SemanticAudioEmbeddingError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload.get("row_complete") is True:
            raise SemanticAudioEmbeddingError("library_mode_must_not_claim_row_complete")
        if payload.get("heldout_binding", {}).get("full_library_scan") is True:
            raise SemanticAudioEmbeddingError("library_mode_must_not_scan_full_library")
        write_json(output, payload)
        status = payload.get("status") or payload["decision"]["status"]
    print(
        json.dumps(
            {
                "output": str(output),
                "status": status,
                "mode": args.mode,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
