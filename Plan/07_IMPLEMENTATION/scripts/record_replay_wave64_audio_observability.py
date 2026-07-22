#!/usr/bin/env python3
"""Record and replay the fail-closed Wave64 Row110 audio run ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_row110_audio_observability_replay_policy_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_observability_run_ledger.schema.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-110_audio_observability_replay.json")
POLICY_REVISION = "wave64_row110_audio_observability_replay_policy_v0.1.0"
ZERO_HASH = "0" * 64
REQUIRED_EVENT_TYPES = {
    "stage_timing", "model_identity", "cache_observation",
    "candidate_ranking", "transform_lineage", "mix_decision",
    "qa_score", "authority_decision",
}
DEPENDENCY_DELTAS = {
    "TRK-W64-102": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-102_GENERATED_ASSET_PROVENANCE_CURRENT_DELTA_20260719.json"),
    "TRK-W64-105": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-105_AUDIO_END_TO_END_ORCHESTRATOR_CURRENT_DELTA_20260722.json"),
    "TRK-W64-106": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-106_AUDIO_AV_QA_MATRIX_CURRENT_DELTA_20260722.json"),
}


class AudioObservabilityError(ValueError):
    """Raised when a ledger cannot be replayed without ambiguity."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row110:{label}".encode()).hexdigest()


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def new_ledger(label: str, *, synthetic: bool) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "tracker_id": "TRK-W64-110", "item_id": "ITEM-W64-110",
        "record_type": "audio_observability_run_ledger", "policy_revision": POLICY_REVISION,
        "run_id": f"audio-run-{stable_hash(label)[:24]}", "is_synthetic": synthetic,
        "events": [], "recorded_projection": {}, "decision": {}, "ledger_sha256": ZERO_HASH,
    }


