#!/usr/bin/env python3
"""Fail-closed Row105 content-addressed audio orchestration state machine."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_orchestration_state.schema.json")
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_row105_audio_orchestrator_policy_registry.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-105_audio_end_to_end_orchestrator.json")
ORCHESTRATOR_REVISION = "wave64_row105_audio_orchestrator_v0.1.0"
POLICY_REVISION = "wave64_row105_audio_orchestrator_policy_v0.1.0"
TRACKER_ID = "TRK-W64-105"
ITEM_ID = "ITEM-W64-105"
SCHEMA_VERSION = "1.0.0"
ZERO_HASH = "0" * 64
DEPENDENCY_DELTAS = {
    "TRK-W64-083": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-083_RETRIEVAL_FALLBACK_CALIBRATION_CURRENT_DELTA_20260719.json"),
    "TRK-W64-092": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-092_EVENT_UNCERTAINTY_FALLBACK_CURRENT_DELTA_20260719.json"),
    "TRK-W64-097": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-097_SAMPLE_ACCURATE_MIX_MUX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-104": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-104_GENERATED_ASSET_PROMOTION_CURRENT_DELTA_20260722.json"),
}


class AudioOrchestratorError(ValueError):
    """Raised when a Row105 transition violates orchestration authority."""


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row105:{label}".encode()).hexdigest()


def resolve_under(root: Path, relative: Path, label: str) -> Path:
    path = relative.resolve() if relative.is_absolute() else (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AudioOrchestratorError(f"{label}_outside_project_root") from exc
    return path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    policy = load_json(resolve_under(root, POLICY_PATH, "policy"))
    if policy.get("revision") != POLICY_REVISION:
        raise AudioOrchestratorError("policy_revision_mismatch")
    return policy


def dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for tracker_id, relative in DEPENDENCY_DELTAS.items():
        path = resolve_under(root, relative, tracker_id.lower())
        present = path.is_file()
        payload = load_json(path) if present else {}
        complete = present and payload.get("row_complete") is True
        result[tracker_id] = {
            "tracker_id": tracker_id,
            "evidence_path": relative.as_posix(),
            "evidence_sha256": sha256_file(path) if present else ZERO_HASH,
            "row_complete": complete,
            "dependency_satisfied": complete,
            "blocker_codes": [] if complete else [f"{tracker_id.replace('-', '_')}_{'NOT_ACCEPTED' if present else 'DELTA_ABSENT'}"],
        }
    return result


def accepted_fixture_dependencies() -> dict[str, dict[str, Any]]:
    return {
        tracker_id: {
            "tracker_id": tracker_id,
            "evidence_path": path.as_posix(),
            "evidence_sha256": stable_hash(f"accepted:{tracker_id}"),
            "row_complete": True,
            "dependency_satisfied": True,
            "blocker_codes": [],
        }
        for tracker_id, path in DEPENDENCY_DELTAS.items()
    }


def _stage_inputs(run: dict[str, Any], stage: dict[str, Any]) -> list[str]:
    outputs = {item["stage_id"]: item["output_sha256"] for item in run["stages"]}
    values = [run["request_sha256"]]
    values.extend(outputs[pred] for pred in stage["predecessors"])
    if any(value is None for value in values):
        raise AudioOrchestratorError("predecessor_output_missing")
    return sorted(set(values))


def _stage_key(request_sha256: str, stage_id: str, revision: str, input_hashes: list[str]) -> str:
    return digest({"request_sha256": request_sha256, "stage_id": stage_id, "implementation_revision": revision, "input_hashes": input_hashes})


def _seal(run: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(run)
    sealed["receipt_sha256"] = digest(run)
    return sealed


def _unseal(run: dict[str, Any]) -> dict[str, Any]:
    body = deepcopy(run)
    receipt = body.pop("receipt_sha256", None)
    if receipt != digest(body):
        raise AudioOrchestratorError("receipt_sha256_mismatch")
    return body


def _append_event(run: dict[str, Any], event_type: str, stage_id: str, payload: Any) -> None:
    previous = run["event_log"][-1]["event_sha256"] if run["event_log"] else ZERO_HASH
    body = {
        "sequence": len(run["event_log"]) + 1,
        "event_type": event_type,
        "stage_id": stage_id,
        "payload_sha256": digest(payload),
        "previous_event_sha256": previous,
    }
    run["event_log"].append({**body, "event_sha256": digest(body)})


def _refresh_ready(run: dict[str, Any]) -> None:
    states = {item["stage_id"]: item["state"] for item in run["stages"]}
    if not all(item["dependency_satisfied"] for item in run["dependency_admissions"].values()):
        return
    for stage in run["stages"]:
        if stage["state"] != "pending":
            continue
        if all(states[pred] in {"pass", "reused"} for pred in stage["predecessors"]):
            stage["state"] = "ready"
            stage["input_hashes"] = _stage_inputs(run, stage)
            stage["idempotency_key"] = _stage_key(run["request_sha256"], stage["stage_id"], stage["implementation_revision"], stage["input_hashes"])
            states[stage["stage_id"]] = "ready"


def compile_run(
    root: Path,
    *,
    request: dict[str, Any],
    is_synthetic: bool,
    admissions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    policy = load_policy(root)
    request_sha = digest(request)
    deps = admissions or dependency_admissions(root)
    stage_specs = policy["mandatory_stages"]
    dag_sha = digest(stage_specs)
    stages = []
    for spec in stage_specs:
        stages.append({
            "stage_id": spec["stage_id"],
            "predecessors": spec["predecessors"],
            "implementation_revision": f"{spec['stage_id']}_v1",
            "state": "pending",
            "attempts": 0,
            "idempotency_key": stable_hash(f"pending:{spec['stage_id']}"),
            "input_hashes": [],
            "output_sha256": None,
            "blocker_codes": [],
        })
    dependency_blockers = [code for item in deps.values() for code in item["blocker_codes"]]
    body = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "audio_orchestration_state",
        "orchestrator_revision": ORCHESTRATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(resolve_under(root, POLICY_PATH, "policy")),
        "run_id": f"audio-run-{digest({'request': request_sha, 'dag': dag_sha})[:24]}",
        "request_sha256": request_sha,
        "is_synthetic": is_synthetic,
        "dependency_admissions": deps,
        "dag_sha256": dag_sha,
        "stages": stages,
        "retry_budget": {"global_max_attempts": policy["global_max_attempts"], "global_used_attempts": 0, "per_stage_max_attempts": policy["per_stage_max_attempts"]},
        "cost_budget": {"maximum_usd": policy["maximum_fixture_cost_usd"], "committed_usd": 0.0, "currency": "USD"},
        "event_log": [],
        "decision": {"status": "blocked" if dependency_blockers else "ready", "row105_acceptance": "held", "runtime_completion": False, "publication_allowed": False, "blocker_codes": sorted(set(dependency_blockers + (["ROW105_DEPENDENCIES_NOT_ACCEPTED"] if dependency_blockers else [])))},
    }
    _refresh_ready(body)
    sealed = _seal(body)
    validate_run(root, sealed)
    return sealed


def complete_stage(root: Path, run: dict[str, Any], stage_id: str, output_sha256: str, *, cost_usd: float = 0.0) -> dict[str, Any]:
    body = _unseal(run)
    stage = next((item for item in body["stages"] if item["stage_id"] == stage_id), None)
    if stage is None:
        raise AudioOrchestratorError("unknown_stage")
    if stage["state"] in {"pass", "reused"}:
        if stage["output_sha256"] != output_sha256:
            raise AudioOrchestratorError("immutable_passed_stage_output_mismatch")
        return run
    if stage["state"] != "ready":
        raise AudioOrchestratorError("stage_not_ready")
    if body["retry_budget"]["global_used_attempts"] >= body["retry_budget"]["global_max_attempts"]:
        raise AudioOrchestratorError("global_retry_budget_exhausted")
    if stage["attempts"] >= body["retry_budget"]["per_stage_max_attempts"]:
        raise AudioOrchestratorError("stage_retry_budget_exhausted")
    if body["cost_budget"]["committed_usd"] + cost_usd > body["cost_budget"]["maximum_usd"]:
        raise AudioOrchestratorError("cost_budget_exceeded")
    stage["attempts"] += 1
    body["retry_budget"]["global_used_attempts"] += 1
    body["cost_budget"]["committed_usd"] = round(body["cost_budget"]["committed_usd"] + cost_usd, 6)
    stage["state"] = "pass"
    stage["output_sha256"] = output_sha256
    stage["blocker_codes"] = []
    _append_event(body, "stage_passed", stage_id, {"output_sha256": output_sha256, "attempt": stage["attempts"], "cost_usd": cost_usd})
    _refresh_ready(body)
    all_pass = all(item["state"] in {"pass", "reused"} for item in body["stages"])
    if all_pass:
        body["decision"] = {
            "status": "complete",
            "row105_acceptance": "fixture_only" if body["is_synthetic"] else "accepted",
            "runtime_completion": not body["is_synthetic"],
            "publication_allowed": not body["is_synthetic"],
            "blocker_codes": ["SYNTHETIC_RUN_NO_PUBLICATION_AUTHORITY"] if body["is_synthetic"] else [],
        }
    else:
        body["decision"]["status"] = "running"
    sealed = _seal(body)
    validate_run(root, sealed)
    return sealed


def fail_stage(root: Path, run: dict[str, Any], stage_id: str, blocker: str, *, retryable: bool) -> dict[str, Any]:
    body = _unseal(run)
    stage = next((item for item in body["stages"] if item["stage_id"] == stage_id), None)
    if stage is None or stage["state"] != "ready":
        raise AudioOrchestratorError("stage_not_ready")
    stage["attempts"] += 1
    body["retry_budget"]["global_used_attempts"] += 1
    stage["blocker_codes"] = [blocker]
    _append_event(body, "stage_failed", stage_id, {"blocker": blocker, "attempt": stage["attempts"]})
    can_retry = retryable and stage["attempts"] < body["retry_budget"]["per_stage_max_attempts"] and body["retry_budget"]["global_used_attempts"] < body["retry_budget"]["global_max_attempts"]
    if can_retry:
        stage["state"] = "ready"
        _append_event(body, "stage_retry_admitted", stage_id, {"next_attempt": stage["attempts"] + 1})
        body["decision"]["status"] = "running"
    else:
        stage["state"] = "failed"
        body["decision"] = {"status": "failed", "row105_acceptance": "held", "runtime_completion": False, "publication_allowed": False, "blocker_codes": [blocker, "ROW105_STAGE_FAILED"]}
    sealed = _seal(body)
    validate_run(root, sealed)
    return sealed


def resume_run(root: Path, run: dict[str, Any]) -> dict[str, Any]:
    body = _unseal(run)
    _refresh_ready(body)
    sealed = _seal(body)
    validate_run(root, sealed)
    return sealed


def validate_run(root: Path, run: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(run)
    body = _unseal(run)
    policy = load_policy(root)
    expected_specs = policy["mandatory_stages"]
    if [(item["stage_id"], item["predecessors"]) for item in body["stages"]] != [(item["stage_id"], item["predecessors"]) for item in expected_specs]:
        raise AudioOrchestratorError("mandatory_dag_mismatch")
    prior = ZERO_HASH
    for index, event in enumerate(body["event_log"], start=1):
        if event["sequence"] != index or event["previous_event_sha256"] != prior:
            raise AudioOrchestratorError("event_chain_sequence_or_parent_mismatch")
        event_body = {key: value for key, value in event.items() if key != "event_sha256"}
        if event["event_sha256"] != digest(event_body):
            raise AudioOrchestratorError("event_hash_mismatch")
        prior = event["event_sha256"]
    if body["retry_budget"]["global_used_attempts"] > body["retry_budget"]["global_max_attempts"]:
        raise AudioOrchestratorError("global_retry_budget_overrun")
    for stage in body["stages"]:
        if stage["attempts"] > body["retry_budget"]["per_stage_max_attempts"]:
            raise AudioOrchestratorError("stage_retry_budget_overrun")
        if stage["state"] in {"pass", "reused"} and stage["output_sha256"] is None:
            raise AudioOrchestratorError("passed_stage_output_missing")
    if body["is_synthetic"] and body["decision"]["publication_allowed"]:
        raise AudioOrchestratorError("synthetic_publication_forbidden")
    if body["decision"]["publication_allowed"] and not all(stage["state"] in {"pass", "reused"} for stage in body["stages"]):
        raise AudioOrchestratorError("publication_skipped_mandatory_stage")


def synthetic_crash_resume_fixture(root: Path) -> dict[str, Any]:
    run = compile_run(root, request={"fixture": "crash_resume", "video_sha256": stable_hash("video")}, is_synthetic=True, admissions=accepted_fixture_dependencies())
    run = complete_stage(root, run, "normalize_inputs", stable_hash("normalized"), cost_usd=0.01)
    serialized = json.dumps(run, sort_keys=True)
    resumed = resume_run(root, json.loads(serialized))
    replayed = complete_stage(root, resumed, "normalize_inputs", stable_hash("normalized"), cost_usd=0.01)
    return {"initial_after_stage": run, "resumed": resumed, "idempotent_replay_identical": replayed == resumed}


def build_hold_packet(root: Path) -> dict[str, Any]:
    admissions = dependency_admissions(root)
    live = compile_run(root, request={"mode": "library", "authority": "held"}, is_synthetic=False, admissions=admissions)
    fixture = synthetic_crash_resume_fixture(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-105_audio_end_to_end_orchestrator",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "row_complete": False,
        "runtime_completion_claimed": False,
        "publication_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_AUDIO_ORCHESTRATOR_RUNTIME_ABSENT",
        "dependency_admissions": admissions,
        "live_hold_run": live,
        "fixture_proof": fixture,
        "decision": {"status": "blocked", "row105_acceptance": "held", "product_completion": False, "safe_next_action": "Accept Rows083, 092, 097, and 104; bind exact stage adapters and retained inputs; then execute crash/resume, retry-budget, cost-budget, no-skip, publication, and failure-injection campaigns under owned runtime authority."},
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise AudioOrchestratorError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    payload = build_hold_packet(root)
    write_json(output, payload)
    print(json.dumps({"output": str(output), "status": payload["status"], "row_complete": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
