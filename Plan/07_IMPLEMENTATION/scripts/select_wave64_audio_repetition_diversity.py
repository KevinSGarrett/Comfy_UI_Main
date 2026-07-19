#!/usr/bin/env python3
"""Fail-closed Wave64 Row082 audio repetition/diversity selection slice.

Library selection refuses authority without accepted Rows074/080/081.
Fixture mode may emit deterministic schema-validated selection receipts from
synthetic history/candidate packets without promoting library completion.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_repetition_diversity_selection_record.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row082_repetition_diversity_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-082_audio_repetition_diversity.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-074": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-080": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-080_HYBRID_AUDIO_RETRIEVAL_INDEX_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-081": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-081_EXPLAINABLE_AUDIO_CANDIDATE_SCORING_CURRENT_DELTA_20260719.json"
    ),
}

SELECTOR_REVISION = "wave64_row082_audio_repetition_diversity_selector_v0.1.0"
POLICY_REVISION = "wave64_row082_repetition_diversity_policy_v0.1.0"
TRACKER_ID = "TRK-W64-082"
ITEM_ID = "ITEM-W64-082"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "cooldown",
    "near_duplicate_penalty",
    "alternation",
    "scene_continuity",
    "bounded_variation",
)

HARD_EXCLUSION_ORDER = (
    "MISSING_SELECTION_HISTORY",
    "COOLDOWN_ACTIVE",
    "ALTERNATION_VIOLATION",
    "CONTINUITY_PARTITION_MISMATCH",
    "TRANSFORM_OUT_OF_BOUNDS",
    "SEMANTIC_FLOOR_VIOLATION",
    "DEPENDENCY_EVIDENCE_ABSENT",
)

FIXTURE_NAMES = (
    "cooldown_blocks_identical_reuse",
    "near_duplicate_penalty_rotates",
    "foot_alternation_preserves_order",
    "missing_history_fails_closed",
    "out_of_bound_transform_rejected",
)


class RepetitionDiversityError(ValueError):
    """Raised when Row082 selection violates fail-closed authority."""


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
        raise RepetitionDiversityError(f"{label}_outside_project_root") from exc
    return path


def round_finite(value: float, digits: int = 9) -> float:
    if not math.isfinite(value):
        raise RepetitionDiversityError("non_finite_score_value")
    return round(float(value), digits)


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise RepetitionDiversityError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise RepetitionDiversityError("policy_required_gates_mismatch")
    if tuple(payload.get("hard_exclusion_order") or ()) != HARD_EXCLUSION_ORDER:
        raise RepetitionDiversityError("policy_hard_exclusion_order_mismatch")
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
    # Row081 hold_with_* qa_decision must not count as pass.
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


def identity_transform() -> dict[str, float]:
    return {
        "gain_db": 0.0,
        "timing_ms": 0.0,
        "pitch_cents": 0.0,
        "eq_tilt_db": 0.0,
        "transient_scale": 1.0,
        "stereo_width": 1.0,
        "room_mix": 0.0,
    }


def transform_out_of_bounds(transform: dict[str, Any], policy: dict[str, Any]) -> bool:
    limits = policy["bounded_variation_policy"]["limits"]
    for key, bounds in limits.items():
        value = float(transform.get(key, 0.0))
        if value < float(bounds["min"]) or value > float(bounds["max"]):
            return True
    return False


def semantic_floor_violation(scores: dict[str, Any], policy: dict[str, Any]) -> bool:
    floors = policy["bounded_variation_policy"]["semantic_floors"]
    for key, floor in floors.items():
        if float(scores.get(key, 0.0)) < float(floor):
            return True
    return False


def apply_hard_exclusions(
    candidate: dict[str, Any],
    *,
    policy: dict[str, Any],
    packet: dict[str, Any],
    library_deps_ok: bool,
) -> list[str]:
    exclusions: list[str] = []
    history_sha = packet.get("selection_history_sha256")
    if not history_sha or history_sha == ("0" * 64):
        exclusions.append("MISSING_SELECTION_HISTORY")

    cooldown = packet.get("cooldown_state") or {}
    recent_assets = set(cooldown.get("recent_asset_sha256") or [])
    if candidate.get("asset_sha256") in recent_assets:
        exclusions.append("COOLDOWN_ACTIVE")

    alternation = packet.get("alternation_state") or {}
    if alternation.get("enabled") is True:
        expected = alternation.get("expected_side")
        candidate_side = candidate.get("foot_side")
        if expected is not None and candidate_side != expected:
            exclusions.append("ALTERNATION_VIOLATION")

    continuity = packet.get("continuity_keys") or {}
    cand_cont = candidate.get("continuity_keys") or {}
    for key in policy["continuity_policy"]["partition_keys"]:
        if key == "foot_side":
            continue
        if continuity.get(key) != cand_cont.get(key):
            exclusions.append("CONTINUITY_PARTITION_MISMATCH")
            break

    transform = candidate.get("variation_transform") or identity_transform()
    if transform_out_of_bounds(transform, policy):
        exclusions.append("TRANSFORM_OUT_OF_BOUNDS")

    semantic = candidate.get("semantic_scores") or {}
    if semantic_floor_violation(semantic, policy):
        exclusions.append("SEMANTIC_FLOOR_VIOLATION")

    if not library_deps_ok and candidate.get("require_dependency_evidence") is True:
        exclusions.append("DEPENDENCY_EVIDENCE_ABSENT")

    return [code for code in HARD_EXCLUSION_ORDER if code in exclusions]


def apply_penalties(
    candidate: dict[str, Any],
    *,
    policy: dict[str, Any],
    packet: dict[str, Any],
) -> list[dict[str, Any]]:
    penalties: list[dict[str, Any]] = []
    penalty_policy = policy["penalty_policy"]
    cooldown = packet.get("cooldown_state") or {}
    recent_groups = set(cooldown.get("recent_near_duplicate_group_ids") or [])
    recent_assets = set(cooldown.get("recent_asset_sha256") or [])

    if candidate.get("asset_sha256") in recent_assets:
        # Hard-excluded already; still record explanation input when present.
        pass

    group_id = str(candidate.get("near_duplicate_group_id") or "")
    similarity = float(candidate.get("near_duplicate_similarity") or 0.0)
    threshold = float(policy["near_duplicate_policy"]["similarity_threshold"])
    if group_id in recent_groups or similarity >= threshold:
        raw = max(similarity, 1.0 if group_id in recent_groups else 0.0)
        cfg = penalty_policy["near_duplicate_recent_use"]
        contribution = -min(float(cfg["cap"]), max(0.0, raw) * float(cfg["scale"]))
        penalties.append(
            {
                "code": "near_duplicate_recent_use",
                "raw": round_finite(raw),
                "scale": float(cfg["scale"]),
                "cap": float(cfg["cap"]),
                "contribution": round_finite(contribution),
                "reason": "near_duplicate_or_group_recently_used",
            }
        )

    recent_use_raw = float(candidate.get("recent_use_raw") or 0.0)
    if recent_use_raw > 0:
        cfg = penalty_policy["recent_use"]
        contribution = -min(float(cfg["cap"]), max(0.0, recent_use_raw) * float(cfg["scale"]))
        penalties.append(
            {
                "code": "recent_use",
                "raw": round_finite(recent_use_raw),
                "scale": float(cfg["scale"]),
                "cap": float(cfg["cap"]),
                "contribution": round_finite(contribution),
                "reason": "recent_use_penalty_applied",
            }
        )

    weak_div = float(candidate.get("weak_variation_diversity") or 0.0)
    if weak_div > 0:
        cfg = penalty_policy["weak_variation_diversity"]
        contribution = -min(float(cfg["cap"]), max(0.0, weak_div) * float(cfg["scale"]))
        penalties.append(
            {
                "code": "weak_variation_diversity",
                "raw": round_finite(weak_div),
                "scale": float(cfg["scale"]),
                "cap": float(cfg["cap"]),
                "contribution": round_finite(contribution),
                "reason": "weak_variation_diversity_penalty",
            }
        )
    return penalties


def score_candidate(
    candidate: dict[str, Any],
    *,
    policy: dict[str, Any],
    packet: dict[str, Any],
    library_deps_ok: bool,
) -> dict[str, Any]:
    hard_exclusions = apply_hard_exclusions(
        candidate, policy=policy, packet=packet, library_deps_ok=library_deps_ok
    )
    eligible = len(hard_exclusions) == 0
    penalties = apply_penalties(candidate, policy=policy, packet=packet)
    base_score = round_finite(float(candidate.get("base_score", 0.0)))
    penalty_total = round_finite(sum(float(item["contribution"]) for item in penalties))
    if eligible:
        total_score = round_finite(base_score + penalty_total)
    else:
        total_score = round_finite(-1.0)

    asset_sha256 = str(candidate["asset_sha256"])
    if len(asset_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in asset_sha256):
        raise RepetitionDiversityError("asset_sha256_invalid")

    transform = candidate.get("variation_transform") or identity_transform()
    semantic = candidate.get("semantic_scores") or {
        "event_fit": 0.9,
        "material_fit": 0.9,
        "force_fit": 0.9,
        "continuity_fit": 0.9,
    }
    explanation = [
        f"hard_filters={hard_exclusions or ['none']}",
        f"eligible={eligible}",
        f"base_score={base_score}",
        f"penalty_total={penalty_total}",
        f"total_score={total_score}",
    ]
    for penalty in penalties:
        explanation.append(f"penalty:{penalty['code']}={penalty['contribution']}")

    return {
        "candidate_id": str(candidate["candidate_id"]),
        "asset_sha256": asset_sha256,
        "near_duplicate_group_id": str(candidate["near_duplicate_group_id"]),
        "base_score": base_score,
        "eligible": eligible,
        "hard_exclusions": hard_exclusions,
        "penalties": penalties,
        "variation_transform": {
            key: round_finite(float(transform[key])) for key in identity_transform()
        },
        "semantic_scores": {
            "event_fit": round_finite(float(semantic["event_fit"])),
            "material_fit": round_finite(float(semantic["material_fit"])),
            "force_fit": round_finite(float(semantic["force_fit"])),
            "continuity_fit": round_finite(float(semantic["continuity_fit"])),
        },
        "total_score": total_score,
        "rank": 0,
        "explanation": explanation,
    }


def tie_break_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
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


def validate_selection_semantics(record: dict[str, Any]) -> None:
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RepetitionDiversityError("candidates_missing")
    ids = [item.get("candidate_id") for item in candidates]
    assets = [item.get("asset_sha256") for item in candidates]
    ranks = [item.get("rank") for item in candidates]
    if len(ids) != len(set(ids)):
        raise RepetitionDiversityError("duplicate_candidate_id")
    if len(assets) != len(set(assets)):
        raise RepetitionDiversityError("duplicate_asset_sha256")
    if len(ranks) != len(set(ranks)):
        raise RepetitionDiversityError("duplicate_rank")
    if sorted(ranks) != list(range(1, len(candidates) + 1)):
        raise RepetitionDiversityError("ranks_not_contiguous")
    by_rank = sorted(candidates, key=lambda item: int(item["rank"]))
    for left, right in zip(by_rank, by_rank[1:], strict=False):
        if tie_break_key(left) > tie_break_key(right):
            raise RepetitionDiversityError("rank_order_inconsistent_with_tie_break")
    for item in candidates:
        exclusions = item.get("hard_exclusions") or []
        if item.get("eligible") is True and exclusions:
            raise RepetitionDiversityError("eligible_with_hard_exclusions")
        if item.get("eligible") is False and not exclusions:
            raise RepetitionDiversityError("ineligible_without_hard_exclusions")
        if not (item.get("explanation") or []):
            raise RepetitionDiversityError("candidate_explanation_missing")
        if item.get("eligible") is True:
            recomputed = float(item["base_score"])
            for penalty in item.get("penalties") or []:
                recomputed += float(penalty["contribution"])
            if abs(recomputed - float(item["total_score"])) > 1e-9:
                raise RepetitionDiversityError("total_score_recompute_mismatch")
    if not record.get("selection_history_sha256"):
        raise RepetitionDiversityError("selection_history_missing")
    if not record.get("resulting_history_sha256"):
        raise RepetitionDiversityError("resulting_history_missing")
    decision = record.get("decision") or {}
    route = decision.get("route")
    selected = decision.get("selected_candidate_id")
    by_id = {item["candidate_id"]: item for item in candidates}
    if route == "select":
        if selected not in by_id:
            raise RepetitionDiversityError("selected_candidate_missing")
        chosen = by_id[selected]
        if chosen.get("eligible") is not True:
            raise RepetitionDiversityError("selected_candidate_ineligible")
        if int(chosen["rank"]) != 1:
            raise RepetitionDiversityError("selected_candidate_not_rank_one")
    elif route in {"abstain", "blocked"}:
        if selected is not None:
            raise RepetitionDiversityError("abstain_or_blocked_must_null_selection")
    else:
        raise RepetitionDiversityError("unknown_decision_route")
    if record.get("library_authority") is True:
        raise RepetitionDiversityError("library_authority_forbidden_in_this_slice")
    if decision.get("product_completion") is True:
        raise RepetitionDiversityError("product_completion_forbidden_in_this_slice")


def validate_selection_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_selection_semantics(record)


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def build_resulting_history_hash(
    *,
    selection_history_sha256: str,
    selected_candidate_id: str | None,
    selected_asset_sha256: str | None,
    event_id: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "previous_history_sha256": selection_history_sha256,
                "event_id": event_id,
                "selected_candidate_id": selected_candidate_id,
                "selected_asset_sha256": selected_asset_sha256,
            }
        )
    )


def build_selection_record(
    root: Path,
    *,
    packet: dict[str, Any],
    is_synthetic: bool,
    force_blocked: bool = False,
) -> dict[str, Any]:
    policy = load_policy(root)
    admissions = evaluate_all_dependency_admissions(root)
    library_deps_ok = all(item["dependency_satisfied"] for item in admissions.values())
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    policy_sha256 = sha256_file(policy_path)

    candidates_input = packet["candidates"]
    scored = [
        score_candidate(
            item,
            policy=policy,
            packet=packet,
            library_deps_ok=library_deps_ok,
        )
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
        "history_aware_hard_exclusions_before_diversity_ranking",
        f"eligible_count={len(eligible)}",
        f"library_deps_ok={library_deps_ok}",
        f"tie_break_applied={tie_break['applied']}",
    ]
    applied_gates = list(REQUIRED_GATES)

    if force_blocked or not library_deps_ok:
        route = "blocked"
        selected = None
        confidence = 0.0
        reason = "dependencies_or_library_authority_absent"
        acceptance = "held"
        explanation.append("library_selection_blocked_fail_closed")
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

    if is_synthetic and not force_blocked and library_deps_ok is False:
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

    selected_asset = None
    if selected is not None:
        selected_asset = next(
            item["asset_sha256"] for item in scored if item["candidate_id"] == selected
        )
    history_sha = str(packet["selection_history_sha256"])
    resulting_history = build_resulting_history_hash(
        selection_history_sha256=history_sha,
        selected_candidate_id=selected,
        selected_asset_sha256=selected_asset,
        event_id=str(packet["event_id"]),
    )

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "audio_repetition_diversity_selection_record",
        "selector_revision": SELECTOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": policy_sha256,
        "event_id": str(packet["event_id"]),
        "event_family": str(packet["event_family"]),
        "query_hash": str(packet["query_hash"]),
        "candidate_set_hash": candidate_set_hash,
        "selection_history_sha256": history_sha,
        "resulting_history_sha256": resulting_history,
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "hard_exclusion_order": list(HARD_EXCLUSION_ORDER),
        "continuity_keys": packet["continuity_keys"],
        "cooldown_state": packet["cooldown_state"],
        "alternation_state": packet["alternation_state"],
        "candidates": sorted(scored, key=lambda item: int(item["rank"])),
        "decision": {
            "route": route,
            "selected_candidate_id": selected,
            "confidence": confidence,
            "reason": reason,
            "tie_break_outcome": tie_break,
            "applied_gates": applied_gates,
            "explanation": explanation,
            "product_completion": False,
            "row082_acceptance": acceptance,
        },
    }
    sealed = seal_record(record)
    validate_selection_record(root, sealed)
    return sealed


def _asset(seed: str) -> str:
    return sha256_bytes(seed.encode("utf-8"))


def _continuity(
    *,
    actor_id: str = "actor_a",
    scene_id: str = "scene_kitchen",
    shot_id: str = "shot_01",
    gait_id: str = "gait_walk",
    foot_side: str | None = None,
) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "scene_id": scene_id,
        "shot_id": shot_id,
        "gait_id": gait_id,
        "foot_side": foot_side,
    }


def _semantic(**overrides: float) -> dict[str, float]:
    values = {
        "event_fit": 0.92,
        "material_fit": 0.90,
        "force_fit": 0.88,
        "continuity_fit": 0.91,
    }
    values.update(overrides)
    return values


def _candidate(
    *,
    candidate_id: str,
    asset_seed: str,
    group_id: str,
    base_score: float,
    continuity: dict[str, Any],
    foot_side: str | None = None,
    transform: dict[str, float] | None = None,
    semantic: dict[str, float] | None = None,
    near_duplicate_similarity: float = 0.0,
    recent_use_raw: float = 0.0,
    weak_variation_diversity: float = 0.0,
    require_dependency_evidence: bool = False,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "asset_sha256": _asset(asset_seed),
        "near_duplicate_group_id": group_id,
        "base_score": base_score,
        "foot_side": foot_side,
        "continuity_keys": continuity,
        "variation_transform": transform or identity_transform(),
        "semantic_scores": semantic or _semantic(),
        "near_duplicate_similarity": near_duplicate_similarity,
        "recent_use_raw": recent_use_raw,
        "weak_variation_diversity": weak_variation_diversity,
        "require_dependency_evidence": require_dependency_evidence,
    }


def fixture_selection_packet(name: str) -> dict[str, Any]:
    history = _asset(f"history:{name}")
    if name == "cooldown_blocks_identical_reuse":
        reused = _asset("asset:foot_a")
        continuity = _continuity(foot_side="left")
        return {
            "event_id": "fixture_event_cooldown",
            "event_family": "footstep",
            "query_hash": _asset("query:cooldown"),
            "selection_history_sha256": history,
            "continuity_keys": continuity,
            "cooldown_state": {
                "window_events": 4,
                "recent_asset_sha256": [reused],
                "recent_near_duplicate_group_ids": ["nd_foot_a"],
            },
            "alternation_state": {
                "enabled": True,
                "expected_side": "left",
                "previous_side": "right",
                "confidence": 0.9,
            },
            "candidates": [
                _candidate(
                    candidate_id="cand_reuse_blocked",
                    asset_seed="asset:foot_a",
                    group_id="nd_foot_a",
                    base_score=0.95,
                    continuity=continuity,
                    foot_side="left",
                ),
                _candidate(
                    candidate_id="cand_alt_ok",
                    asset_seed="asset:foot_b",
                    group_id="nd_foot_b",
                    base_score=0.84,
                    continuity=continuity,
                    foot_side="left",
                ),
            ],
        }
    if name == "near_duplicate_penalty_rotates":
        continuity = _continuity(foot_side="right")
        return {
            "event_id": "fixture_event_near_dup",
            "event_family": "footstep",
            "query_hash": _asset("query:near_dup"),
            "selection_history_sha256": history,
            "continuity_keys": continuity,
            "cooldown_state": {
                "window_events": 4,
                "recent_asset_sha256": [_asset("asset:prior_unique")],
                "recent_near_duplicate_group_ids": ["nd_group_hot"],
            },
            "alternation_state": {
                "enabled": True,
                "expected_side": "right",
                "previous_side": "left",
                "confidence": 0.88,
            },
            "candidates": [
                _candidate(
                    candidate_id="cand_near_dup_hot",
                    asset_seed="asset:near_dup_hot",
                    group_id="nd_group_hot",
                    base_score=0.93,
                    continuity=continuity,
                    foot_side="right",
                    near_duplicate_similarity=0.97,
                ),
                _candidate(
                    candidate_id="cand_distinct_rotate",
                    asset_seed="asset:distinct_rotate",
                    group_id="nd_group_cool",
                    base_score=0.86,
                    continuity=continuity,
                    foot_side="right",
                    near_duplicate_similarity=0.20,
                ),
            ],
        }
    if name == "foot_alternation_preserves_order":
        continuity = _continuity(foot_side="left")
        return {
            "event_id": "fixture_event_alternation",
            "event_family": "footstep",
            "query_hash": _asset("query:alternation"),
            "selection_history_sha256": history,
            "continuity_keys": continuity,
            "cooldown_state": {
                "window_events": 4,
                "recent_asset_sha256": [],
                "recent_near_duplicate_group_ids": [],
            },
            "alternation_state": {
                "enabled": True,
                "expected_side": "left",
                "previous_side": "right",
                "confidence": 0.95,
            },
            "candidates": [
                _candidate(
                    candidate_id="cand_right_wrong",
                    asset_seed="asset:right_wrong",
                    group_id="nd_right",
                    base_score=0.96,
                    continuity=_continuity(foot_side="right"),
                    foot_side="right",
                ),
                _candidate(
                    candidate_id="cand_left_expected",
                    asset_seed="asset:left_expected",
                    group_id="nd_left",
                    base_score=0.85,
                    continuity=continuity,
                    foot_side="left",
                ),
            ],
        }
    if name == "missing_history_fails_closed":
        continuity = _continuity(foot_side="left")
        return {
            "event_id": "fixture_event_missing_history",
            "event_family": "footstep",
            "query_hash": _asset("query:missing_history"),
            "selection_history_sha256": "0" * 64,
            "continuity_keys": continuity,
            "cooldown_state": {
                "window_events": 4,
                "recent_asset_sha256": [],
                "recent_near_duplicate_group_ids": [],
            },
            "alternation_state": {
                "enabled": True,
                "expected_side": "left",
                "previous_side": "right",
                "confidence": 0.9,
            },
            "candidates": [
                _candidate(
                    candidate_id="cand_no_history",
                    asset_seed="asset:no_history",
                    group_id="nd_no_history",
                    base_score=0.90,
                    continuity=continuity,
                    foot_side="left",
                )
            ],
        }
    if name == "out_of_bound_transform_rejected":
        continuity = _continuity(foot_side=None)
        bad_transform = identity_transform()
        bad_transform["gain_db"] = 4.0
        return {
            "event_id": "fixture_event_transform_bounds",
            "event_family": "fabric_rustle",
            "query_hash": _asset("query:transform_bounds"),
            "selection_history_sha256": history,
            "continuity_keys": continuity,
            "cooldown_state": {
                "window_events": 2,
                "recent_asset_sha256": [],
                "recent_near_duplicate_group_ids": [],
            },
            "alternation_state": {
                "enabled": False,
                "expected_side": None,
                "previous_side": None,
                "confidence": 1.0,
            },
            "candidates": [
                _candidate(
                    candidate_id="cand_transform_bad",
                    asset_seed="asset:transform_bad",
                    group_id="nd_fabric_a",
                    base_score=0.94,
                    continuity=continuity,
                    transform=bad_transform,
                ),
                _candidate(
                    candidate_id="cand_transform_ok",
                    asset_seed="asset:transform_ok",
                    group_id="nd_fabric_b",
                    base_score=0.82,
                    continuity=continuity,
                    transform=identity_transform(),
                ),
            ],
        }
    raise RepetitionDiversityError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_selection_packet(name)
    return build_selection_record(
        root,
        packet=packet,
        is_synthetic=True,
        force_blocked=False,
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW082_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_LIBRARY_DIVERSITY_RUNTIME_ABSENT",
        "HELD_OUT_REPEATED_EVENT_BENCHMARK_ABSENT",
        "ATOMIC_SELECTION_HISTORY_TRANSACTION_ABSENT",
        "CONTENT_ADDRESSED_RUNTIME_RECEIPT_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-082_audio_repetition_diversity",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "selector_revision": SELECTOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_LIBRARY_DIVERSITY_RUNTIME_ABSENT",
        "required_gates": list(REQUIRED_GATES),
        "hard_exclusion_order": list(HARD_EXCLUSION_ORDER),
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
                "Fixture records prove cooldown, near-duplicate penalties, foot "
                "alternation, history binding, and bounded-variation rejection; they do "
                "not accept Row082 library completion or repeated-event runtime proof."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row082_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows074, 080, and 081; freeze an immutable selection-history "
                "ledger with atomic claim semantics; enforce cooldown, near-duplicate, "
                "alternation, continuity, and bounded-variation gates; run held-out "
                "repeated-event benchmarks proving diversity without semantic drift or "
                "continuity breaks; then replace this hold packet."
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
    parser.add_argument("--fixture", default="cooldown_blocks_identical_reuse")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise RepetitionDiversityError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise RepetitionDiversityError(
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