def append_event(ledger: dict[str, Any], event_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(ledger)
    if result.get("ledger_sha256") not in {None, ZERO_HASH}:
        raise AudioObservabilityError("sealed_ledger_is_immutable")
    if event_id in {event["event_id"] for event in result["events"]}:
        raise AudioObservabilityError("duplicate_event_id")
    body = {
        "sequence": len(result["events"]) + 1, "event_id": event_id,
        "event_type": event_type, "payload": payload, "payload_sha256": digest(payload),
        "previous_event_sha256": result["events"][-1]["event_sha256"] if result["events"] else ZERO_HASH,
    }
    result["events"].append({**body, "event_sha256": digest(body)})
    return result


def replay(events: list[dict[str, Any]]) -> dict[str, Any]:
    prior = ZERO_HASH
    seen_ids = set()
    counts: dict[str, int] = {}
    projection = {
        "event_count": len(events), "event_type_counts": counts,
        "model_sha256s": [], "cache_hits": 0, "ranked_candidate_ids": [],
        "rejected_candidate_ids": [], "transform_sha256s": [], "mix_sha256": None,
        "qa_evidence_sha256s": [], "retry_count": 0,
        "authority_evidence_sha256": None, "final_artifact_sha256": None,
        "external_blocker_codes": [], "reconstructable": False,
    }
    for index, event in enumerate(events, start=1):
        if event["sequence"] != index or event["previous_event_sha256"] != prior:
            raise AudioObservabilityError("event_chain_sequence_or_parent_mismatch")
        if event["event_id"] in seen_ids:
            raise AudioObservabilityError("duplicate_event_id")
        seen_ids.add(event["event_id"])
        if event["payload_sha256"] != digest(event["payload"]):
            raise AudioObservabilityError("payload_sha256_mismatch")
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        if event["event_sha256"] != digest(body):
            raise AudioObservabilityError("event_sha256_mismatch")
        prior = event["event_sha256"]
        event_type, payload = event["event_type"], event["payload"]
        counts[event_type] = counts.get(event_type, 0) + 1
        if event_type == "model_identity":
            projection["model_sha256s"].append(payload["model_sha256"])
        elif event_type == "cache_observation" and payload.get("cache_hit") is True:
            projection["cache_hits"] += 1
        elif event_type == "candidate_ranking":
            projection["ranked_candidate_ids"].extend(payload["candidate_ids"])
        elif event_type == "candidate_rejection":
            projection["rejected_candidate_ids"].append(payload["candidate_id"])
        elif event_type == "transform_lineage":
            projection["transform_sha256s"].append(payload["transform_sha256"])
        elif event_type == "mix_decision":
            projection["mix_sha256"] = payload["mix_sha256"]
        elif event_type == "qa_score":
            projection["qa_evidence_sha256s"].append(payload["evidence_sha256"])
        elif event_type == "retry":
            projection["retry_count"] += 1
        elif event_type == "authority_decision":
            projection["authority_evidence_sha256"] = payload["authority_evidence_sha256"]
            projection["final_artifact_sha256"] = payload.get("final_artifact_sha256")
        elif event_type == "external_blocker":
            projection["external_blocker_codes"].append(payload["blocker_code"])
    for key in ("model_sha256s", "ranked_candidate_ids", "rejected_candidate_ids", "transform_sha256s", "qa_evidence_sha256s", "external_blocker_codes"):
        projection[key] = list(dict.fromkeys(projection[key]))
    present = set(counts)
    has_lineage = projection["mix_sha256"] is not None and projection["authority_evidence_sha256"] is not None
    projection["reconstructable"] = REQUIRED_EVENT_TYPES <= present and has_lineage
    return projection


def seal_ledger(root: Path, ledger: dict[str, Any], *, release_authority: bool) -> dict[str, Any]:
    result = deepcopy(ledger)
    projection = replay(result["events"])
    blockers = []
    missing_types = sorted(REQUIRED_EVENT_TYPES - set(projection["event_type_counts"]))
    if missing_types:
        blockers.extend(f"MISSING_EVENT_TYPE_{value.upper()}" for value in missing_types)
    if not projection["reconstructable"]:
        blockers.append("RUN_NOT_RECONSTRUCTABLE")
    if release_authority:
        if result["is_synthetic"]:
            blockers.append("SYNTHETIC_RELEASE_FORBIDDEN")
        if projection["external_blocker_codes"]:
            blockers.append("UNRESOLVED_EXTERNAL_BLOCKERS")
        if projection["final_artifact_sha256"] is None:
            blockers.append("FINAL_ARTIFACT_HASH_ABSENT")
    if release_authority and blockers:
        raise AudioObservabilityError("release_authority_requirements_unsatisfied")
    result["recorded_projection"] = projection
    result["decision"] = {
        "status": "pass" if not blockers else "blocked", "release_authority": release_authority,
        "row110_acceptance": "fixture_only" if result["is_synthetic"] and not blockers else ("accepted" if release_authority else "held"),
        "blocker_codes": blockers,
    }
    result["ledger_sha256"] = digest({key: value for key, value in result.items() if key != "ledger_sha256"})
    validate_ledger(root, result)
    return result


def validate_ledger(root: Path, ledger: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(ledger)
    observed = ledger["ledger_sha256"]
    expected = digest({key: value for key, value in ledger.items() if key != "ledger_sha256"})
    if observed != expected:
        raise AudioObservabilityError("ledger_sha256_mismatch")
    replayed = replay(ledger["events"])
    if replayed != ledger["recorded_projection"]:
        raise AudioObservabilityError("recorded_projection_replay_mismatch")
    if ledger["decision"]["release_authority"] and not replayed["reconstructable"]:
        raise AudioObservabilityError("release_not_reconstructable")


def fixture_ledger(root: Path) -> dict[str, Any]:
    ledger = new_ledger("complete-fixture", synthetic=True)
    fixture_events = [
        ("e01", "stage_timing", {"stage_id": "analysis", "duration_ms": 12.0}),
        ("e02", "model_identity", {"model_id": "fixture-model", "model_sha256": stable_hash("model")}),
        ("e03", "cache_observation", {"cache_key": stable_hash("cache"), "cache_hit": True}),
        ("e04", "candidate_ranking", {"candidate_ids": ["candidate-a", "candidate-b"], "ranking_sha256": stable_hash("ranking")}),
        ("e05", "candidate_rejection", {"candidate_id": "candidate-b", "reason_codes": ["SEMANTIC_MISMATCH"]}),
        ("e06", "transform_lineage", {"input_sha256": stable_hash("input"), "transform_sha256": stable_hash("transform"), "output_sha256": stable_hash("transformed")}),
        ("e07", "mix_decision", {"mix_sha256": stable_hash("mix"), "decision_sha256": stable_hash("mix-decision")}),
        ("e08", "qa_score", {"evidence_sha256": stable_hash("qa"), "status": "pass"}),
        ("e09", "authority_decision", {"authority_evidence_sha256": stable_hash("authority"), "final_artifact_sha256": stable_hash("artifact"), "status": "fixture_only"}),
    ]
    for event_id, event_type, payload in fixture_events:
        ledger = append_event(ledger, event_id, event_type, payload)
    return seal_ledger(root, ledger, release_authority=False)


def dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for tracker, relative in DEPENDENCY_DELTAS.items():
        path = root / relative
        payload = load_json(path) if path.is_file() else {}
        complete = payload.get("row_complete") is True
        status = str(payload.get("status", "ABSENT"))
        result[tracker] = {"path": relative.as_posix(), "sha256": sha256_file(path) if path.is_file() else ZERO_HASH,
                           "row_complete": complete, "dependency_satisfied": complete and not status.lower().startswith("hold"), "status": status}
    return result


def build_evidence(root: Path) -> dict[str, Any]:
    fixture = fixture_ledger(root)
    blocked = new_ledger("live-held", synthetic=False)
    blocked = append_event(blocked, "b01", "external_blocker", {"blocker_code": "ROW110_DEPENDENCIES_NOT_ACCEPTED", "evidence_sha256": stable_hash("dependency-blocker")})
    blocked = seal_ledger(root, blocked, release_authority=False)
    admissions = dependency_admissions(root)
    return {
        "schema_version": "1.0.0", "evidence_id": "TRK-W64-110_audio_observability_replay",
        "tracker_id": "TRK-W64-110", "item_id": "ITEM-W64-110",
        "status": "HOLD_DEPENDENCIES_AND_GENUINE_RUN_REPLAY_ABSENT_WITH_FAIL_CLOSED_LEDGER_PRESENT",
        "row_complete": False, "implementation_completion_claimed": True, "runtime_completion_claimed": False,
        "dependency_admissions": admissions, "fixture_replay": fixture, "live_blocker_ledger": blocked,
        "implementation": {"script": str(Path(__file__).resolve().relative_to(root)).replace("\\", "/"), "script_sha256": sha256_file(Path(__file__).resolve()),
                           "schema": SCHEMA_PATH.as_posix(), "schema_sha256": sha256_file(root / SCHEMA_PATH),
                           "policy": POLICY_PATH.as_posix(), "policy_sha256": sha256_file(root / POLICY_PATH)},
        "decision": {"status": "blocked", "row110_acceptance": "held", "product_completion": False,
                     "blocker_codes": ["ROW110_DEPENDENCIES_NOT_ACCEPTED", "GENUINE_RELEASE_OR_PROMOTION_RUN_REPLAY_ABSENT"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--emit-evidence", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build_evidence(root)
    output = args.output or (root / DEFAULT_EVIDENCE if args.emit_evidence else None)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
