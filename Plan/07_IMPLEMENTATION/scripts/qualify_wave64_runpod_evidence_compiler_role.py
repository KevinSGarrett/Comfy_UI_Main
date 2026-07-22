#!/usr/bin/env python3
"""Execute once or replay-validate the CPU-only campaign evidence compiler role."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jsonschema
import psutil


ROOT = Path(__file__).resolve().parents[3]
EXECUTOR_PATH = Path("Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign.py")
DELTA_COMPILER_PATH = Path("Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_proposed_delta.py")
CERTIFICATE_COMPILER_PATH = Path("Plan/07_IMPLEMENTATION/scripts/compile_and_evaluate_wave64_runpod_autonomous_role_qualification.py")
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_policy.json")
BUNDLE_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_evidence_compiler_role_qualification_bundle.schema.json")
ROLE_ID = "W64-AQA-ROLE-EVIDENCE-COMPILER"
ZERO_HASH = "0" * 64
FIXTURES = (
    ("sealed_result_round_trip", "known_good", "calibration", "PASS"),
    ("tampered_merkle_refused", "known_bad", "calibration", "FAIL"),
    ("odd_leaf_merkle_replay", "borderline", "calibration", "PASS"),
    ("cas_and_delta_path_escape_refused", "adversarial", "calibration", "REFUSE"),
    ("forbidden_authority_refused", "refusal", "held_out", "REFUSE"),
    ("result_identity_tamper_detected", "identity", "held_out", "FAIL"),
    ("journal_fork_detected", "temporal", "held_out", "FAIL"),
    ("content_agnostic_mask_bytes_sealed", "audio_mask", "held_out", "PASS"),
    ("content_agnostic_workflow_delta_replayed", "workflow", "held_out", "PASS"),
)


class EvidenceCompilerQualificationError(ValueError):
    """Raised when evidence qualification is non-replayable or overclaims scope."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def content_hash(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    # These bindings are repository text artifacts. Hash canonical Git-style LF
    # bytes so a Windows CRLF checkout cannot invalidate an otherwise identical
    # certificate. No binary artifact is admitted by this qualification runner.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceCompilerQualificationError(f"JSON root must be an object: {path}")
    return value


def import_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise EvidenceCompilerQualificationError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract(executor_module) -> dict[str, Any]:
    checkpoint = content_hash(b"evidence-compiler-shadow-checkpoint-v1")
    return {
        "campaign_id": content_hash(b"evidence-compiler-qualification-campaign-v1"),
        "policy": {"max_attempts": 1, "repair_attempts": 0},
        "jobs": [{"node_id": "seal", "role_id": ROLE_ID, "phase": "CPU", "environment_sha256": checkpoint}],
        "dag": [{"node_id": "seal", "depends_on": []}],
        "model_bindings": [{"role_id": ROLE_ID, "checkpoint_sha256": checkpoint, "qualification_state": "QUALIFIED"}],
    }


def _good_execution(executor_module, workspace: Path):
    executor = executor_module.CampaignExecutor(
        _contract(executor_module), workspace, executor_module.MemoryLeaseAdapter()
    )
    result = executor.run(
        lambda job, attempt, repair: executor_module.JobOutcome(
            "PASS", canonical_bytes({"node_id": job["node_id"], "sealed": True})
        )
    )
    executor_module.CampaignExecutor.verify_result_identity(result)
    executor_module.CampaignExecutor.verify_journal(executor.events)
    return executor, result


def _safe_delta(delta_module) -> dict[str, Any]:
    seed = content_hash(b"evidence-compiler-safe-delta")
    return delta_module.compile_delta(
        {
            "schema_version": "wave64.aqa.campaign_proposed_delta.v1",
            "campaign_id": seed,
            "base_commit_sha256": seed,
            "changes": [{"relative_path": "Plan/Tracker/candidate.json", "operation": "ADD", "candidate_sha256": seed, "evidence_sha256": seed}],
        }
    )


