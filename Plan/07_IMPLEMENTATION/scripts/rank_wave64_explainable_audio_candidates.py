#!/usr/bin/env python3
"""Fail-closed Wave64 Row081 explainable audio candidate ranking slice.

Library scoring refuses authority without accepted Rows068/072/076/079/080.
Fixture mode may emit deterministic schema-validated ranking receipts from
synthetic candidate packets without promoting library completion.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/explainable_audio_candidate_ranking_record.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row081_explainable_candidate_ranking_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-081_explainable_candidate_ranking.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-068": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-072": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-072_ONSET_TRANSIENT_ANCHOR_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-076": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-076_REVERB_DRYNESS_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-079": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-079_FINE_GRAINED_FOLEY_TAXONOMY_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-080": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-080_HYBRID_AUDIO_RETRIEVAL_INDEX_CURRENT_DELTA_20260719.json"
    ),
}

SCORER_REVISION = "wave64_row081_explainable_audio_candidate_ranker_v0.1.0"
POLICY_REVISION = "wave64_row081_explainable_candidate_ranking_policy_v0.1.0"
TRACKER_ID = "TRK-W64-081"
ITEM_ID = "ITEM-W64-081"
SCHEMA_VERSION = "1.0.0"

REQUIRED_COMPONENTS = (
    "event_fit",
    "source_target_fit",
    "material_fit",
    "body_part_fit",
    "footwear_fit",
    "force_fit",
    "timing_fit",
    "duration_fit",
    "onset_fit",
    "acoustic_fit",
    "quality_fit",
    "rights_eligibility",
    "continuity_fit",
    "cost",
)

HARD_FILTER_ORDER = (
    "RIGHTS_INELIGIBLE",
    "MISSING_MANDATORY_FEATURE",
    "TAXONOMY_INCOMPATIBLE",
    "QUERY_CANDIDATE_SET_MISMATCH",
    "DEPENDENCY_EVIDENCE_ABSENT",
)

FIXTURE_NAMES = (
    "select_clear_winner",
    "tie_break_by_candidate_id",
    "hard_exclude_rights",
    "missing_mandatory_abstain",
)


class ExplainableRankingError(ValueError):
    """Raised when Row081 ranking violates fail-closed authority."""


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
        raise ExplainableRankingError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise ExplainableRankingError("non_finite_score_value")
    return round(float(value), digits)


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise ExplainableRankingError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_components") or ()) != REQUIRED_COMPONENTS:
        raise ExplainableRankingError("policy_required_components_mismatch")
    if tuple(payload.get("hard_filter_order") or ()) != HARD_FILTER_ORDER:
        raise ExplainableRankingError("policy_hard_filter_order_mismatch")
    weights = [
        float(payload["component_policy"][name]["weight"]) for name in REQUIRED_COMPONENTS
    ]
    if abs(sum(weights) - 1.0) > 1e-9:
        raise ExplainableRankingError("policy_weights_must_sum_to_one")
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


def normalize_component(
    *,
    raw: float | None,
    raw_min: float,
    raw_max: float,
    direction: str,
) -> float | None:
    if raw is None:
        return None
    if raw_max <= raw_min:
        raise ExplainableRankingError("invalid_component_bounds")
    clamped = min(max(float(raw), raw_min), raw_max)
    unit = (clamped - raw_min) / (raw_max - raw_min)
    if direction == "higher_better":
        return round_finite(unit)
    if direction == "lower_better":
        return round_finite(1.0 - unit)
    raise ExplainableRankingError("unknown_component_direction")


def apply_hard_filters(candidate: dict[str, Any], *, library_deps_ok: bool) -> list[str]:
    exclusions: list[str] = []
    features = candidate.get("features") or {}
    if candidate.get("rights_eligible") is not True:
        exclusions.append("RIGHTS_INELIGIBLE")
    for name in REQUIRED_COMPONENTS:
        if features.get(name) is None:
            exclusions.append("MISSING_MANDATORY_FEATURE")
            break
    if candidate.get("taxonomy_compatible") is not True:
        exclusions.append("TAXONOMY_INCOMPATIBLE")
    if candidate.get("in_candidate_set") is not True:
        exclusions.append("QUERY_CANDIDATE_SET_MISMATCH")
    if not library_deps_ok and candidate.get("require_dependency_evidence") is True:
        exclusions.append("DEPENDENCY_EVIDENCE_ABSENT")
    ordered = [code for code in HARD_FILTER_ORDER if code in exclusions]
    return ordered


def score_candidate(
    candidate: dict[str, Any],
    policy: dict[str, Any],
    *,
    library_deps_ok: bool,
) -> dict[str, Any]:
    hard_exclusions = apply_hard_filters(candidate, library_deps_ok=library_deps_ok)
    eligible = len(hard_exclusions) == 0
    features = candidate.get("features") or {}
    components: dict[str, Any] = {}
    contributions: list[float] = []
    explanation: list[str] = [
        f"hard_filters={hard_exclusions or ['none']}",
        f"eligible={eligible}",
    ]
    for name in REQUIRED_COMPONENTS:
        cfg = policy["component_policy"][name]
        raw = features.get(name)
        present = raw is not None
        if present and not isinstance(raw, (int, float)):
            raise ExplainableRankingError(f"non_numeric_feature:{name}")
        if present and not math.isfinite(float(raw)):
            raise ExplainableRankingError(f"non_finite_feature:{name}")
        normalized = normalize_component(
            raw=float(raw) if present else None,
            raw_min=float(cfg["raw_min"]),
            raw_max=float(cfg["raw_max"]),
            direction=str(cfg["direction"]),
        )
        weight = float(cfg["weight"])
        contribution = None if normalized is None else round_finite(normalized * weight)
        if contribution is not None and eligible:
            contributions.append(contribution)
        components[name] = {
            "raw": None if raw is None else round_finite(float(raw)),
            "raw_min": float(cfg["raw_min"]),
            "raw_max": float(cfg["raw_max"]),
            "normalized": normalized,
            "weight": weight,
            "contribution": contribution,
            "direction": cfg["direction"],
            "mandatory": bool(cfg["mandatory"]),
            "present": present,
        }
        explanation.append(
            f"{name}: raw={components[name]['raw']} norm={normalized} "
            f"weight={weight} contrib={contribution}"
        )

    penalties: list[dict[str, Any]] = []
    penalty_total = 0.0
    for code, raw_value in (candidate.get("penalty_inputs") or {}).items():
        cfg = policy["penalty_policy"].get(code)
        if cfg is None:
            raise ExplainableRankingError(f"unknown_penalty_code:{code}")
        raw_f = float(raw_value)
        if not math.isfinite(raw_f):
            raise ExplainableRankingError(f"non_finite_penalty:{code}")
        contribution = -min(float(cfg["cap"]), max(0.0, raw_f) * float(cfg["scale"]))
        contribution = round_finite(contribution)
        penalty_total += contribution
        penalties.append(
            {
                "code": code,
                "raw": round_finite(raw_f),
                "scale": float(cfg["scale"]),
                "cap": float(cfg["cap"]),
                "contribution": contribution,
                "reason": f"penalty_{code}_applied",
            }
        )
        explanation.append(f"penalty:{code}={contribution}")

    if eligible:
        total_score = round_finite(sum(contributions) + penalty_total)
    else:
        total_score = round_finite(-1.0)
        explanation.append("weighted_ranking_skipped_due_to_hard_exclusion")

    asset_sha256 = str(candidate["asset_sha256"])
    if len(asset_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in asset_sha256):
        raise ExplainableRankingError("asset_sha256_invalid")

    return {
        "candidate_id": str(candidate["candidate_id"]),
        "asset_sha256": asset_sha256,
        "eligible": eligible,
        "hard_exclusions": hard_exclusions,
        "components": components,
        "penalties": penalties,
        "total_score": total_score,
        "rank": 0,
        "explanation": explanation,
    }


def tie_break_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    # Ascending sort: negate score so higher score sorts first.
    return (-float(candidate["total_score"]), candidate["candidate_id"], candidate["asset_sha256"])


def assign_ranks(scored: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    ordered = sorted(scored, key=tie_break_key)
    for index, candidate in enumerate(ordered, start=1):
        candidate["rank"] = index
    winner = ordered[0] if ordered else None
    eligible = [item for item in ordered if item["eligible"]]
    applied = False
    if len(eligible) >= 2:
        top = eligible[0]
        second = eligible[1]
        applied = abs(float(top["total_score"]) - float(second["total_score"])) < 1e-12
    return {
        "applied": applied,
        "order": list(policy["tie_break_order"]),
        "winner_candidate_id": None if winner is None else winner["candidate_id"],
        "inputs": [
            {
                "candidate_id": item["candidate_id"],
                "total_score": item["total_score"],
                "asset_sha256": item["asset_sha256"],
            }
            for item in ordered
        ],
    }


def validate_ranking_semantics(record: dict[str, Any]) -> None:
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ExplainableRankingError("candidates_missing")
    ids = [item.get("candidate_id") for item in candidates]
    assets = [item.get("asset_sha256") for item in candidates]
    ranks = [item.get("rank") for item in candidates]
    if len(ids) != len(set(ids)):
        raise ExplainableRankingError("duplicate_candidate_id")
    if len(assets) != len(set(assets)):
        raise ExplainableRankingError("duplicate_asset_sha256")
    if len(ranks) != len(set(ranks)):
        raise ExplainableRankingError("duplicate_rank")
    if sorted(ranks) != list(range(1, len(candidates) + 1)):
        raise ExplainableRankingError("ranks_not_contiguous")
    by_rank = sorted(candidates, key=lambda item: int(item["rank"]))
    for left, right in zip(by_rank, by_rank[1:], strict=False):
        if tie_break_key(left) > tie_break_key(right):
            raise ExplainableRankingError("rank_order_inconsistent_with_tie_break")
    for item in candidates:
        exclusions = item.get("hard_exclusions") or []
        if item.get("eligible") is True and exclusions:
            raise ExplainableRankingError("eligible_with_hard_exclusions")
        if item.get("eligible") is False and not exclusions:
            raise ExplainableRankingError("ineligible_without_hard_exclusions")
        components = item.get("components") or {}
        if set(components.keys()) != set(REQUIRED_COMPONENTS):
            raise ExplainableRankingError("component_set_mismatch")
        explanation = item.get("explanation") or []
        if not explanation:
            raise ExplainableRankingError("candidate_explanation_missing")
        if item.get("eligible") is True:
            recomputed = 0.0
            for name in REQUIRED_COMPONENTS:
                contribution = components[name]["contribution"]
                if contribution is None:
                    raise ExplainableRankingError(f"eligible_missing_contribution:{name}")
                recomputed += float(contribution)
            for penalty in item.get("penalties") or []:
                recomputed += float(penalty["contribution"])
            if abs(recomputed - float(item["total_score"])) > 1e-9:
                raise ExplainableRankingError("total_score_recompute_mismatch")
    decision = record.get("decision") or {}
    route = decision.get("route")
    selected = decision.get("selected_candidate_id")
    by_id = {item["candidate_id"]: item for item in candidates}
    if route == "select":
        if selected not in by_id:
            raise ExplainableRankingError("selected_candidate_missing")
        chosen = by_id[selected]
        if chosen.get("eligible") is not True:
            raise ExplainableRankingError("selected_candidate_ineligible")
        if int(chosen["rank"]) != 1:
            raise ExplainableRankingError("selected_candidate_not_rank_one")
    elif route in {"abstain", "blocked"}:
        if selected is not None:
            raise ExplainableRankingError("abstain_or_blocked_must_null_selection")
    else:
        raise ExplainableRankingError("unknown_decision_route")
    if record.get("library_authority") is True:
        raise ExplainableRankingError("library_authority_forbidden_in_this_slice")
    if decision.get("product_completion") is True:
        raise ExplainableRankingError("product_completion_forbidden_in_this_slice")


def validate_ranking_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_ranking_semantics(record)


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def build_ranking_record(
    root: Path,
    *,
    event_id: str,
    query_hash: str,
    index_revision: str,
    candidates_input: list[dict[str, Any]],
    is_synthetic: bool,
    force_blocked: bool = False,
) -> dict[str, Any]:
    policy = load_policy(root)
    admissions = evaluate_all_dependency_admissions(root)
    library_deps_ok = all(item["dependency_satisfied"] for item in admissions.values())
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    policy_sha256 = sha256_file(policy_path)

    scored = [
        score_candidate(item, policy, library_deps_ok=library_deps_ok)
        for item in candidates_input
    ]
    tie_break = assign_ranks(scored, policy)
    candidate_set_hash = sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "candidate_id": item["candidate_id"],
                    "asset_sha256": item["asset_sha256"],
                }
                for item in sorted(scored, key=lambda row: row["candidate_id"])
            ]
        )
    )
    eligible = [item for item in scored if item["eligible"]]
    thresholds = policy["decision_thresholds"]
    explanation = [
        "hard_exclusions_evaluated_before_weighted_ranking",
        f"eligible_count={len(eligible)}",
        f"library_deps_ok={library_deps_ok}",
        f"tie_break_applied={tie_break['applied']}",
    ]

    if force_blocked or not library_deps_ok:
        route = "blocked"
        selected = None
        confidence = 0.0
        reason = "dependencies_or_library_authority_absent"
        acceptance = "held"
        explanation.append("library_scoring_blocked_fail_closed")
    elif not eligible:
        route = "abstain"
        selected = None
        confidence = 0.0
        reason = "no_eligible_candidate"
        acceptance = "fixture_only" if is_synthetic else "held"
        explanation.append("abstain_no_eligible_candidate")
    else:
        winner = sorted(eligible, key=tie_break_key)[0]
        confidence = round_finite(min(1.0, max(0.0, float(winner["total_score"]))))
        if confidence < float(thresholds["min_select_confidence"]):
            route = "abstain"
            selected = None
            reason = "below_min_select_confidence"
            acceptance = "fixture_only" if is_synthetic else "held"
            explanation.append("abstain_below_confidence_threshold")
        else:
            route = "select"
            selected = winner["candidate_id"]
            reason = "selected_rank_one_eligible_candidate"
            acceptance = "fixture_only" if is_synthetic else "held"
            explanation.append(f"selected={selected}")

    # Fixture-only ranking still records selection semantics under library_authority=false.
    # When dependencies are unmet, library mode remains blocked even if fixtures select.
    if is_synthetic and not force_blocked and library_deps_ok is False:
        # Keep fixture semantics visible while proving library authority remains false.
        if eligible:
            winner = sorted(eligible, key=tie_break_key)[0]
            confidence = round_finite(min(1.0, max(0.0, float(winner["total_score"]))))
            if confidence >= float(thresholds["min_select_confidence"]):
                route = "select"
                selected = winner["candidate_id"]
                reason = "fixture_selected_rank_one_eligible_candidate"
                acceptance = "fixture_only"
            else:
                route = "abstain"
                selected = None
                reason = "fixture_below_min_select_confidence"
                acceptance = "fixture_only"
        else:
            route = "abstain"
            selected = None
            reason = "fixture_no_eligible_candidate"
            acceptance = "fixture_only"
        explanation.append("fixture_mode_records_decision_without_library_authority")

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "explainable_audio_candidate_ranking_record",
        "scorer_revision": SCORER_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": policy_sha256,
        "event_id": event_id,
        "query_hash": query_hash,
        "candidate_set_hash": candidate_set_hash,
        "index_revision": index_revision,
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "hard_filter_order": list(HARD_FILTER_ORDER),
        "required_components": list(REQUIRED_COMPONENTS),
        "candidates": sorted(scored, key=lambda item: int(item["rank"])),
        "decision": {
            "route": route,
            "selected_candidate_id": selected,
            "confidence": confidence,
            "reason": reason,
            "tie_break_outcome": tie_break,
            "explanation": explanation,
            "product_completion": False,
            "row081_acceptance": acceptance,
        },
    }
    sealed = seal_record(record)
    validate_ranking_record(root, sealed)
    return sealed


def _asset(seed: str) -> str:
    return sha256_bytes(seed.encode("utf-8"))


def _base_features(**overrides: float | None) -> dict[str, float | None]:
    values: dict[str, float | None] = {
        "event_fit": 0.90,
        "source_target_fit": 0.88,
        "material_fit": 0.86,
        "body_part_fit": 0.84,
        "footwear_fit": 0.80,
        "force_fit": 0.82,
        "timing_fit": 0.85,
        "duration_fit": 0.83,
        "onset_fit": 0.81,
        "acoustic_fit": 0.79,
        "quality_fit": 0.87,
        "rights_eligibility": 1.0,
        "continuity_fit": 0.78,
        "cost": 0.20,
    }
    values.update(overrides)
    return values


def fixture_candidate_packet(name: str) -> dict[str, Any]:
    if name == "select_clear_winner":
        return {
            "event_id": "fixture_event_select_clear_winner",
            "query_hash": _asset("query:select_clear_winner"),
            "index_revision": "fixture_index_v0",
            "candidates": [
                {
                    "candidate_id": "cand_a_best",
                    "asset_sha256": _asset("asset:a_best"),
                    "rights_eligible": True,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": _base_features(event_fit=0.95, cost=0.10),
                    "penalty_inputs": {},
                },
                {
                    "candidate_id": "cand_b_mid",
                    "asset_sha256": _asset("asset:b_mid"),
                    "rights_eligible": True,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": _base_features(event_fit=0.70, cost=0.40),
                    "penalty_inputs": {"near_duplicate_recent_use": 0.5},
                },
            ],
        }
    if name == "tie_break_by_candidate_id":
        features = _base_features()
        return {
            "event_id": "fixture_event_tie_break",
            "query_hash": _asset("query:tie_break"),
            "index_revision": "fixture_index_v0",
            "candidates": [
                {
                    "candidate_id": "cand_z_tie",
                    "asset_sha256": _asset("asset:z_tie"),
                    "rights_eligible": True,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": dict(features),
                    "penalty_inputs": {},
                },
                {
                    "candidate_id": "cand_a_tie",
                    "asset_sha256": _asset("asset:a_tie"),
                    "rights_eligible": True,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": dict(features),
                    "penalty_inputs": {},
                },
            ],
        }
    if name == "hard_exclude_rights":
        return {
            "event_id": "fixture_event_rights_exclude",
            "query_hash": _asset("query:rights_exclude"),
            "index_revision": "fixture_index_v0",
            "candidates": [
                {
                    "candidate_id": "cand_rights_bad",
                    "asset_sha256": _asset("asset:rights_bad"),
                    "rights_eligible": False,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": _base_features(rights_eligibility=0.0),
                    "penalty_inputs": {},
                },
                {
                    "candidate_id": "cand_rights_ok",
                    "asset_sha256": _asset("asset:rights_ok"),
                    "rights_eligible": True,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": _base_features(),
                    "penalty_inputs": {},
                },
            ],
        }
    if name == "missing_mandatory_abstain":
        missing = _base_features()
        missing["onset_fit"] = None
        return {
            "event_id": "fixture_event_missing_mandatory",
            "query_hash": _asset("query:missing_mandatory"),
            "index_revision": "fixture_index_v0",
            "candidates": [
                {
                    "candidate_id": "cand_missing_onset",
                    "asset_sha256": _asset("asset:missing_onset"),
                    "rights_eligible": True,
                    "taxonomy_compatible": True,
                    "in_candidate_set": True,
                    "require_dependency_evidence": False,
                    "features": missing,
                    "penalty_inputs": {},
                }
            ],
        }
    raise ExplainableRankingError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_candidate_packet(name)
    return build_ranking_record(
        root,
        event_id=packet["event_id"],
        query_hash=packet["query_hash"],
        index_revision=packet["index_revision"],
        candidates_input=packet["candidates"],
        is_synthetic=True,
        force_blocked=False,
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW081_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_LIBRARY_SCORING_RUNTIME_ABSENT",
        "HELD_OUT_RANKING_CALIBRATION_ABSENT",
        "CONTENT_ADDRESSED_RUNTIME_RECEIPT_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-081_explainable_candidate_ranking",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "scorer_revision": SCORER_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_LIBRARY_SCORING_RUNTIME_ABSENT",
        "required_components": list(REQUIRED_COMPONENTS),
        "hard_filter_order": list(HARD_FILTER_ORDER),
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
                "Fixture records prove hard filters, fourteen component contributions, "
                "penalties, deterministic tie-breaks, and explanation receipts; they do not "
                "accept Row081 library completion."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row081_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows068, 072, 076, 079, and 080; bind an immutable query and "
                "canonical candidate set; execute typed hard filters before weighted ranking; "
                "emit content-addressed runtime receipts with held-out calibration; then replace "
                "this hold packet."
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
    parser.add_argument("--fixture", default="select_clear_winner")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise ExplainableRankingError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise ExplainableRankingError(
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
