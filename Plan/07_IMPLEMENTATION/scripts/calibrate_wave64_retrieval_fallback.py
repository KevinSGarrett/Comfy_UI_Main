#!/usr/bin/env python3
"""Fail-closed Wave64 Row083 retrieval fallback calibration slice.

Library calibration refuses authority without accepted Rows081/082.
Fixture mode may emit deterministic schema-validated calibration receipts from
synthetic event-family metrics without promoting library completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_retrieval_fallback_calibration_record.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row083_retrieval_fallback_calibration_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-083_retrieval_fallback_calibration.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-081": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-081_EXPLAINABLE_AUDIO_CANDIDATE_SCORING_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-082": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-082_REPETITION_DIVERSITY_CONTINUITY_CURRENT_DELTA_20260719.json"
    ),
}

CALIBRATOR_REVISION = "wave64_row083_retrieval_fallback_calibrator_v0.1.0"
POLICY_REVISION = "wave64_row083_retrieval_fallback_calibration_policy_v0.1.0"
CALIBRATION_REVISION = "wave64_row083_synthetic_calibration_v0.1.0"
METRIC_TABLE_REVISION = "wave64_row083_synthetic_event_family_metrics_v0.1.0"
TRACKER_ID = "TRK-W64-083"
ITEM_ID = "ITEM-W64-083"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "confidence_calibration",
    "precision_recall",
    "false_match_rate",
    "fallback_threshold",
    "abstention",
)

REQUIRED_ROUTES = (
    "exact_retrieval",
    "approximate_retrieval",
    "layered_synthesis",
    "generated_fallback",
    "abstain",
    "review_escalation",
)

HARD_EXCLUSION_ORDER = (
    "MISSING_METRIC_TABLE",
    "STALE_CALIBRATION_REVISION",
    "NON_FINITE_CONFIDENCE",
    "SPARSE_EVENT_FAMILY",
    "FALSE_MATCH_CONSTRAINT_BREACH",
    "BELOW_ROUTE_THRESHOLD",
    "RELEVANCE_ROUTE_MISMATCH",
    "NO_CANDIDATES",
    "DEPENDENCY_EVIDENCE_ABSENT",
)

FIXTURE_NAMES = (
    "high_confidence_exact_selects_exact",
    "below_exact_routes_to_approximate",
    "low_confidence_abstains_not_silent_select",
    "no_candidates_fails_closed",
    "sparse_family_fails_closed",
    "missing_metric_table_fails_closed",
    "generated_fallback_under_calibrated_band",
)


class RetrievalFallbackError(ValueError):
    """Raised when Row083 calibration violates fail-closed authority."""


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
        raise RetrievalFallbackError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise RetrievalFallbackError("non_finite_score_value")
    return round(float(value), digits)


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row083_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise RetrievalFallbackError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise RetrievalFallbackError("policy_required_gates_mismatch")
    if tuple(payload.get("required_routes") or ()) != REQUIRED_ROUTES:
        raise RetrievalFallbackError("policy_required_routes_mismatch")
    if payload.get("calibration_revision") != CALIBRATION_REVISION:
        raise RetrievalFallbackError("policy_calibration_revision_mismatch")
    if payload.get("metric_table_revision") != METRIC_TABLE_REVISION:
        raise RetrievalFallbackError("policy_metric_table_revision_mismatch")
    return payload


def metric_table_sha256(policy: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(policy.get("event_family_metrics") or {}))


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
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    row_suffix = tracker_id.rsplit("-", 1)[-1].lower()
    exact_acceptance = str(decision.get(f"row{row_suffix}_acceptance", "")).lower()
    coarse_markers = [
        exact_acceptance,
        str(decision.get("status", "")).lower(),
        str(payload.get("qa_decision", "")).lower(),
    ]
    accepted_markers = {"accepted", "pass", "passed"}
    acceptance_hit = any(marker in accepted_markers for marker in coarse_markers if marker)
    status_text = str(payload.get("status", "")).lower()
    hold_decision = str(payload.get("hold_decision", {}).get("decision", "")).lower()
    if status_text.startswith("hold") or hold_decision.startswith("hold"):
        acceptance_hit = False
    qa_decision = str(payload.get("qa_decision", "")).lower()
    if "hold" in qa_decision:
        acceptance_hit = False
    dependency_satisfied = row_complete and acceptance_hit
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


def calibrate_confidence(raw: float) -> float:
    """Monotone synthetic calibration map for fixture authority only."""
    if not math.isfinite(raw):
        raise RetrievalFallbackError("non_finite_confidence")
    clamped = min(1.0, max(0.0, float(raw)))
    # Mild under-confidence correction that preserves order.
    return round_finite(clamped * 0.97 + 0.01)


def choose_route(
    *,
    calibrated: float,
    relevance: str | None,
    metrics: dict[str, Any] | None,
    policy: dict[str, Any],
    force_missing_metrics: bool,
    semantic_disagreement: bool,
) -> tuple[str, list[str], str]:
    explanation: list[str] = []
    exclusions: list[str] = []

    if force_missing_metrics or metrics is None:
        exclusions.append("MISSING_METRIC_TABLE")
        explanation.append("missing_metric_table")
        return "blocked", exclusions, "missing_metric_table"

    support = int(metrics.get("support_count", 0))
    min_support = int(policy["support_policy"]["min_event_family_support"])
    if support < min_support:
        exclusions.append("SPARSE_EVENT_FAMILY")
        explanation.append(f"sparse_support={support}<{min_support}")
        return "review_escalation", exclusions, "sparse_event_family"

    if semantic_disagreement:
        explanation.append("semantic_disagreement")
        return "review_escalation", exclusions, "semantic_disagreement"

    thresholds = policy["route_thresholds"]
    fmr = float(metrics.get("false_match_rate", 1.0))

    def _try(route: str) -> bool:
        cfg = thresholds[route]
        if calibrated < float(cfg["min_calibrated_confidence"]):
            return False
        if relevance not in cfg["allowed_relevance"]:
            return False
        if fmr > float(cfg["max_false_match_rate"]):
            return False
        return True

    for route in (
        "exact_retrieval",
        "approximate_retrieval",
        "layered_synthesis",
        "generated_fallback",
    ):
        if _try(route):
            explanation.append(
                f"route={route};calibrated={calibrated};relevance={relevance};fmr={fmr}"
            )
            return route, exclusions, f"calibrated_route_{route}"

    if relevance is not None and calibrated < float(
        thresholds["generated_fallback"]["min_calibrated_confidence"]
    ):
        exclusions.append("BELOW_ROUTE_THRESHOLD")
        explanation.append("low_confidence_cannot_silently_select")
        return "abstain", exclusions, "low_confidence_abstain"

    if fmr > float(thresholds["generated_fallback"]["max_false_match_rate"]):
        exclusions.append("FALSE_MATCH_CONSTRAINT_BREACH")
        explanation.append("false_match_constraint_breach")
        return "review_escalation", exclusions, "false_match_constraint_breach"

    if relevance is not None:
        exclusions.append("RELEVANCE_ROUTE_MISMATCH")
        explanation.append("relevance_route_mismatch")
        return "abstain", exclusions, "relevance_route_mismatch"

    exclusions.append("NO_CANDIDATES")
    explanation.append("no_candidates")
    return "abstain", exclusions, "no_candidates"


def score_candidates(
    candidates: list[dict[str, Any]],
    *,
    route: str,
    exclusions: list[str],
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        cand_exclusions = list(exclusions)
        relevance = str(candidate["relevance"])
        route_allows = {
            "exact_retrieval": {"exact"},
            "approximate_retrieval": {"exact", "approximate"},
            "layered_synthesis": {"exact", "approximate", "layered"},
            "generated_fallback": {"exact", "approximate", "layered", "generated"},
        }
        if route in route_allows and relevance not in route_allows[route]:
            cand_exclusions.append("RELEVANCE_ROUTE_MISMATCH")
        if route in {"abstain", "review_escalation", "blocked"}:
            # Non-selecting routes keep candidates for explanation but mark ineligible.
            if "BELOW_ROUTE_THRESHOLD" not in cand_exclusions and exclusions:
                pass
            if not cand_exclusions:
                cand_exclusions.append("BELOW_ROUTE_THRESHOLD")
        ordered = [code for code in HARD_EXCLUSION_ORDER if code in cand_exclusions]
        eligible = route in route_allows and len(ordered) == 0
        scored.append(
            {
                "candidate_id": str(candidate["candidate_id"]),
                "asset_sha256": str(candidate["asset_sha256"]),
                "relevance": relevance,
                "eligible": eligible,
                "hard_exclusions": ordered,
                "rank": index,
                "explanation": [
                    f"relevance={relevance}",
                    f"route={route}",
                    f"eligible={eligible}",
                    f"hard_filters={ordered or ['none']}",
                ],
            }
        )
    # Re-rank: eligible first by original order, then ineligible.
    eligible = [item for item in scored if item["eligible"]]
    ineligible = [item for item in scored if not item["eligible"]]
    ordered_all = eligible + ineligible
    for index, item in enumerate(ordered_all, start=1):
        item["rank"] = index
    return ordered_all


def validate_calibration_semantics(record: dict[str, Any]) -> None:
    if record.get("library_authority") is True:
        raise RetrievalFallbackError("library_authority_forbidden_in_this_slice")
    decision = record.get("decision") or {}
    if decision.get("product_completion") is True:
        raise RetrievalFallbackError("product_completion_forbidden_in_this_slice")
    route = decision.get("route")
    selected = decision.get("selected_candidate_id")
    candidates = record.get("candidates") or []
    by_id = {item["candidate_id"]: item for item in candidates}
    if route in {
        "exact_retrieval",
        "approximate_retrieval",
        "layered_synthesis",
        "generated_fallback",
    }:
        if selected is None or selected not in by_id:
            raise RetrievalFallbackError("selected_candidate_missing")
        chosen = by_id[selected]
        if chosen.get("eligible") is not True:
            raise RetrievalFallbackError("selected_candidate_ineligible")
        if int(chosen["rank"]) != 1:
            raise RetrievalFallbackError("selected_candidate_not_rank_one")
        relevance = chosen.get("relevance")
        if route == "exact_retrieval" and relevance != "exact":
            raise RetrievalFallbackError("exact_route_requires_exact_relevance")
    elif route in {"abstain", "review_escalation", "blocked"}:
        if selected is not None:
            raise RetrievalFallbackError("non_select_route_must_null_selection")
    else:
        raise RetrievalFallbackError("unknown_decision_route")
    for item in candidates:
        exclusions = item.get("hard_exclusions") or []
        if item.get("eligible") is True and exclusions:
            raise RetrievalFallbackError("eligible_with_hard_exclusions")
        if item.get("eligible") is False and not exclusions:
            raise RetrievalFallbackError("ineligible_without_hard_exclusions")
    ranks = [item.get("rank") for item in candidates]
    if candidates and len(ranks) != len(set(ranks)):
        raise RetrievalFallbackError("duplicate_rank")
    if not math.isfinite(float(record.get("raw_confidence", float("nan")))):
        raise RetrievalFallbackError("non_finite_raw_confidence")
    if not math.isfinite(float(record.get("calibrated_confidence", float("nan")))):
        raise RetrievalFallbackError("non_finite_calibrated_confidence")
    if not record.get("metric_table_sha256"):
        raise RetrievalFallbackError("metric_table_sha256_missing")
    if not record.get("calibration_revision"):
        raise RetrievalFallbackError("calibration_revision_missing")


def validate_calibration_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_calibration_semantics(record)


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def build_calibration_record(
    root: Path,
    *,
    packet: dict[str, Any],
    is_synthetic: bool,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    raw = float(packet["raw_confidence"])
    if not math.isfinite(raw):
        raise RetrievalFallbackError("non_finite_confidence")
    calibrated = calibrate_confidence(raw)
    force_missing = bool(packet.get("force_missing_metrics", False))
    event_family = str(packet["event_family"])
    metrics = None if force_missing else deepcopy(
        (policy.get("event_family_metrics") or {}).get(event_family)
    )
    if metrics is None and not force_missing:
        # Unknown family treated as missing metrics for fail-closed behavior.
        force_missing = True

    candidates_in = list(packet.get("candidates") or [])
    if not candidates_in and not force_missing:
        route, exclusions, reason = choose_route(
            calibrated=calibrated,
            relevance=None,
            metrics=metrics,
            policy=policy,
            force_missing_metrics=False,
            semantic_disagreement=bool(packet.get("semantic_disagreement", False)),
        )
        if route not in {"abstain", "review_escalation", "blocked"}:
            route, exclusions, reason = "abstain", ["NO_CANDIDATES"], "no_candidates"
        scored: list[dict[str, Any]] = []
    else:
        top_relevance = None
        if candidates_in:
            top_relevance = str(candidates_in[0]["relevance"])
        route, exclusions, reason = choose_route(
            calibrated=calibrated,
            relevance=top_relevance,
            metrics=metrics,
            policy=policy,
            force_missing_metrics=force_missing,
            semantic_disagreement=bool(packet.get("semantic_disagreement", False)),
        )
        scored = score_candidates(candidates_in, route=route, exclusions=exclusions)

    selected_id = None
    if route in {
        "exact_retrieval",
        "approximate_retrieval",
        "layered_synthesis",
        "generated_fallback",
    }:
        eligible = [item for item in scored if item["eligible"]]
        if not eligible:
            route = "abstain"
            reason = "no_eligible_candidate"
            scored = score_candidates(candidates_in, route=route, exclusions=["BELOW_ROUTE_THRESHOLD"])
        else:
            selected_id = eligible[0]["candidate_id"]

    family_metrics = metrics or {
        "support_count": 0,
        "precision": 0.0,
        "recall": 0.0,
        "false_match_rate": 1.0,
        "false_negative_rate": 1.0,
    }

    candidate_set_hash = sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "candidate_id": item["candidate_id"],
                    "asset_sha256": item["asset_sha256"],
                    "relevance": item["relevance"],
                }
                for item in scored
            ]
        )
    )

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "audio_retrieval_fallback_calibration_record",
        "calibrator_revision": CALIBRATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "calibration_revision": CALIBRATION_REVISION,
        "metric_table_revision": METRIC_TABLE_REVISION,
        "metric_table_sha256": metric_table_sha256(policy),
        "event_id": str(packet["event_id"]),
        "event_family": event_family,
        "query_hash": str(packet["query_hash"]),
        "candidate_set_hash": candidate_set_hash,
        "partition_id": str(packet.get("partition_id", "synthetic_fixture")),
        "raw_confidence": round_finite(raw),
        "calibrated_confidence": calibrated,
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "required_routes": list(REQUIRED_ROUTES),
        "event_family_metrics": {
            "support_count": int(family_metrics["support_count"]),
            "precision": round_finite(float(family_metrics["precision"])),
            "recall": round_finite(float(family_metrics["recall"])),
            "false_match_rate": round_finite(float(family_metrics["false_match_rate"])),
            "false_negative_rate": round_finite(float(family_metrics["false_negative_rate"])),
        },
        "candidates": scored,
        "decision": {
            "route": route,
            "selected_candidate_id": selected_id,
            "confidence": calibrated,
            "reason": reason,
            "applied_gates": list(REQUIRED_GATES),
            "explanation": [
                f"raw_confidence={round_finite(raw)}",
                f"calibrated_confidence={calibrated}",
                f"route={route}",
                f"reason={reason}",
                f"exclusions={exclusions or ['none']}",
                *(
                    ["low_confidence_cannot_silently_select"]
                    if reason == "low_confidence_abstain"
                    else []
                ),
            ],
            "product_completion": False,
            "row083_acceptance": "fixture_only" if is_synthetic else "held",
        },
    }
    sealed = seal_record(record)
    validate_calibration_record(root, sealed)
    return sealed


def _candidate(candidate_id: str, asset_seed: str, relevance: str) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "asset_sha256": _stable_hash(asset_seed),
        "relevance": relevance,
    }


def fixture_calibration_packet(name: str) -> dict[str, Any]:
    if name == "high_confidence_exact_selects_exact":
        return {
            "event_id": "fixture_exact_ok",
            "event_family": "footstep",
            "query_hash": _stable_hash("query:exact_ok"),
            "raw_confidence": 0.97,
            "partition_id": "synthetic_fixture",
            "candidates": [
                _candidate("cand_exact_ok", "asset:exact_ok", "exact"),
                _candidate("cand_approx_alt", "asset:approx_alt", "approximate"),
            ],
        }
    if name == "below_exact_routes_to_approximate":
        return {
            "event_id": "fixture_below_exact",
            "event_family": "fabric_rustle",
            "query_hash": _stable_hash("query:below_exact"),
            "raw_confidence": 0.84,
            "partition_id": "synthetic_fixture",
            "candidates": [
                _candidate("cand_approx_primary", "asset:approx_primary", "approximate"),
                _candidate("cand_exact_secondary", "asset:exact_secondary", "exact"),
            ],
        }
    if name == "low_confidence_abstains_not_silent_select":
        return {
            "event_id": "fixture_low_confidence",
            "event_family": "impact_hard",
            "query_hash": _stable_hash("query:low_confidence"),
            "raw_confidence": 0.30,
            "partition_id": "synthetic_fixture",
            "candidates": [
                _candidate("cand_silent_trap", "asset:silent_trap", "exact"),
            ],
        }
    if name == "no_candidates_fails_closed":
        return {
            "event_id": "fixture_no_candidates",
            "event_family": "footstep",
            "query_hash": _stable_hash("query:no_candidates"),
            "raw_confidence": 0.99,
            "partition_id": "synthetic_fixture",
            "candidates": [],
        }
    if name == "sparse_family_fails_closed":
        return {
            "event_id": "fixture_sparse",
            "event_family": "sparse_unknown",
            "query_hash": _stable_hash("query:sparse"),
            "raw_confidence": 0.99,
            "partition_id": "synthetic_fixture",
            "candidates": [
                _candidate("cand_sparse", "asset:sparse", "exact"),
            ],
        }
    if name == "missing_metric_table_fails_closed":
        return {
            "event_id": "fixture_missing_metrics",
            "event_family": "footstep",
            "query_hash": _stable_hash("query:missing_metrics"),
            "raw_confidence": 0.99,
            "force_missing_metrics": True,
            "partition_id": "synthetic_fixture",
            "candidates": [
                _candidate("cand_no_metrics", "asset:no_metrics", "exact"),
            ],
        }
    if name == "generated_fallback_under_calibrated_band":
        return {
            "event_id": "fixture_generated_fallback",
            "event_family": "impact_hard",
            "query_hash": _stable_hash("query:generated"),
            "raw_confidence": 0.60,
            "partition_id": "synthetic_fixture",
            "candidates": [
                _candidate("cand_generated", "asset:generated", "generated"),
            ],
        }
    raise RetrievalFallbackError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_calibration_packet(name)
    return build_calibration_record(root, packet=packet, is_synthetic=True)


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW083_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "HELD_OUT_EVENT_FAMILY_CORPUS_ABSENT",
        "RUNTIME_CALIBRATION_THRESHOLDS_ABSENT",
        "LIBRARY_SOURCE_ROUTE_RUNTIME_ABSENT",
        "CONTENT_ADDRESSED_RUNTIME_RECEIPT_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-083_retrieval_fallback_calibration",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "calibrator_revision": CALIBRATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "calibration_revision": CALIBRATION_REVISION,
        "metric_table_revision": METRIC_TABLE_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_LIBRARY_CALIBRATION_RUNTIME_ABSENT",
        "required_gates": list(REQUIRED_GATES),
        "required_routes": list(REQUIRED_ROUTES),
        "dependency_admissions": admissions,
        "policy_registry": {
            "path": str(POLICY_PATH).replace("\\", "/"),
            "revision": policy["revision"],
            "authority": policy.get("authority"),
            "sha256": sha256_file(policy_path),
        },
        "schema": {
            "path": str(SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(resolve_under(root, SCHEMA_PATH, "schema")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove exact/approximate routing, low-confidence abstention, "
                "no-candidate fail-closed behavior, sparse-family review escalation, missing "
                "metric-table rejection, and generated-fallback banding; they do not accept "
                "Row083 library completion or held-out runtime proof."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row083_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows081 and 082; freeze an immutable held-out event-family corpus with "
                "train/calibration/final-test partitions; bind precision, recall, false-match "
                "rates, confidence intervals, and versioned route thresholds; enforce mutually "
                "exclusive route semantics and selected-candidate invariants; emit content-"
                "addressed decision receipts; then replace this hold packet."
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
    parser.add_argument("--fixture", default="high_confidence_exact_selects_exact")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise RetrievalFallbackError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise RetrievalFallbackError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["route"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
