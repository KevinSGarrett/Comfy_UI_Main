#!/usr/bin/env python3
"""Fail-closed Wave64 Row092 event uncertainty/fallback policy slice.

Production authority refuses until Row091 is accepted. Fixture mode may emit
deterministic schema-validated decisions that preserve detector votes, derive
fallback routes, and reject self-declared certification without evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/event_uncertainty_fallback_decision.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row092_event_uncertainty_fallback_policy_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-092_event_uncertainty_fallback.json"
)
DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-091": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"
    ),
}

ENGINE_REVISION = "wave64_row092_event_uncertainty_fallback_engine_v0.1.0"
POLICY_REVISION = "wave64_row092_event_uncertainty_fallback_policy_v0.1.0"
TRACKER_ID = "TRK-W64-092"
ITEM_ID = "ITEM-W64-092"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "conflict_resolution",
    "uncertainty_preserved",
    "offscreen_policy",
    "fallback_route",
    "certification_ceiling",
)

AUTHORITY_RANK = {"candidate": 0, "technical": 1, "certification": 2}
ROUTE_PRIORITY = (
    "blocked",
    "intentional_silence",
    "multi_anchor_sync",
    "generated_candidate",
    "broader_retrieval",
    "exact_library",
)

FIXTURE_NAMES = (
    "adversarial_self_declared_certification_blocked",
    "detector_conflict_preserves_votes",
    "unknown_material_routes_fallback",
    "offscreen_event_intentional_silence",
    "occluded_contact_candidate_only",
)


class EventUncertaintyFallbackError(ValueError):
    """Raised when Row092 policy violates fail-closed authority."""


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
        raise EventUncertaintyFallbackError(f"{label}_outside_project_root") from exc
    return path


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise EventUncertaintyFallbackError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise EventUncertaintyFallbackError("policy_required_gates_mismatch")
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
            "sha256": "0" * 64,
            "bytes": 0,
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    status_text = str(payload.get("status", "")).lower()
    exact_acceptance = str(decision.get("row091_acceptance", "")).lower()
    accepted_markers = {"accepted", "pass", "passed"}
    coarse_markers = [
        exact_acceptance,
        str(decision.get("status", "")).lower(),
        str(payload.get("qa_decision", "")).lower(),
    ]
    acceptance_hit = any(marker in accepted_markers for marker in coarse_markers if marker)
    if status_text.startswith("hold") or hold_text.startswith("hold"):
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


def min_authority(left: str, right: str) -> str:
    return left if AUTHORITY_RANK[left] <= AUTHORITY_RANK[right] else right


def stricter_route(left: str, right: str) -> str:
    return left if ROUTE_PRIORITY.index(left) <= ROUTE_PRIORITY.index(right) else right


def is_unknown_material(material: str, policy: dict[str, Any]) -> bool:
    tokens = {str(t).lower() for t in policy["thresholds"]["unknown_material_tokens"]}
    return str(material or "").strip().lower() in tokens or not str(material or "").strip()


def vote_identity(vote: dict[str, Any]) -> tuple[Any, ...]:
    return (
        vote.get("event_type"),
        vote.get("source_owner"),
        vote.get("target_owner"),
        vote.get("material"),
    )


def select_vote(votes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not votes:
        return None
    ordered = sorted(
        votes,
        key=lambda vote: (-float(vote["confidence"]), str(vote["detector_name"])),
    )
    return ordered[0]


def compute_disagreement(votes: list[dict[str, Any]]) -> float:
    if len(votes) <= 1:
        return 0.0
    identities = [vote_identity(vote) for vote in votes]
    unique = {identity for identity in identities}
    if len(unique) == 1:
        return 0.0
    confidences = [float(vote["confidence"]) for vote in votes]
    spread = max(confidences) - min(confidences)
    return max(0.25, min(1.0, (len(unique) - 1) / len(votes) + 0.5 * spread))


def fixture_observations() -> dict[str, dict[str, Any]]:
    return {
        "adversarial_self_declared_certification_blocked": {
            "event_id": "evt_adversarial_zero_evidence",
            "declared_authority_ceiling": "certification",
            "scene_flags": {
                "occlusion": False,
                "offscreen": False,
                "cut_boundary": False,
                "crowded_scene": False,
                "intentionally_silent": False,
            },
            "ambiguous_onset": False,
            "evidence_empty": True,
            "detector_votes": [
                {
                    "detector_name": "contact_detector",
                    "detector_revision": "r0",
                    "event_type": "unknown_contact",
                    "source_owner": None,
                    "target_owner": None,
                    "material": "unknown",
                    "confidence": 0.0,
                    "evidence_ref": "empty",
                }
            ],
        },
        "detector_conflict_preserves_votes": {
            "event_id": "evt_conflict_foot_vs_hand",
            "declared_authority_ceiling": "technical",
            "scene_flags": {
                "occlusion": False,
                "offscreen": False,
                "cut_boundary": False,
                "crowded_scene": False,
                "intentionally_silent": False,
            },
            "ambiguous_onset": False,
            "evidence_empty": False,
            "detector_votes": [
                {
                    "detector_name": "contact_detector",
                    "detector_revision": "r2",
                    "event_type": "footstep",
                    "source_owner": "character_1",
                    "target_owner": "floor_1",
                    "material": "wood",
                    "confidence": 0.72,
                    "evidence_ref": "contact_a",
                },
                {
                    "detector_name": "pose_detector",
                    "detector_revision": "r2",
                    "event_type": "hand_body_contact",
                    "source_owner": "character_1",
                    "target_owner": "character_1",
                    "material": "skin",
                    "confidence": 0.68,
                    "evidence_ref": "pose_b",
                },
            ],
        },
        "unknown_material_routes_fallback": {
            "event_id": "evt_unknown_material",
            "declared_authority_ceiling": "certification",
            "scene_flags": {
                "occlusion": False,
                "offscreen": False,
                "cut_boundary": False,
                "crowded_scene": False,
                "intentionally_silent": False,
            },
            "ambiguous_onset": False,
            "evidence_empty": False,
            "detector_votes": [
                {
                    "detector_name": "material_detector",
                    "detector_revision": "r1",
                    "event_type": "footstep",
                    "source_owner": "character_1",
                    "target_owner": "floor_1",
                    "material": "unknown",
                    "confidence": 0.9,
                    "evidence_ref": "mat_unresolved",
                }
            ],
        },
        "offscreen_event_intentional_silence": {
            "event_id": "evt_offscreen_door",
            "declared_authority_ceiling": "technical",
            "scene_flags": {
                "occlusion": False,
                "offscreen": True,
                "cut_boundary": False,
                "crowded_scene": False,
                "intentionally_silent": True,
            },
            "ambiguous_onset": False,
            "evidence_empty": False,
            "detector_votes": [
                {
                    "detector_name": "scene_continuity",
                    "detector_revision": "r1",
                    "event_type": "door_close",
                    "source_owner": "prop_door",
                    "target_owner": "frame_1",
                    "material": "wood",
                    "confidence": 0.6,
                    "evidence_ref": "offscreen_audio_cue",
                }
            ],
        },
        "occluded_contact_candidate_only": {
            "event_id": "evt_occluded_hand_contact",
            "declared_authority_ceiling": "certification",
            "scene_flags": {
                "occlusion": True,
                "offscreen": False,
                "cut_boundary": False,
                "crowded_scene": True,
                "intentionally_silent": False,
            },
            "ambiguous_onset": True,
            "evidence_empty": False,
            "detector_votes": [
                {
                    "detector_name": "mask_detector",
                    "detector_revision": "r3",
                    "event_type": "hand_body_contact",
                    "source_owner": "character_1",
                    "target_owner": "character_2",
                    "material": "fabric",
                    "confidence": 0.8,
                    "evidence_ref": "mask_partial",
                }
            ],
        },
    }


def derive_decision(
    root: Path,
    observation: dict[str, Any],
    *,
    is_synthetic: bool,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    votes = deepcopy(observation["detector_votes"])
    if not votes:
        raise EventUncertaintyFallbackError("detector_votes_required")

    selected = select_vote(votes)
    disagreement = compute_disagreement(votes)
    conflict_present = disagreement >= float(policy["thresholds"]["conflict_disagreement_floor"])
    if conflict_present:
        resolution = "majority_confidence"
    else:
        resolution = "unanimous"

    reason_codes: list[str] = []
    uncertainty_sources: list[str] = []
    derived_ceiling = "certification"
    route = "exact_library"
    status = "proceed"
    sync_class = "frame_exact"

    if not admissions["TRK-W64-091"]["dependency_satisfied"]:
        reason_codes.append("DEPENDENCY_ROW091_NOT_ACCEPTED")
        # Synthetic fixtures still exercise observation-driven routes; production
        # and hold packets remain fail-closed until Row091 is accepted.
        if not is_synthetic:
            derived_ceiling = min_authority(derived_ceiling, "candidate")
            route = stricter_route(route, "blocked")
            status = "blocked"
            sync_class = "none"

    scene_flags = dict(observation["scene_flags"])
    thresholds = policy["thresholds"]
    selected_material = selected["material"] if selected else None
    selected_source = selected["source_owner"] if selected else None
    selected_target = selected["target_owner"] if selected else None
    selected_event_type = selected["event_type"] if selected else None
    max_confidence = max(float(vote["confidence"]) for vote in votes)

    if conflict_present:
        reason_codes.append("DETECTOR_CONFLICT")
        uncertainty_sources.append("detector_disagreement")
        derived_ceiling = min_authority(derived_ceiling, "technical")
        route = stricter_route(route, "broader_retrieval")
        status = "fallback" if status == "proceed" else status

    if max_confidence < float(thresholds["technical_min_confidence"]):
        reason_codes.append("LOW_CONFIDENCE")
        uncertainty_sources.append("low_confidence")
        derived_ceiling = min_authority(derived_ceiling, "candidate")
        route = stricter_route(route, "generated_candidate")
        status = "fallback" if status == "proceed" else status
        sync_class = "windowed"
    elif max_confidence < float(thresholds["certification_min_confidence"]):
        reason_codes.append("LOW_CONFIDENCE")
        uncertainty_sources.append("low_confidence")
        derived_ceiling = min_authority(derived_ceiling, "technical")

    if selected_source is None or selected_target is None:
        reason_codes.append("NULL_OWNERSHIP")
        uncertainty_sources.append("null_ownership")
        derived_ceiling = min_authority(derived_ceiling, "candidate")
        route = stricter_route(route, "generated_candidate")
        status = "fallback" if status == "proceed" else status

    if selected_material is not None and is_unknown_material(selected_material, policy):
        reason_codes.append("UNKNOWN_MATERIAL")
        uncertainty_sources.append("unknown_material")
        derived_ceiling = min_authority(derived_ceiling, "candidate")
        route = stricter_route(route, "broader_retrieval")
        status = "fallback" if status == "proceed" else status

    if scene_flags.get("occlusion"):
        reason_codes.append("OCCLUSION")
        uncertainty_sources.append("occlusion")
        derived_ceiling = min_authority(derived_ceiling, policy["scene_ceiling_caps"]["occlusion"])
        route = stricter_route(route, "generated_candidate")
        status = "fallback" if status == "proceed" else status
        sync_class = "windowed"

    if scene_flags.get("crowded_scene"):
        reason_codes.append("CROWDED_SCENE")
        uncertainty_sources.append("crowded_scene")
        derived_ceiling = min_authority(
            derived_ceiling, policy["scene_ceiling_caps"]["crowded_scene"]
        )

    if scene_flags.get("cut_boundary"):
        reason_codes.append("CUT_BOUNDARY")
        uncertainty_sources.append("cut_boundary")
        derived_ceiling = min_authority(
            derived_ceiling, policy["scene_ceiling_caps"]["cut_boundary"]
        )
        route = stricter_route(route, "multi_anchor_sync")
        status = "fallback" if status == "proceed" else status
        sync_class = "multi_anchor"

    if scene_flags.get("offscreen"):
        reason_codes.append("OFFSCREEN")
        uncertainty_sources.append("offscreen")
        derived_ceiling = min_authority(derived_ceiling, policy["scene_ceiling_caps"]["offscreen"])
        if scene_flags.get("intentionally_silent"):
            reason_codes.append("INTENTIONAL_SILENCE")
            uncertainty_sources.append("offscreen")
            route = stricter_route(route, "intentional_silence")
            status = "intentional_silence"
            sync_class = "none"
        else:
            route = stricter_route(route, "generated_candidate")
            status = "fallback" if status == "proceed" else status
            sync_class = "windowed"

    if observation.get("ambiguous_onset"):
        reason_codes.append("AMBIGUOUS_ONSET")
        uncertainty_sources.append("ambiguous_onset")
        derived_ceiling = min_authority(derived_ceiling, "technical")
        route = stricter_route(route, "multi_anchor_sync")
        status = "fallback" if status == "proceed" else status
        sync_class = "multi_anchor"

    if observation.get("evidence_empty"):
        reason_codes.append("EMPTY_EVIDENCE")
        uncertainty_sources.append("low_confidence")
        derived_ceiling = min_authority(derived_ceiling, "candidate")
        route = stricter_route(route, "blocked")
        status = "blocked"
        sync_class = "none"

    declared = observation.get("declared_authority_ceiling")
    if (
        declared == "certification"
        and AUTHORITY_RANK[derived_ceiling] < AUTHORITY_RANK["certification"]
    ):
        reason_codes.append("SELF_DECLARED_CERTIFICATION_REJECTED")
        route = stricter_route(route, "blocked")
        status = "blocked"
        sync_class = "none"

    if not uncertainty_sources:
        uncertainty_sources = ["low_confidence"] if max_confidence < 1.0 else ["low_confidence"]
        if max_confidence >= float(thresholds["certification_min_confidence"]) and not conflict_present:
            uncertainty_sources = ["low_confidence"]
            # Keep a machine-readable uncertainty object even on strong agreement.
            uncertainty_value = max(0.0, 1.0 - max_confidence)
        else:
            uncertainty_value = max(disagreement, 1.0 - max_confidence)
    else:
        uncertainty_value = max(disagreement, 1.0 - max_confidence)
        if "unknown_material" in uncertainty_sources:
            uncertainty_value = max(uncertainty_value, 0.75)
        if "null_ownership" in uncertainty_sources:
            uncertainty_value = max(uncertainty_value, 0.8)
        if "offscreen" in uncertainty_sources or "occlusion" in uncertainty_sources:
            uncertainty_value = max(uncertainty_value, 0.7)

    uncertainty_value = min(1.0, round(uncertainty_value, 6))
    reason_codes = sorted(set(reason_codes))
    uncertainty_sources = sorted(set(uncertainty_sources))

    observation_canonical = {
        "event_id": observation["event_id"],
        "declared_authority_ceiling": declared,
        "scene_flags": scene_flags,
        "ambiguous_onset": bool(observation.get("ambiguous_onset")),
        "evidence_empty": bool(observation.get("evidence_empty")),
        "detector_votes": votes,
    }
    observation_sha256 = sha256_bytes(canonical_json_bytes(observation_canonical))

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "event_uncertainty_fallback_decision",
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "event_id": observation["event_id"],
        "observation_sha256": observation_sha256,
        "is_synthetic": is_synthetic,
        "production_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "detector_votes": votes,
        "conflict_record": {
            "conflict_present": conflict_present,
            "disagreement_metric": round(disagreement, 6),
            "tie_policy": policy["tie_policy"],
            "preserved_vote_count": len(votes),
            "selected_detector_name": selected["detector_name"] if selected else None,
            "resolution": resolution,
        },
        "uncertainty": {
            "value": uncertainty_value,
            "sources": uncertainty_sources,
            "propagation": "event_local",
            "calibration_revision": policy["calibration_revision"],
            "ceiling_effect": derived_ceiling,
        },
        "scene_flags": scene_flags,
        "fallback_route": route,
        "fallback_reason_codes": reason_codes,
        "declared_authority_ceiling": declared,
        "derived_authority_ceiling": derived_ceiling,
        "decision": {
            "status": status,
            "route": route,
            "product_completion": False,
            "row092_acceptance": "fixture_only" if is_synthetic else "held",
            "selected_event_type": selected_event_type,
            "selected_material": selected_material,
            "selected_source_owner": selected_source,
            "selected_target_owner": selected_target,
            "sync_class": sync_class,
        },
    }
    sealed = {key: value for key, value in record.items() if key != "receipt_sha256"}
    record["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    validate_decision_record(root, record)
    return record


def validate_decision_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda err: list(err.path),
    )
    if errors:
        raise EventUncertaintyFallbackError(
            "schema_validation_failed:" + errors[0].message
        )
    if record["production_authority"] is not False:
        raise EventUncertaintyFallbackError("production_authority_must_be_false")
    if record["decision"]["product_completion"] is not False:
        raise EventUncertaintyFallbackError("product_completion_must_be_false")
    declared = record.get("declared_authority_ceiling")
    derived = record["derived_authority_ceiling"]
    if (
        declared == "certification"
        and AUTHORITY_RANK[derived] < AUTHORITY_RANK["certification"]
        and "SELF_DECLARED_CERTIFICATION_REJECTED" not in record["fallback_reason_codes"]
    ):
        raise EventUncertaintyFallbackError("self_declared_certification_not_rejected")
    if record["conflict_record"]["preserved_vote_count"] != len(record["detector_votes"]):
        raise EventUncertaintyFallbackError("conflict_vote_preservation_mismatch")
    if not record["uncertainty"]["sources"]:
        raise EventUncertaintyFallbackError("uncertainty_sources_required")


def extract_fixture_record(root: Path, fixture_name: str) -> dict[str, Any]:
    observations = fixture_observations()
    if fixture_name not in observations:
        raise EventUncertaintyFallbackError(f"unknown_fixture:{fixture_name}")
    return derive_decision(root, observations[fixture_name], is_synthetic=True)


def build_hold_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW092_DEPENDENCY_ROW091_NOT_ACCEPTED")
    for code in (
        "PRODUCTION_EVENT_UNCERTAINTY_RUNTIME_ABSENT",
        "COMBINED_FRAME_CONTACT_AUDIO_REVIEW_ABSENT",
        "GENUINE_FIXTURE_RUNTIME_PROOF_ABSENT",
        "STRICT_ROW091_MANIFEST_AUTHORITY_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-092_event_uncertainty_fallback",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "production_authority": False,
        "status": "HOLD_DEPENDENCY_ROW091_AND_RUNTIME_VISUAL_QA_ABSENT",
        "required_gates": list(REQUIRED_GATES),
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
            "authority": "synthetic_non_production",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture decisions prove detector-vote preservation, conflict resolution, "
                "unknown-material fallback, offscreen intentional silence, occlusion "
                "candidate ceiling, and rejection of self-declared certification; they do "
                "not accept Row092 production completion or combined visual/audio review."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row092_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row091 strict hash-bound visual event manifest authority; bind "
                "production observations into this policy engine; prove conflict, "
                "occlusion, cut, offscreen, unknown-material, and silence fixtures under "
                "combined frame/contact/audio review; then replace this hold packet."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("hold", "fixture"), default="hold")
    parser.add_argument("--fixture", default="adversarial_self_declared_certification_blocked")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise EventUncertaintyFallbackError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_hold_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise EventUncertaintyFallbackError(
                "hold_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
        if payload["row_complete"] is not False:
            raise EventUncertaintyFallbackError("row_complete_must_remain_false")
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["status"],
                "row_complete": payload.get("row_complete", False),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