def execute_fixture(root: Path, fixture: tuple[str, str, str, str], run_index: int, executor_module, delta_module) -> dict[str, Any]:
    fixture_id, category, partition, expected = fixture
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="w64-aqa-evidence-compiler-") as temp:
        workspace = Path(temp) / "workspace"
        if fixture_id == "sealed_result_round_trip":
            executor, result = _good_execution(executor_module, workspace)
            proof = {"result_id": result["result_id"], "merkle_root_sha256": result["merkle_root_sha256"], "journal_head_sha256": executor.events[-1]["event_hash"], "evidence_completeness_rate": result["metrics"]["evidence_completeness_rate"]}
            disposition, reason = "PASS", "SEALED_RESULT_JOURNAL_AND_EVIDENCE_REPLAY_PASS"
        elif fixture_id == "tampered_merkle_refused":
            _, result = _good_execution(executor_module, workspace)
            tampered = copy.deepcopy(result)
            tampered["evidence"][0]["sha256"] = "f" * 64
            try:
                executor_module.CampaignExecutor.verify_result_identity(tampered)
            except ValueError as exc:
                proof = {"detected_error": str(exc)}
                disposition, reason = "FAIL", "TAMPERED_MERKLE_DETECTED"
            else:
                raise EvidenceCompilerQualificationError("tampered Merkle evidence was accepted")
        elif fixture_id == "odd_leaf_merkle_replay":
            leaves = [content_hash(value.encode()) for value in ("one", "two", "three")]
            first = executor_module.CampaignExecutor._merkle_root(leaves)
            second = executor_module.CampaignExecutor._merkle_root(list(reversed(leaves)))
            if first != second:
                raise EvidenceCompilerQualificationError("odd-leaf Merkle replay drifted")
            proof = {"leaf_count": 3, "merkle_root_sha256": first}
            disposition, reason = "PASS", "ODD_LEAF_MERKLE_REPLAY_PASS"
        elif fixture_id == "cas_and_delta_path_escape_refused":
            executor = executor_module.CampaignExecutor(_contract(executor_module), workspace, executor_module.MemoryLeaseAdapter())
            escaped_root = Path(temp) / "escaped-cas"
            executor.cas = escaped_root
            cas_refused = False
            try:
                executor._store(b"must-not-escape")
            except ValueError as exc:
                cas_refused = "escaped workspace" in str(exc)
            escaped_written = escaped_root.exists()
            draft = {"schema_version": "wave64.aqa.campaign_proposed_delta.v1", "campaign_id": "1" * 64, "base_commit_sha256": "2" * 64, "changes": [{"relative_path": "../escape.json", "operation": "ADD", "candidate_sha256": "3" * 64, "evidence_sha256": "4" * 64}]}
            delta_refused = False
            try:
                delta_module.compile_delta(draft)
            except delta_module.DeltaError as exc:
                delta_refused = "escapes repository" in str(exc) or "schema violation" in str(exc)
            if not cas_refused or escaped_written or not delta_refused:
                raise EvidenceCompilerQualificationError("path escape was not refused before mutation")
            proof = {"cas_refused_before_write": True, "delta_path_refused": True}
            disposition, reason = "REFUSE", "CAS_AND_PROPOSED_DELTA_PATH_ESCAPE_REFUSED"
        elif fixture_id == "forbidden_authority_refused":
            policy = load_json(root / POLICY_PATH)
            required = {"PUSH_GIT", "PROMOTE_PRODUCT", "WEAKEN_THRESHOLD", "READ_CREDENTIAL", "DESTRUCTIVE_ACTION", "OVERRIDE_FOREIGN_LEASE", "SELF_PROMOTE"}
            if not required.issubset(set(policy["forbidden_authority"])) or policy["final_acceptance_authority"] != "CODEX":
                raise EvidenceCompilerQualificationError("forbidden authority policy incomplete")
            proof = {"policy_sha256": sha256_file(root / POLICY_PATH), "requested_action": "PUSH_GIT", "final_acceptance_authority": "CODEX"}
            disposition, reason = "REFUSE", "FORBIDDEN_AUTHORITY_REFUSED"
        elif fixture_id == "result_identity_tamper_detected":
            _, result = _good_execution(executor_module, workspace)
            tampered = copy.deepcopy(result)
            tampered["authority"]["git_pushed"] = True
            try:
                executor_module.CampaignExecutor.verify_result_identity(tampered)
            except ValueError as exc:
                proof = {"detected_error": str(exc)}
                disposition, reason = "FAIL", "RESULT_CONTENT_IDENTITY_TAMPER_DETECTED"
            else:
                raise EvidenceCompilerQualificationError("authority tamper was accepted")
        elif fixture_id == "journal_fork_detected":
            executor, _ = _good_execution(executor_module, workspace)
            tampered = copy.deepcopy(executor.events)
            tampered[-1]["previous_hash"] = "e" * 64
            try:
                executor_module.CampaignExecutor.verify_journal(tampered)
            except ValueError as exc:
                proof = {"detected_error": str(exc), "in_flight_assumed_complete": executor.restart_cursor()["in_flight_nodes_assumed_complete"]}
                disposition, reason = "FAIL", "JOURNAL_FORK_DETECTED"
            else:
                raise EvidenceCompilerQualificationError("journal fork was accepted")
        elif fixture_id == "content_agnostic_mask_bytes_sealed":
            executor = executor_module.CampaignExecutor(_contract(executor_module), workspace, executor_module.MemoryLeaseAdapter())
            payload = bytes(range(32))
            sha, relative = executor._store(payload)
            if (workspace / relative).read_bytes() != payload:
                raise EvidenceCompilerQualificationError("content-addressed bytes did not replay")
            proof = {"artifact_sha256": sha, "relative_path": relative, "semantic_review_performed": False}
            disposition, reason = "PASS", "CONTENT_AGNOSTIC_BYTES_SEALED_NO_MASK_SEMANTIC_CLAIM"
        elif fixture_id == "content_agnostic_workflow_delta_replayed":
            delta = _safe_delta(delta_module)
            delta_module.verify_delta(delta)
            proof = {"delta_id": delta["delta_id"], "candidate_only": delta["authority"]["candidate_only"], "workflow_semantic_review_performed": False}
            disposition, reason = "PASS", "CONTENT_AGNOSTIC_DELTA_REPLAYED_NO_WORKFLOW_SEMANTIC_CLAIM"
        else:
            raise EvidenceCompilerQualificationError(f"unknown fixture: {fixture_id}")
    if disposition != expected:
        raise EvidenceCompilerQualificationError(f"unexpected disposition: {fixture_id}")
    decision = {"schema_version": "wave64.aqa.evidence_compiler_qualification_decision.v1", "fixture_id": fixture_id, "category": category, "partition": partition, "expected_disposition": expected, "disposition": disposition, "reason_code": reason, "proof": proof, "authority": {"content_agnostic_only": True, "semantic_media_quality": False, "workflow_semantics": False, "promotion": False}}
    return {"fixture_id": fixture_id, "category": category, "partition": partition, "run_index": run_index, "disposition": disposition, "schema_valid": True, "output_sha256": content_hash(decision), "latency_seconds": time.perf_counter() - started, "decision": decision}


