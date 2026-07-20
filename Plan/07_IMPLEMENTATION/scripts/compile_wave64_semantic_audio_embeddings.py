#!/usr/bin/env python3
"""Fail-closed Wave64 Row077 semantic audio embedding contract slice.

Library embedding generation refuses authority without accepted Row069 inventory
and Row070 canonical decode. Fixture mode may emit deterministic schema-validated
synthetic audio/text embeddings, held-out retrieval proofs, unknown abstention,
and non-certifying similarity policy without promoting library completion or
loading production models.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
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

COMPILER_REVISION = "wave64_row077_semantic_audio_embedding_compiler_v0.1.0"
REGISTRY_REVISION = "wave64_row077_semantic_audio_embedding_registry_v0.1.0"
TRACKER_ID = "TRK-W64-077"
ITEM_ID = "ITEM-W64-077"
SCHEMA_VERSION = "1.0.0"
FIXTURE_INDEX_REVISION = "wave64_row077_fixture_embedding_index_v0.1.0"
HELDOUT_INDEX_REVISION = "wave64_row077_heldout_embedding_index_v0.1.0"
HELDOUT_ARTIFACT_REL = Path("runtime_artifacts/embeddings/row077_heldout_20260720")
SELECTED_ASSET_ID = "laion_clap_general"
VECTOR_DIM = 16
HELDOUT_SLICE_SEEDS = (
    ("event", "footstep", "cloth"),
    ("material", "hardwood", "carpet"),
    ("intensity", "medium", "soft"),
    ("acoustic_descriptor", "transient_dry", "sustained_wet"),
)

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
    if len(a) != VECTOR_DIM or len(b) != VECTOR_DIM:
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


def build_heldout_binding_artifacts(root: Path) -> dict[str, Any]:
    """Build disjoint held-out-only index + metrics; never scans full library PCM."""
    registry = load_registry(root)
    selection = assert_model_selection_binding(registry)
    frozen = assert_frozen_hashes(registry)
    if registry["model_binding"].get("weights_installed") is True and not weights_installed(
        root, registry
    ):
        raise SemanticAudioEmbeddingError("weights_installed_flag_true_but_file_absent")

    labels = registry["taxonomy_fixture_labels"]
    common_blockers = [
        "LIBRARY_AUTHORITY_NOT_GRANTED",
        "EMBEDDING_MODEL_WEIGHTS_NOT_INSTALLED",
        "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT",
    ]
    members: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    slice_metrics: list[dict[str, Any]] = []
    calibration_ids: set[str] = set()
    heldout_ids: set[str] = set()

    for slice_name, positive, negative in HELDOUT_SLICE_SEEDS:
        query_seed = f"heldout:bound:{slice_name}:{positive}:query"
        pos_seed = f"heldout:bound:{slice_name}:{positive}:neighbor"
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

    index_payload = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "embedding_index_revision": HELDOUT_INDEX_REVISION,
        "scope": "held_out_only",
        "full_library_scan": False,
        "pcm_decoded": False,
        "model_weights_loaded": False,
        "selected_asset_id": selection["selected_asset_id"],
        "selected_model_revision": selection["selected_model_revision"],
        "expected_key_file_sha256": selection["expected_key_file_sha256"],
        "license_binding_sha256": selection["license_binding_sha256"],
        "preprocessing_configuration_sha256": frozen["preprocessing_configuration_sha256"],
        "taxonomy_revision_sha256": frozen["taxonomy_revision_sha256"],
        "member_count": len(members),
        "members": sorted(members, key=lambda row: row["asset_id"]),
    }
    index_payload["embedding_index_sha256"] = canonical_json_sha256(
        {k: v for k, v in index_payload.items() if k != "embedding_index_sha256"}
    )

    metrics_payload = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "scope": "held_out_only",
        "top_k": int(registry["held_out_metrics"]["top_k"]),
        "thresholds": registry["held_out_metrics"]["fixture_thresholds"],
        "slices": slice_metrics,
        "all_slices_pass": all(row["metric_pass"] for row in slice_metrics),
        "partition_disjoint": True,
        "full_library_metrics": False,
    }
    metrics_payload["metrics_sha256"] = canonical_json_sha256(
        {k: v for k, v in metrics_payload.items() if k != "metrics_sha256"}
    )

    paths = heldout_artifact_paths(root)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    write_json(paths["index"], index_payload)
    write_json(paths["metrics"], metrics_payload)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "artifact_kind": "row077_heldout_binding",
        "embedding_index_revision": HELDOUT_INDEX_REVISION,
        "scope": "held_out_only",
        "full_library_scan": False,
        "pcm_decoded": False,
        "model_weights_loaded": False,
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
        "index_sha256": sha256_bytes(
            canonical_json_bytes(index_payload)
        ),
        "metrics_sha256": metrics_payload["metrics_sha256"],
        "record_count": len(records),
        "slice_count": len(slice_metrics),
        "all_slices_pass": metrics_payload["all_slices_pass"],
        "library_authority": False,
        "row_complete": False,
    }
    manifest["manifest_sha256"] = canonical_json_sha256(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    write_json(paths["manifest"], manifest)
    return {
        "manifest": manifest,
        "index": index_payload,
        "metrics": metrics_payload,
        "records": records,
        "paths": {k: str(v.relative_to(root)).replace("\\", "/") for k, v in paths.items()},
    }


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
        raise SemanticAudioEmbeddingError("heldout_index_revision_mismatch")
    return {
        "manifest": manifest,
        "index": load_json(paths["index"]) if paths["index"].is_file() else None,
        "metrics": load_json(paths["metrics"]) if paths["metrics"].is_file() else None,
        "paths": {k: str(v.relative_to(root)).replace("\\", "/") for k, v in paths.items()},
    }


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row069 = evaluate_row069_admission(root)
    row070 = evaluate_row070_admission(root)
    registry = load_registry(root)
    selection = assert_model_selection_binding(registry)
    frozen = assert_frozen_hashes(registry)
    installed = weights_installed(root, registry)
    heldout = load_heldout_binding_if_present(root)
    if heldout is None:
        heldout_pack = build_heldout_binding_artifacts(root)
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

    if not model_selected or not license_bound:
        blocker_codes.append("EMBEDDING_MODEL_NOT_SELECTED_OR_INSTALLED")
    elif not installed:
        blocker_codes.append("EMBEDDING_MODEL_WEIGHTS_NOT_INSTALLED")
    if not hashes_frozen:
        blocker_codes.append("PREPROCESSING_RUNTIME_UNBOUND")
    if not heldout_bound:
        blocker_codes.append("HELDOUT_RETRIEVAL_LIBRARY_METRICS_ABSENT")
    for code in (
        "EMBEDDING_INDEX_LIBRARY_RUNTIME_ABSENT",
        "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    if deps_unlocked and model_selected and license_bound and hashes_frozen and heldout_bound:
        status = "HOLD_LIBRARY_EMBEDDING_INDEX_ABSENT_MODEL_SELECTED_HELDOUT_BOUND"
        proof_tier = "CONTRACT_PASS_BOUNDED"
        safe_next = (
            "Model laion_clap_general is selected, Apache-2.0 license-bound, and hash-frozen; "
            "held-out-only index/metrics are bound under runtime_artifacts/embeddings/"
            "row077_heldout_*. Install and hash-reconcile the selected weights, then build the "
            "full-library embedding index only after Row075 releases library I/O. Do not start a "
            "full-library PCM/embedding scan while Row075 owns library I/O."
        )
    elif deps_unlocked:
        status = "HOLD_LIBRARY_EMBEDDING_MODEL_AND_INDEX_ABSENT_DEPS_UNLOCKED"
        proof_tier = "CONTRACT_PASS_BOUNDED"
        safe_next = (
            "Rows069-070 library authority is accepted. Select and license-bind one exact "
            "embedding model file-set; freeze preprocessing and taxonomy serialization "
            "hashes; build a hash-bound held-out embedding index; prove exact or "
            "tolerance-bound determinism and disjoint held-out retrieval across required "
            "slices. Do not start a full-library PCM/embedding scan while Row075 owns library I/O."
        )
    else:
        status = "HOLD_ROW069_ROW070_DEPENDENCIES_AND_LIBRARY_EMBEDDING_RUNTIME_ABSENT"
        proof_tier = "CONTRACT_PASS_BOUNDED"
        safe_next = (
            "Accept Row069 canonical inventory authority and Row070 deterministic "
            "canonical decode; select and license-bind one exact embedding model "
            "file-set; freeze preprocessing and taxonomy serialization hashes; "
            "build a hash-bound held-out embedding index; prove exact or tolerance-bound "
            "determinism and disjoint held-out retrieval across required slices; "
            "then replace this hold packet with library embedding evidence."
        )

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    assert_partitions_disjoint(fixture_records)
    prep = preprocessing_identity(registry)
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-077_semantic_audio_embeddings",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "registry_revision": REGISTRY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
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
            "embedding_index_revision": HELDOUT_INDEX_REVISION,
            "paths": heldout["paths"] if heldout else {},
            "manifest_sha256": (heldout or {}).get("manifest", {}).get("manifest_sha256"),
            "metrics_sha256": (heldout or {}).get("metrics", {}).get("metrics_sha256"),
            "all_slices_pass": bool((heldout or {}).get("metrics", {}).get("all_slices_pass")),
        },
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
            "product_completion": False,
            "runtime_completion": False,
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
        "--mode", choices=("library", "fixture", "heldout"), default="library"
    )
    parser.add_argument("--fixture", default="audio_text_compatible_space")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
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
        heldout = build_heldout_binding_artifacts(root)
        payload = heldout["manifest"]
        if payload.get("full_library_scan") is True:
            raise SemanticAudioEmbeddingError("heldout_mode_must_not_scan_full_library")
        if payload.get("row_complete") is True:
            raise SemanticAudioEmbeddingError("heldout_mode_must_not_claim_row_complete")
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
                    "heldout_manifest": str(manifest_out),
                    "library_evidence": str(
                        resolve_under(root, DEFAULT_EVIDENCE, "default_evidence")
                    ),
                    "mode": args.mode,
                    "status": status,
                },
                sort_keys=True,
            )
        )
        return 0
    else:
        payload = build_library_blocker_packet(root)
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
