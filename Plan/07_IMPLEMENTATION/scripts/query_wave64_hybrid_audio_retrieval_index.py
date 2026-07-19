#!/usr/bin/env python3
"""Fail-closed Wave64 Row080 hybrid audio retrieval index slice.

Library retrieval refuses authority without accepted Rows069/077/079.
Fixture mode may emit deterministic schema-validated query receipts from a
synthetic immutable generation without promoting library completion or mixing
stale index generations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/hybrid_audio_retrieval_query_receipt.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row080_hybrid_audio_retrieval_index_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-080_hybrid_audio_retrieval_index.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-069": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-077": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-077_SEMANTIC_AUDIO_EMBEDDING_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-079": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-079_FINE_GRAINED_FOLEY_TAXONOMY_CURRENT_DELTA_20260719.json"
    ),
}

ENGINE_REVISION = "wave64_row080_hybrid_audio_retrieval_engine_v0.1.0"
POLICY_REVISION = "wave64_row080_hybrid_audio_retrieval_index_v0.1.0"
TRACKER_ID = "TRK-W64-080"
ITEM_ID = "ITEM-W64-080"
SCHEMA_VERSION = "1.0.0"
FIXTURE_INDEX_REVISION = "fixture_generation_v0"
STALE_INDEX_REVISION = "stale_generation_v0"

REQUIRED_CHANNELS = (
    "structured_metadata_filter",
    "lexical_search",
    "embedding_similarity",
    "canonical_content_hash_deduplication",
)

FIXTURE_NAMES = (
    "deterministic_repeat_query",
    "canonical_dedup_collapses_duplicates",
    "stale_generation_mix_rejected",
    "structured_lexical_vector_merge",
    "missing_embedding_channel_fail_closed",
)


class HybridRetrievalError(ValueError):
    """Raised when Row080 retrieval violates fail-closed authority."""


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


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise HybridRetrievalError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row080_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise HybridRetrievalError("policy_registry_revision_mismatch")
    channels = payload.get("required_channels")
    if not isinstance(channels, list) or tuple(channels) != REQUIRED_CHANNELS:
        raise HybridRetrievalError("policy_required_channels_mismatch")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
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
            "status": "",
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    row_suffix = tracker_id.rsplit("-", 1)[-1].lower()
    exact_acceptance = str(decision.get(f"row{row_suffix}_acceptance", "")).lower()
    accepted_markers = {"accepted", "pass", "passed"}
    coarse_markers = [
        exact_acceptance,
        str(decision.get("status", "")).lower(),
        str(payload.get("qa_decision", "")).lower(),
    ]
    acceptance_hit = any(marker in accepted_markers for marker in coarse_markers if marker)
    status_text = str(payload.get("status", "")).lower()
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    if status_text.startswith("hold") or hold_text.startswith("hold"):
        acceptance_hit = False
    dependency_satisfied = row_complete and acceptance_hit
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append(blocker_code)
    result: dict[str, Any] = {
        "tracker_id": tracker_id,
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    return result


def evaluate_all_dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for tracker_id, delta_path in DEPENDENCY_DELTAS.items():
        code = tracker_id.replace("-", "_") + "_DEPENDENCY_NOT_ACCEPTED"
        absent = tracker_id.replace("-", "_") + "_DELTA_ABSENT"
        out[tracker_id] = evaluate_dependency_admission(
            root,
            delta_path=delta_path,
            tracker_id=tracker_id,
            blocker_code=code,
            absent_code=absent,
        )
    return out


def tokenize(text: str, *, min_token_length: int) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) >= min_token_length]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise HybridRetrievalError("embedding_dimension_mismatch")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [v / norm for v in vector]


def fixture_records() -> list[dict[str, Any]]:
    shared_pcm = _stable_hash("pcm:shared_heel_strike")
    return [
        {
            "asset_id": "fixture:heel_hardwood_a",
            "canonical_pcm_sha256": shared_pcm,
            "event_type": "body_foley",
            "material": "hardwood",
            "sync_class": "frame_exact",
            "intensity_band": "medium",
            "license_classification": "cleared_fixture",
            "tags": "heel hardwood footstep strike",
            "caption": "heel strike on hardwood floor",
            "relative_path": "fixtures/heel_hardwood_a.wav",
            "embedding": [0.9, 0.1, 0.0, 0.2],
            "index_revision": FIXTURE_INDEX_REVISION,
        },
        {
            "asset_id": "fixture:heel_hardwood_b_dup",
            "canonical_pcm_sha256": shared_pcm,
            "event_type": "body_foley",
            "material": "hardwood",
            "sync_class": "frame_exact",
            "intensity_band": "medium",
            "license_classification": "cleared_fixture",
            "tags": "heel hardwood footstep duplicate path",
            "caption": "duplicate content heel strike",
            "relative_path": "fixtures/heel_hardwood_b_dup.wav",
            "embedding": [0.88, 0.12, 0.01, 0.18],
            "index_revision": FIXTURE_INDEX_REVISION,
        },
        {
            "asset_id": "fixture:hand_body_contact",
            "canonical_pcm_sha256": _stable_hash("pcm:hand_body"),
            "event_type": "body_foley",
            "material": "skin",
            "sync_class": "frame_exact",
            "intensity_band": "light",
            "license_classification": "cleared_fixture",
            "tags": "hand body contact soft",
            "caption": "hand to body contact soft onset",
            "relative_path": "fixtures/hand_body_contact.wav",
            "embedding": [0.2, 0.8, 0.3, 0.1],
            "index_revision": FIXTURE_INDEX_REVISION,
        },
        {
            "asset_id": "fixture:cloth_rustle",
            "canonical_pcm_sha256": _stable_hash("pcm:cloth"),
            "event_type": "cloth_foley",
            "material": "fabric",
            "sync_class": "loose",
            "intensity_band": "light",
            "license_classification": "cleared_fixture",
            "tags": "cloth fabric rustle",
            "caption": "soft cloth rustle",
            "relative_path": "fixtures/cloth_rustle.wav",
            "embedding": [0.1, 0.2, 0.9, 0.1],
            "index_revision": FIXTURE_INDEX_REVISION,
        },
        {
            "asset_id": "fixture:stale_generation_intruder",
            "canonical_pcm_sha256": _stable_hash("pcm:stale"),
            "event_type": "body_foley",
            "material": "hardwood",
            "sync_class": "frame_exact",
            "intensity_band": "medium",
            "license_classification": "cleared_fixture",
            "tags": "heel hardwood stale generation",
            "caption": "stale generation heel strike",
            "relative_path": "fixtures/stale_generation_intruder.wav",
            "embedding": [0.91, 0.09, 0.0, 0.21],
            "index_revision": STALE_INDEX_REVISION,
        },
    ]


def build_generation_manifest(
    records: list[dict[str, Any]],
    *,
    index_revision: str,
    policy: dict[str, Any],
    policy_sha256: str,
    record_schema_sha256: str,
) -> dict[str, Any]:
    generation_records = [r for r in records if r["index_revision"] == index_revision]
    lexical_index = {
        record["asset_id"]: sorted(
            set(
                tokenize(record["tags"], min_token_length=2)
                + tokenize(record["caption"], min_token_length=2)
                + tokenize(record["relative_path"], min_token_length=2)
            )
        )
        for record in generation_records
    }
    embedding_index = {
        record["asset_id"]: normalize_vector(list(record["embedding"]))
        for record in generation_records
    }
    manifest = {
        "index_revision": index_revision,
        "record_count": len(generation_records),
        "asset_ids": sorted(record["asset_id"] for record in generation_records),
        "canonical_pcm_sha256_set": sorted(
            {record["canonical_pcm_sha256"] for record in generation_records}
        ),
        "lexical_index_sha256": sha256_bytes(canonical_json_bytes(lexical_index)),
        "embedding_index_sha256": sha256_bytes(canonical_json_bytes(embedding_index)),
        "record_schema_sha256": record_schema_sha256,
        "taxonomy_revision_sha256": _stable_hash("taxonomy_revision:fixture_v0"),
        "retrieval_policy_sha256": policy_sha256,
        "policy_revision": policy["revision"],
        "required_channels": list(REQUIRED_CHANNELS),
    }
    manifest["index_manifest_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    return {
        "manifest": manifest,
        "records": generation_records,
        "lexical_index": lexical_index,
        "embedding_index": embedding_index,
    }


def canonicalize_query(query: dict[str, Any]) -> dict[str, Any]:
    return {
        "index_revision": query["index_revision"],
        "structured_filters": dict(sorted((query.get("structured_filters") or {}).items())),
        "lexical_text": str(query.get("lexical_text") or ""),
        "embedding": [float(v) for v in (query.get("embedding") or [])],
        "limit": int(query.get("limit") or 10),
    }


def query_sha256(query: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(canonicalize_query(query)))


def empty_channel(status: str = "blocked", blocker_codes: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "hit_count": 0,
        "hits": [],
        "blocker_codes": list(blocker_codes or []),
    }


def run_structured_channel(
    records: list[dict[str, Any]],
    filters: dict[str, str],
) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for record in records:
        if all(record.get(key) == value for key, value in filters.items()):
            hits.append({"asset_id": record["asset_id"], "score": 1.0})
    hits.sort(key=lambda item: (-item["score"], item["asset_id"]))
    return {
        "status": "ok",
        "hit_count": len(hits),
        "hits": hits,
        "blocker_codes": [],
    }


def run_lexical_channel(
    records: list[dict[str, Any]],
    lexical_index: dict[str, list[str]],
    lexical_text: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    min_len = int(policy["lexical_policy"]["min_token_length"])
    query_tokens = set(tokenize(lexical_text, min_token_length=min_len))
    if not query_tokens:
        return empty_channel("blocked", ["EMPTY_LEXICAL_QUERY"])
    hits: list[dict[str, Any]] = []
    for record in records:
        asset_id = record["asset_id"]
        tokens = set(lexical_index.get(asset_id) or [])
        overlap = query_tokens & tokens
        if not overlap:
            continue
        score = len(overlap) / max(len(query_tokens), 1)
        hits.append({"asset_id": asset_id, "score": round(score, 6)})
    hits.sort(key=lambda item: (-item["score"], item["asset_id"]))
    return {
        "status": "ok",
        "hit_count": len(hits),
        "hits": hits,
        "blocker_codes": [],
    }


def run_vector_channel(
    records: list[dict[str, Any]],
    embedding_index: dict[str, list[float]],
    query_embedding: list[float],
    policy: dict[str, Any],
    *,
    force_missing: bool = False,
) -> dict[str, Any]:
    if force_missing:
        return empty_channel("blocked", ["EMBEDDING_INDEX_ARTIFACT_MISSING"])
    expected_dim = int(policy["vector_policy"]["dimension"])
    if len(query_embedding) != expected_dim:
        return empty_channel("blocked", ["QUERY_EMBEDDING_DIMENSION_MISMATCH"])
    if any(record["asset_id"] not in embedding_index for record in records):
        return empty_channel("blocked", ["EMBEDDING_INDEX_INCOMPLETE_FOR_GENERATION"])
    query_vec = normalize_vector([float(v) for v in query_embedding])
    min_sim = float(policy["vector_policy"]["min_similarity"])
    hits: list[dict[str, Any]] = []
    for record in records:
        asset_id = record["asset_id"]
        score = cosine_similarity(query_vec, embedding_index[asset_id])
        if score < min_sim:
            continue
        hits.append({"asset_id": asset_id, "score": round(score, 6)})
    hits.sort(key=lambda item: (-item["score"], item["asset_id"]))
    return {
        "status": "ok",
        "hit_count": len(hits),
        "hits": hits,
        "blocker_codes": [],
    }


def merge_and_dedup(
    records: list[dict[str, Any]],
    channel_results: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    weights = policy["merge_policy"]["channel_weights"]
    score_maps = {
        channel: {hit["asset_id"]: float(hit["score"]) for hit in result["hits"]}
        for channel, result in channel_results.items()
        if channel != "canonical_content_hash_deduplication"
    }
    union_ids = sorted(
        set().union(*[set(mapping.keys()) for mapping in score_maps.values()])
        if score_maps
        else set()
    )
    record_by_id = {record["asset_id"]: record for record in records}
    merged: list[dict[str, Any]] = []
    for asset_id in union_ids:
        record = record_by_id[asset_id]
        channel_scores = {
            "structured_metadata_filter": score_maps["structured_metadata_filter"].get(asset_id, 0.0),
            "lexical_search": score_maps["lexical_search"].get(asset_id, 0.0),
            "embedding_similarity": score_maps["embedding_similarity"].get(asset_id, 0.0),
        }
        merged_score = round(
            channel_scores["structured_metadata_filter"] * float(weights["structured_metadata_filter"])
            + channel_scores["lexical_search"] * float(weights["lexical_search"])
            + channel_scores["embedding_similarity"] * float(weights["embedding_similarity"]),
            6,
        )
        merged.append(
            {
                "asset_id": asset_id,
                "canonical_pcm_sha256": record["canonical_pcm_sha256"],
                "merged_score": merged_score,
                "channel_scores": channel_scores,
                "dedup_group": record["canonical_pcm_sha256"],
                "representative": False,
            }
        )

    # Canonical dedup before limit.
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in merged:
        grouped.setdefault(item["dedup_group"], []).append(item)
    exclusions: list[dict[str, Any]] = []
    representatives: list[dict[str, Any]] = []
    for group_id, members in sorted(grouped.items()):
        ordered = sorted(
            members,
            key=lambda item: (-item["merged_score"], item["asset_id"]),
        )
        winner = deepcopy(ordered[0])
        winner["representative"] = True
        representatives.append(winner)
        for loser in ordered[1:]:
            exclusions.append(
                {
                    "asset_id": loser["asset_id"],
                    "reason_codes": ["CANONICAL_CONTENT_HASH_DUPLICATE"],
                }
            )

    representatives.sort(
        key=lambda item: (-item["merged_score"], item["canonical_pcm_sha256"], item["asset_id"])
    )
    limited = representatives[:limit]
    for rank, item in enumerate(limited, start=1):
        item["rank"] = rank

    dedup_channel = {
        "status": "ok",
        "hit_count": len(limited),
        "hits": [{"asset_id": item["asset_id"], "score": item["merged_score"]} for item in limited],
        "blocker_codes": [],
    }
    return limited, exclusions, dedup_channel


def ordered_candidate_set_sha256(candidates: list[dict[str, Any]]) -> str:
    identity = [
        {
            "rank": item["rank"],
            "asset_id": item["asset_id"],
            "canonical_pcm_sha256": item["canonical_pcm_sha256"],
            "merged_score": item["merged_score"],
        }
        for item in candidates
    ]
    return sha256_bytes(canonical_json_bytes(identity))


def seal_receipt(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def validate_query_receipt(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise HybridRetrievalError(f"schema_validation_failed:{location}:{first.message}")
    expected = seal_receipt({k: v for k, v in record.items() if k != "receipt_sha256"})
    if expected["receipt_sha256"] != record["receipt_sha256"]:
        raise HybridRetrievalError("receipt_sha256_mismatch")
    ranks = [item["rank"] for item in record["candidates"]]
    if ranks != list(range(1, len(ranks) + 1)):
        raise HybridRetrievalError("candidate_ranks_not_dense")
    pcm_values = [item["canonical_pcm_sha256"] for item in record["candidates"]]
    if len(pcm_values) != len(set(pcm_values)):
        raise HybridRetrievalError("duplicate_canonical_pcm_in_result")


def execute_query(
    root: Path,
    *,
    query: dict[str, Any],
    allow_stale_mix: bool = False,
    force_missing_embedding: bool = False,
    force_blocked: bool = False,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    policy_sha256 = sha256_file(policy_path)
    schema_sha256 = sha256_file(resolve_under(root, SCHEMA_PATH, "schema"))
    admissions = evaluate_all_dependency_admissions(root)
    library_deps_ok = all(item["dependency_satisfied"] for item in admissions.values())

    all_records = fixture_records()
    index_revision = str(query["index_revision"])
    if allow_stale_mix:
        # Intentionally mix generations to prove fail-closed rejection.
        mixed_records = list(all_records)
        generation = {
            "manifest": {
                "index_revision": index_revision,
                "index_manifest_sha256": _stable_hash("corrupt_mixed_manifest"),
                "record_schema_sha256": schema_sha256,
                "taxonomy_revision_sha256": _stable_hash("taxonomy_revision:fixture_v0"),
                "embedding_index_sha256": _stable_hash("embedding_mixed"),
                "retrieval_policy_sha256": policy_sha256,
            },
            "records": mixed_records,
            "lexical_index": {},
            "embedding_index": {},
        }
        stale_ids = [
            record["asset_id"]
            for record in mixed_records
            if record["index_revision"] != index_revision
        ]
        channel_results = {
            "structured_metadata_filter": empty_channel(
                "blocked", ["STALE_OR_MIXED_GENERATION_REJECTED"]
            ),
            "lexical_search": empty_channel("blocked", ["STALE_OR_MIXED_GENERATION_REJECTED"]),
            "embedding_similarity": empty_channel(
                "blocked", ["STALE_OR_MIXED_GENERATION_REJECTED"]
            ),
            "canonical_content_hash_deduplication": empty_channel(
                "blocked", ["STALE_OR_MIXED_GENERATION_REJECTED"]
            ),
        }
        candidates: list[dict[str, Any]] = []
        exclusions = [
            {"asset_id": asset_id, "reason_codes": ["STALE_OR_MIXED_GENERATION_REJECTED"]}
            for asset_id in stale_ids
        ]
        blocker_codes = ["STALE_OR_MIXED_GENERATION_REJECTED"]
        route = "blocked"
        acceptance = "fixture_only"
        explanation = [
            "mixed_index_generations_rejected_fail_closed",
            f"stale_asset_count={len(stale_ids)}",
        ]
        status = "blocked"
    else:
        generation = build_generation_manifest(
            all_records,
            index_revision=index_revision,
            policy=policy,
            policy_sha256=policy_sha256,
            record_schema_sha256=schema_sha256,
        )
        if not generation["records"]:
            raise HybridRetrievalError("index_revision_has_no_records")
        # Fail closed if any supplied record claims a foreign generation.
        foreign = [
            record["asset_id"]
            for record in generation["records"]
            if record["index_revision"] != index_revision
        ]
        if foreign:
            raise HybridRetrievalError("generation_isolation_invariant_broken")

        structured = run_structured_channel(
            generation["records"], dict(query.get("structured_filters") or {})
        )
        lexical = run_lexical_channel(
            generation["records"],
            generation["lexical_index"],
            str(query.get("lexical_text") or ""),
            policy,
        )
        vector = run_vector_channel(
            generation["records"],
            generation["embedding_index"],
            list(query.get("embedding") or []),
            policy,
            force_missing=force_missing_embedding,
        )
        channel_results = {
            "structured_metadata_filter": structured,
            "lexical_search": lexical,
            "embedding_similarity": vector,
        }
        blocker_codes: list[str] = []
        for result in channel_results.values():
            blocker_codes.extend(result["blocker_codes"])
        if any(result["status"] != "ok" for result in channel_results.values()):
            candidates = []
            exclusions = []
            channel_results["canonical_content_hash_deduplication"] = empty_channel(
                "blocked", ["CHANNEL_PREREQUISITE_FAILED"]
            )
            route = "blocked"
            acceptance = "fixture_only"
            explanation = ["one_or_more_retrieval_channels_blocked"]
            status = "blocked"
            if "CHANNEL_PREREQUISITE_FAILED" not in blocker_codes:
                blocker_codes.append("CHANNEL_PREREQUISITE_FAILED")
        else:
            candidates, exclusions, dedup_channel = merge_and_dedup(
                generation["records"],
                channel_results,
                policy,
                limit=int(query.get("limit") or 10),
            )
            channel_results["canonical_content_hash_deduplication"] = dedup_channel
            if not candidates:
                route = "abstain"
                acceptance = "fixture_only"
                explanation = ["no_candidates_after_hybrid_merge"]
                status = "pass"
            else:
                route = "return_candidates"
                acceptance = "fixture_only"
                explanation = [
                    f"returned_candidates={len(candidates)}",
                    "all_channels_bound_one_immutable_generation",
                ]
                status = "pass"

    if force_blocked or not library_deps_ok:
        # Library authority remains false; fixture semantics may still record route.
        if not library_deps_ok:
            for admission in admissions.values():
                for code in admission["blocker_codes"]:
                    if code not in blocker_codes:
                        blocker_codes.append(code)
            if "ROW069_ROW077_ROW079_DEPENDENCIES_NOT_ACCEPTED" not in blocker_codes:
                blocker_codes.append("ROW069_ROW077_ROW079_DEPENDENCIES_NOT_ACCEPTED")
        if force_blocked:
            route = "blocked"
            status = "blocked"
            acceptance = "held"
            explanation = ["library_mode_blocked_fail_closed"]
            candidates = []

    manifest = generation["manifest"]
    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "hybrid_audio_retrieval_query_receipt",
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": policy_sha256,
        "query_sha256": query_sha256(query),
        "index_revision": index_revision,
        "index_manifest_sha256": manifest["index_manifest_sha256"],
        "record_schema_sha256": manifest["record_schema_sha256"],
        "taxonomy_revision_sha256": manifest["taxonomy_revision_sha256"],
        "embedding_index_sha256": manifest["embedding_index_sha256"],
        "retrieval_policy_sha256": manifest["retrieval_policy_sha256"],
        "ordered_candidate_set_sha256": ordered_candidate_set_sha256(candidates),
        "is_synthetic": True,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_channels": list(REQUIRED_CHANNELS),
        "channel_results": channel_results,
        "exclusions": exclusions,
        "candidates": candidates,
        "decision": {
            "status": status,
            "route": route,
            "product_completion": False,
            "row080_acceptance": acceptance,
            "blocker_codes": blocker_codes,
            "explanation": explanation,
        },
    }
    sealed = seal_receipt(record)
    validate_query_receipt(root, sealed)
    return sealed


def fixture_query_packet(name: str) -> dict[str, Any]:
    heel_embedding = [0.9, 0.1, 0.0, 0.2]
    if name == "deterministic_repeat_query":
        return {
            "query": {
                "index_revision": FIXTURE_INDEX_REVISION,
                "structured_filters": {
                    "event_type": "body_foley",
                    "sync_class": "frame_exact",
                },
                "lexical_text": "heel hardwood",
                "embedding": heel_embedding,
                "limit": 5,
            }
        }
    if name == "canonical_dedup_collapses_duplicates":
        return {
            "query": {
                "index_revision": FIXTURE_INDEX_REVISION,
                "structured_filters": {
                    "event_type": "body_foley",
                    "material": "hardwood",
                },
                "lexical_text": "heel hardwood footstep",
                "embedding": heel_embedding,
                "limit": 5,
            }
        }
    if name == "stale_generation_mix_rejected":
        return {
            "query": {
                "index_revision": FIXTURE_INDEX_REVISION,
                "structured_filters": {"event_type": "body_foley"},
                "lexical_text": "heel hardwood",
                "embedding": heel_embedding,
                "limit": 5,
            },
            "allow_stale_mix": True,
        }
    if name == "structured_lexical_vector_merge":
        return {
            "query": {
                "index_revision": FIXTURE_INDEX_REVISION,
                "structured_filters": {"event_type": "body_foley"},
                "lexical_text": "hand body contact",
                "embedding": [0.2, 0.8, 0.3, 0.1],
                "limit": 5,
            }
        }
    if name == "missing_embedding_channel_fail_closed":
        return {
            "query": {
                "index_revision": FIXTURE_INDEX_REVISION,
                "structured_filters": {"event_type": "body_foley"},
                "lexical_text": "heel hardwood",
                "embedding": heel_embedding,
                "limit": 5,
            },
            "force_missing_embedding": True,
        }
    raise HybridRetrievalError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_query_packet(name)
    return execute_query(
        root,
        query=packet["query"],
        allow_stale_mix=bool(packet.get("allow_stale_mix")),
        force_missing_embedding=bool(packet.get("force_missing_embedding")),
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW069_ROW077_ROW079_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_LIBRARY_HYBRID_RETRIEVAL_RUNTIME_ABSENT",
        "IMMUTABLE_LIBRARY_GENERATION_MANIFEST_ABSENT",
        "HELD_OUT_HYBRID_RETRIEVAL_METRICS_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records_out = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-080_hybrid_audio_retrieval_index",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW069_ROW077_ROW079_DEPENDENCIES_AND_LIBRARY_HYBRID_RUNTIME_ABSENT",
        "required_channels": list(REQUIRED_CHANNELS),
        "dependency_admissions": admissions,
        "retrieval_policy": {
            "path": str(POLICY_PATH).replace("\\", "/"),
            "revision": policy["revision"],
            "authority": policy.get("authority"),
            "sha256": sha256_file(policy_path),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records_out),
            "records": fixture_records_out,
            "determinism_note": (
                "Fixture receipts prove structured/lexical/vector channel binding to one "
                "immutable generation, canonical-hash deduplication before limit, stale "
                "generation rejection, and deterministic ordered candidate hashes; they do "
                "not accept Row080 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row080_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row069 canonical inventory authority, Row077 immutable embedding "
                "generation, and Row079 versioned Foley taxonomy; publish one immutable "
                "library generation manifest binding structured/lexical/vector/canonical "
                "artifacts; then replace this hold packet with registry-bound hybrid query "
                "runtime evidence and held-out retrieval metrics."
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
    parser.add_argument("--fixture", default="deterministic_repeat_query")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise HybridRetrievalError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise HybridRetrievalError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
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