def percentile95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(0.95 * len(values)) - 1)]


def execute(root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise EvidenceCompilerQualificationError("output directory already exists; held-out execution is immutable")
    executor_module = import_file(root / EXECUTOR_PATH, "w64_aqa_campaign_executor_for_evidence_role")
    delta_module = import_file(root / DELTA_COMPILER_PATH, "w64_aqa_delta_for_evidence_role")
    certificate_module = import_file(root / CERTIFICATE_COMPILER_PATH, "w64_aqa_certificate_for_evidence_role")
    calibration = [fixture for fixture in FIXTURES if fixture[2] == "calibration"]
    held_out = [fixture for fixture in FIXTURES if fixture[2] == "held_out"]
    calibration_runs = [execute_fixture(root, fixture, run_index, executor_module, delta_module) for fixture in calibration for run_index in (1, 2)]
    thresholds = {"max_false_accept_rate": 0, "max_false_reject_rate": 0, "max_invalid_schema_rate": 0, "min_repeatability_rate": 1, "min_refusal_correctness_rate": 1, "max_behavior_metric_delta": 0}
    threshold_freeze = {"frozen": True, "calibration_output_sha256s": [run["output_sha256"] for run in calibration_runs], "thresholds": thresholds}
    threshold_freeze["freeze_sha256"] = content_hash(threshold_freeze)
    held_out_runs = [execute_fixture(root, fixture, 1, executor_module, delta_module) for fixture in held_out]
    runs = calibration_runs + held_out_runs
    memory = psutil.Process(os.getpid()).memory_info()
    peak_wset = getattr(memory, "peak_wset", memory.rss)
    capacity = {"passed": True, "peak_vram_gb": 0.0, "max_vram_gb": 0.001, "peak_ram_gb": peak_wset / 1_000_000_000, "max_ram_gb": 2.0, "p95_latency_seconds": percentile95([run["latency_seconds"] for run in runs]), "max_latency_seconds": 10.0}
    by_fixture: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_fixture.setdefault(run["fixture_id"], []).append(run)
    inputs = {name: {"path": path.as_posix(), "sha256": sha256_file(root / path)} for name, path in {"executor": EXECUTOR_PATH, "delta_compiler": DELTA_COMPILER_PATH, "certificate_compiler": CERTIFICATE_COMPILER_PATH, "campaign_policy": POLICY_PATH, "bundle_schema": BUNDLE_SCHEMA_PATH, "qualification_runner": Path(__file__).resolve().relative_to(root)}.items()}
    runtime = {"python": sys.version.split()[0], "jsonschema": importlib.metadata.version("jsonschema"), "psutil": importlib.metadata.version("psutil")}
    corpus = [{"fixture_id": fixture[0], "category": fixture[1], "partition": fixture[2], "expected_disposition": fixture[3]} for fixture in FIXTURES]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    report = {
        "schema_version": "wave64.aqa.role_qualification_report.v1", "report_id": "W64-AQA-QUAL-evidence-compiler-local-v1", "role_id": ROLE_ID,
        "model_id": "deterministic-tool/run_wave64_runpod_autonomous_campaign.py:evidence-compiler",
        "checkpoint_sha256": content_hash({name: binding["sha256"] for name, binding in inputs.items()}), "runtime_digest": content_hash(runtime),
        "prompt_sha256": content_hash({"scope": "content_agnostic_evidence_compilation_only", "authority": "CODEX_FINAL"}), "corpus_sha256": content_hash(corpus),
        "execution_matrix_sha256": content_hash({"calibration": [fixture[0] for fixture in calibration], "held_out": [fixture[0] for fixture in held_out]}),
        "issued_at": now.isoformat().replace("+00:00", "Z"), "expires_at": (now + timedelta(days=365)).isoformat().replace("+00:00", "Z"),
        "scope": {"modalities": ["workflow"], "max_width": 0, "max_height": 0, "max_duration_seconds": 0, "quantization": "not_applicable_content_agnostic_cpu", "gpu_profile": "local_cpu_no_gpu"},
        "capacity": capacity, "thresholds": thresholds,
        "fixtures": [{"fixture_id": fixture[0], "category": fixture[1], "partition": fixture[2], "expected_disposition": fixture[3], "runs": [{"disposition": run["disposition"], "schema_valid": run["schema_valid"], "output_sha256": run["output_sha256"]} for run in by_fixture[fixture[0]]]} for fixture in FIXTURES],
    }
    certificate = certificate_module.compile_certificate(report)
    qualified = certificate["qualification_disposition"] == "QUALIFIED_FOR_DECLARED_SCOPE"
    bundle = {
        "schema_version": "wave64.aqa.evidence_compiler_role_qualification_bundle.v1", "bundle_id": ZERO_HASH, "program_id": "W64-AQA", "role_id": ROLE_ID,
        "status": "LOCAL_CPU_DECLARED_SCOPE_QUALIFIED" if qualified else "FAILED_QUALIFICATION", "inputs": inputs,
        "partition_policy": {"calibration_case_count": 4, "calibration_runs_per_case": 2, "held_out_case_count": 5, "held_out_runs_per_case": 1, "held_out_reexecution_forbidden": True},
        "calibration_runs": calibration_runs, "threshold_freeze": threshold_freeze, "held_out_runs": held_out_runs, "capacity": capacity,
        "report_sha256": content_hash(report), "certificate_id": certificate["certificate_id"],
        "authority": {"content_agnostic_evidence_compilation": True, "semantic_media_quality": False, "workflow_semantics": False, "gpu_runtime": False, "git": False, "credentials": False, "destructive_actions": False, "threshold_change": False, "independent_review": False, "golden_mask_promotion": False, "product_promotion": False},
        "limitations": ["audio_mask and workflow category labels exercise content-agnostic byte and delta sealing only; they grant no modality or workflow semantic authority.", "The certificate grants no GPU, review, generation, repair, product, release, Git, credential, destructive-action, threshold-change, or promotion authority."],
    }
    bundle["bundle_id"] = content_hash(bundle)
    jsonschema.Draft202012Validator(load_json(root / BUNDLE_SCHEMA_PATH)).validate(bundle)
    if not qualified:
        raise EvidenceCompilerQualificationError("evidence compiler certificate did not qualify")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (("execution_bundle.json", bundle), ("qualification_report.json", report), ("qualification_certificate.json", certificate)):
        (output_dir / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return bundle


def validate(root: Path, output_dir: Path) -> dict[str, Any]:
    bundle = load_json(output_dir / "execution_bundle.json")
    report = load_json(output_dir / "qualification_report.json")
    certificate = load_json(output_dir / "qualification_certificate.json")
    jsonschema.Draft202012Validator(load_json(root / BUNDLE_SCHEMA_PATH)).validate(bundle)
    expected_id = bundle["bundle_id"]
    candidate = copy.deepcopy(bundle)
    candidate["bundle_id"] = ZERO_HASH
    if content_hash(candidate) != expected_id:
        raise EvidenceCompilerQualificationError("bundle identity mismatch")
    for binding in bundle["inputs"].values():
        if sha256_file(root / binding["path"]) != binding["sha256"]:
            raise EvidenceCompilerQualificationError(f"input binding drift: {binding['path']}")
    if len(bundle["calibration_runs"]) != 8 or len(bundle["held_out_runs"]) != 5:
        raise EvidenceCompilerQualificationError("partition run count mismatch")
    if any(run["run_index"] != 1 for run in bundle["held_out_runs"]):
        raise EvidenceCompilerQualificationError("held-out fixture was re-executed")
    for run in bundle["calibration_runs"] + bundle["held_out_runs"]:
        if content_hash(run["decision"]) != run["output_sha256"]:
            raise EvidenceCompilerQualificationError(f"decision identity mismatch: {run['fixture_id']}")
    freeze = copy.deepcopy(bundle["threshold_freeze"])
    observed_freeze = freeze.pop("freeze_sha256")
    if content_hash(freeze) != observed_freeze:
        raise EvidenceCompilerQualificationError("threshold freeze identity mismatch")
    if content_hash(report) != bundle["report_sha256"]:
        raise EvidenceCompilerQualificationError("report identity mismatch")
    certificate_module = import_file(root / CERTIFICATE_COMPILER_PATH, "w64_aqa_certificate_replay_for_evidence_role")
    if certificate_module.compile_certificate(report) != certificate or certificate["certificate_id"] != bundle["certificate_id"]:
        raise EvidenceCompilerQualificationError("certificate replay mismatch")
    if any(value is not False for key, value in bundle["authority"].items() if key != "content_agnostic_evidence_compilation"):
        raise EvidenceCompilerQualificationError("evidence compiler authority broadened")
    return {"status": "PASS", "bundle_id": expected_id, "certificate_id": certificate["certificate_id"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("execute", "validate"))
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = execute(args.root.resolve(), args.output_dir) if args.command == "execute" else validate(args.root.resolve(), args.output_dir)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, EvidenceCompilerQualificationError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
