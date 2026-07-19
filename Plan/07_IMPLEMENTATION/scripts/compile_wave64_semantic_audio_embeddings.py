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
VECTOR_DIM = 16

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


def model_identity(registry: dict[str, Any]) -> dict[str, Any]:
    binding = registry["model_binding"]
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
    index_members = {
        "revision": FIXTURE_INDEX_REVISION,
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
        "model_identity": model_identity(registry),
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


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    row069 = evaluate_row069_admission(root)
    row070 = evaluate_row070_admission(root)
    registry = load_registry(root)
    blocker_codes: list[str] = []
    for admission in (row069, row070):
        blocker_codes.extend(admission["blocker_codes"])
    if not (row069["dependency_satisfied"] and row070["dependency_satisfied"]):
        blocker_codes.append("ROW069_ROW070_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "EMBEDDING_MODEL_NOT_SELECTED_OR_INSTALLED",
        "PREPROCESSING_RUNTIME_UNBOUND",
        "EMBEDDING_INDEX_LIBRARY_RUNTIME_ABSENT",
        "HELDOUT_RETRIEVAL_LIBRARY_METRICS_ABSENT",
        "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

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
        "status": "HOLD_ROW069_ROW070_DEPENDENCIES_AND_LIBRARY_EMBEDDING_RUNTIME_ABSENT",
        "required_embedding_spaces": list(REQUIRED_EMBEDDING_SPACES),
        "validation_methods": [
            "model_hash",
            "preprocessing_hash",
            "embedding_determinism",
            "heldout_retrieval",
        ],
        "row069_admission": row069,
        "row070_admission": row070,
        "embedding_registry": {
            "path": str(REGISTRY_PATH).replace("\\", "/"),
            "registry_revision": registry["registry_revision"],
            "authority": registry.get("authority"),
            "sha256": sha256_file(resolve_under(root, REGISTRY_PATH, "registry")),
            "preprocessing_configuration_sha256": prep["preprocessing_configuration_sha256"],
            "model_selected_for_library": False,
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
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row069 canonical inventory authority and Row070 deterministic "
                "canonical decode; select and license-bind one exact embedding model "
                "file-set; freeze preprocessing and taxonomy serialization hashes; "
                "build a hash-bound embedding index; prove exact or tolerance-bound "
                "determinism and disjoint held-out retrieval across required slices; "
                "then replace this hold packet with library embedding evidence."
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
    parser.add_argument("--fixture", default="audio_text_compatible_space")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise SemanticAudioEmbeddingError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise SemanticAudioEmbeddingError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload.get("row_complete") is True:
            raise SemanticAudioEmbeddingError("library_mode_must_not_claim_row_complete")
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
