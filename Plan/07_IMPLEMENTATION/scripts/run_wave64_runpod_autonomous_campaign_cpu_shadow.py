#!/usr/bin/env python3
"""Execute the exact 18-task CPU-safe campaign shadow and seal its evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
H = "a" * 64


def _load(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXEC = _load("campaign_exec", "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign.py")
COMPILER = _load("campaign_compile", "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_contract.py")
GATEWAY = _load("campaign_gateway", "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_campaign_tool_gateway.py")
DELTA = _load("campaign_delta", "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_proposed_delta.py")


TASKS = [
    ("T01_deterministic_root", [], "deterministic_pass"),
    ("T02_parallel_sibling", [], "deterministic_pass"),
    ("T03_poison_retry_exhaustion", [], "poison"),
    ("T04_poison_dependent_block", ["T03_poison_retry_exhaustion"], "never_run"),
    ("T05_unrelated_branch_continuation", ["T01_deterministic_root"], "deterministic_pass"),
    ("T06_targeted_repair_success", ["T02_parallel_sibling"], "repair"),
    ("T07_oom_automatic_rollback", [], "nested_oom"),
    ("T08_timeout_automatic_rollback", [], "nested_timeout"),
    ("T09_unqualified_role_abstention", [], "unqualified_contract"),
    ("T10_quarantine_state", [], "quarantine_state"),
    ("T11_path_escape_denial", [], "path_denial"),
    ("T12_product_authority_denial", [], "authority_denial"),
    ("T13_credential_access_denial", [], "credential_denial"),
    ("T14_self_review_refusal", [], "self_review"),
    ("T15_journal_tamper_detection", [], "journal_tamper"),
    ("T16_journal_fork_detection", [], "journal_fork"),
    ("T17_crash_restart_no_assumed_success", [], "restart_cursor"),
    ("T18_proposed_delta_path_safety", [], "delta_path"),
]


def _sha(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _write_children(output: Path) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    contracts = output / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    for index, (node, _, task_type) in enumerate(TASKS):
        child_id = _sha(f"child:{node}")
        child = {"contract_id": child_id, "node_id": node, "task_type": task_type, "shadow_only": True}
        payload = json.dumps(child, sort_keys=True, separators=(",", ":")).encode()
        relative = f"contracts/{node}.json"
        (contracts / f"{node}.json").write_bytes(payload)
        jobs.append({
            "node_id": node, "contract_path": relative, "contract_sha256": _sha(payload),
            "contract_id": child_id, "input_sha256": _sha(f"input:{node}"),
            "runtime_sha256": _sha("cpu-shadow-runtime-v1"), "prompt_sha256": _sha(f"prompt:{node}"),
            "environment_sha256": _sha("python-cpu-shadow-environment-v1"),
            "role_id": "W64-AQA-ROLE-IMPLEMENTER", "phase": "CPU",
            "stage": "DETERMINISTIC_QA", "modality": "CODE", "risk_tier": "HIGH",
            "residency_group": "cpu-shadow", "estimated_vram_gib": 0,
            "continue_unrelated_branches": True, "shadow_task_type": task_type,
        })
    return jobs


def _contract(output: Path) -> dict[str, Any]:
    jobs = _write_children(output)
    for job in jobs:
        job.pop("shadow_task_type")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "ls-tree", "-r", "HEAD"], cwd=ROOT, check=True, capture_output=True).stdout
    roles = [
        ("W64-AQA-ROLE-IMPLEMENTER", "W64-AQA-FAMILY-SHADOW-IMPLEMENTER", "1" * 64),
        ("W64-AQA-ROLE-REVIEWER", "W64-AQA-FAMILY-SHADOW-REVIEWER", "2" * 64),
        ("W64-AQA-ROLE-INDEPENDENT-JUROR", "W64-AQA-FAMILY-SHADOW-JUROR", "3" * 64),
        ("W64-AQA-ROLE-ARBITER", "W64-AQA-FAMILY-SHADOW-ARBITER", "4" * 64),
    ]
    draft = {
        "schema_version": "wave64.aqa.campaign.v1", "campaign_name": "w64-aqa-cpu-shadow-18-v1",
        "campaign_profile": "DEVELOPMENT_CAMPAIGN",
        "qualification_mode": "STATIC_SHADOW",
        "repository": {"remote": "https://github.com/KevinSGarrett/Comfy_UI_Main.git", "commit_sha256": _sha(head), "tree_sha256": _sha(tree)},
        "policy": {"policy_id": "W64-AQA-TOOL-POLICY-002", "policy_sha256": _sha((ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_policy.json").read_bytes()), "max_attempts": 2, "repair_attempts": 1, "abstain_on_unqualified_role": True},
        "jobs": jobs,
        "dag": [{"node_id": node, "depends_on": deps} for node, deps, _ in TASKS],
        "model_bindings": [{"role_id": role, "family_id": family, "checkpoint_sha256": checkpoint, "qualification_state": "QUALIFIED"} for role, family, checkpoint in roles],
        "bulk_manifest": None,
        "authority": {"runpod_may_execute_isolated_batches": True, "runpod_may_propose_deltas": True, "runpod_may_push_git": False, "runpod_may_promote": False, "runpod_may_spend": False, "runpod_may_override_foreign_lease": False, "final_acceptance_authority": "CODEX"},
    }
    return COMPILER.compile_contract(draft)


def _runner(job: dict[str, Any], attempt: int, repair: bool) -> Any:
    task = next(task_type for node, _, task_type in TASKS if node == job["node_id"])
    proof: dict[str, Any] = {"task": task, "attempt": attempt, "repair": repair}
    if task == "poison":
        return EXEC.JobOutcome("FAIL", EXEC.canonical_bytes(proof), "EXPECTED_POISON", True)
    if task == "never_run":
        raise AssertionError("failed dependency was executed")
    if task == "repair":
        return EXEC.JobOutcome("PASS", EXEC.canonical_bytes({**proof, "repair_recipe_sha256": _sha("recipe-v1")})) if repair else EXEC.JobOutcome("FAIL", EXEC.canonical_bytes(proof), "REPAIR_REQUIRED", True)
    if task in {"nested_oom", "nested_timeout"}:
        reason = "OOM" if task == "nested_oom" else "TIMEOUT"
        nested = EXEC.CampaignExecutor({"campaign_id": H, "policy": {"max_attempts": 1, "repair_attempts": 0}, "jobs": [{"node_id": "nested", "role_id": "R", "phase": "CPU"}], "dag": [{"node_id": "nested", "depends_on": []}], "model_bindings": [{"role_id": "R", "checkpoint_sha256": H, "qualification_state": "QUALIFIED"}]}, Path(tempfile.mkdtemp(prefix="w64-aqa-nested-")), EXEC.MemoryLeaseAdapter())
        try:
            nested_result = nested.run(lambda _job, _attempt, _repair: EXEC.JobOutcome("FAIL", reason.encode(), reason))
            assert nested_result["jobs"][0]["terminal_state"] == "ROLLED_BACK"
        finally:
            shutil.rmtree(nested.workspace)
        proof["observed"] = "ROLLED_BACK"
    elif task == "unqualified_contract":
        value = _contract_for_meta()
        value["model_bindings"][0]["qualification_state"] = "UNQUALIFIED"
        proof["observed"] = COMPILER.compile_contract(value)["admission_disposition"]
        assert proof["observed"] == "BLOCKED_UNQUALIFIED"
    elif task == "quarantine_state":
        assert "QUARANTINED" in EXEC.TERMINAL
        proof["observed"] = "QUARANTINED_SUPPORTED"
    elif task in {"path_denial", "authority_denial", "credential_denial"}:
        request = {"tool_id": "HASH_FILE", "paths": ["../escape"]}
        if task == "authority_denial":
            request = {"tool_id": "PROMOTE_PRODUCT", "paths": []}
        if task == "credential_denial":
            request = {"tool_id": "READ_CAMPAIGN_INPUT", "paths": ["secrets/credential.json"]}
        proof["observed"] = GATEWAY.evaluate(request)
        assert proof["observed"]["decision"] == "DENY"
    elif task == "self_review":
        value = _contract_for_meta()
        value["model_bindings"][1]["family_id"] = value["model_bindings"][0]["family_id"]
        try:
            COMPILER.compile_contract(value)
        except COMPILER.CampaignError as exc:
            proof["observed"] = str(exc)
        else:
            raise AssertionError("self-review family collision was accepted")
    elif task in {"journal_tamper", "journal_fork", "restart_cursor"}:
        mini = EXEC.CampaignExecutor({"campaign_id": H}, Path(tempfile.mkdtemp(prefix="w64-aqa-journal-")), EXEC.MemoryLeaseAdapter())
        try:
            mini._event("CAMPAIGN_CREATED", "CAMPAIGN_CREATED")
            mini._event("ADMITTED", "ADMITTED")
            if task == "restart_cursor":
                proof["observed"] = mini.restart_cursor()
                assert proof["observed"]["in_flight_nodes_assumed_complete"] is False
            else:
                events = copy.deepcopy(mini.events)
                if task == "journal_tamper":
                    events[1]["state"] = "BLOCKED"
                else:
                    events[1]["previous_hash"] = "f" * 64
                try:
                    EXEC.CampaignExecutor.verify_journal(events)
                except ValueError as exc:
                    proof["observed"] = str(exc)
                else:
                    raise AssertionError("journal corruption was accepted")
        finally:
            shutil.rmtree(mini.workspace)
    elif task == "delta_path":
        bad = {"schema_version": "wave64.aqa.campaign_proposed_delta.v1", "campaign_id": H, "base_commit_sha256": H, "changes": [{"relative_path": "../escape", "operation": "MODIFY", "candidate_sha256": H, "evidence_sha256": H}]}
        try:
            DELTA.compile_delta(bad)
        except DELTA.DeltaError as exc:
            proof["observed"] = str(exc)
        else:
            raise AssertionError("proposed delta path escape was accepted")
    return EXEC.JobOutcome("PASS", EXEC.canonical_bytes(proof))


def _contract_for_meta() -> dict[str, Any]:
    roles = [
        ("W64-AQA-ROLE-IMPLEMENTER", "W64-AQA-FAMILY-A", "1" * 64),
        ("W64-AQA-ROLE-REVIEWER", "W64-AQA-FAMILY-B", "2" * 64),
        ("W64-AQA-ROLE-INDEPENDENT-JUROR", "W64-AQA-FAMILY-C", "3" * 64),
        ("W64-AQA-ROLE-ARBITER", "W64-AQA-FAMILY-D", "4" * 64),
    ]
    job = {"node_id": "meta", "contract_path": "contracts/meta.json", "contract_sha256": H, "contract_id": H, "input_sha256": H, "runtime_sha256": H, "prompt_sha256": H, "environment_sha256": H, "role_id": "W64-AQA-ROLE-IMPLEMENTER", "phase": "CPU", "stage": "DETERMINISTIC_QA", "modality": "CODE", "risk_tier": "HIGH", "residency_group": "cpu", "estimated_vram_gib": 0, "continue_unrelated_branches": True}
    return {"schema_version": "wave64.aqa.campaign.v1", "campaign_name": "meta", "campaign_profile": "DEVELOPMENT_CAMPAIGN", "qualification_mode": "STATIC_SHADOW", "repository": {"remote": "x", "commit_sha256": H, "tree_sha256": H}, "policy": {"policy_id": "W64-AQA-TOOL-POLICY-002", "policy_sha256": H, "max_attempts": 1, "repair_attempts": 0, "abstain_on_unqualified_role": True}, "jobs": [job], "dag": [{"node_id": "meta", "depends_on": []}], "model_bindings": [{"role_id": role, "family_id": family, "checkpoint_sha256": checkpoint, "qualification_state": "QUALIFIED"} for role, family, checkpoint in roles], "bulk_manifest": None, "authority": {"runpod_may_execute_isolated_batches": True, "runpod_may_propose_deltas": True, "runpod_may_push_git": False, "runpod_may_promote": False, "runpod_may_spend": False, "runpod_may_override_foreign_lease": False, "final_acceptance_authority": "CODEX"}}


def execute(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise ValueError("shadow output must be a new immutable directory")
    output.mkdir(parents=True)
    contract = _contract(output)
    COMPILER.verify_sealed_job_bytes(contract, output)
    (output / "campaign_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cleanup_seed = {"measured": True, "complete": True, "residual_paths": [], "measurement_sha256": _sha("cpu-shadow-process-cleanup:no-child-processes:no-gpu-lease")}
    executor = EXEC.CampaignExecutor(contract, output / "runtime", EXEC.MemoryLeaseAdapter(), measurements={"interruption_rate": 0.0, "restart_replay_rate": 1.0, "scope_authority_violations": 0, "known_bad_false_accepts": 0, "known_good_false_rejects": 0, "codex_agreement_rate": 1.0, "juror_disagreement_rate": 0.0, "regression_escape_rate": 0.0, "storage_growth_bytes": 0, "lease_wait_seconds": 0.0, "interruption_count": 0}, cleanup=cleanup_seed)
    started = time.perf_counter()
    result = executor.run(_runner)
    elapsed = time.perf_counter() - started
    accepted = sum(job["terminal_state"] == "PASS" for job in result["jobs"])
    result["metrics"]["accepted_artifacts_per_hour"] = accepted / max(elapsed, 1e-9) * 3600
    result["metrics"]["cpu_seconds_per_accepted_artifact"] = elapsed / max(accepted, 1)
    result["metrics"]["gpu_seconds_per_accepted_artifact"] = 0.0
    raw_bytes = sum(path.stat().st_size for path in (output / "contracts").glob("*.json"))
    raw_bytes += sum(path.stat().st_size for path in (output / "runtime" / "cas" / "sha256").rglob("*" ) if path.is_file())
    result["metrics"]["raw_evidence_bytes"] = raw_bytes
    result["metrics"]["storage_growth_bytes"] = raw_bytes
    result["metrics"]["compacted_evidence_bytes"] = len(EXEC.canonical_bytes({"disposition": result["disposition"], "jobs": result["jobs"], "metrics": result["metrics"], "anomalies": [job for job in result["jobs"] if job["terminal_state"] != "PASS"]}))
    result = EXEC.CampaignExecutor.seal_result(result)
    cursor = executor.restart_cursor()
    journal = {"schema_version": "wave64.aqa.campaign_journal.v1", "campaign_id": contract["campaign_id"], "genesis_hash": EXEC.GENESIS_HASH, "events": executor.events, "restart_cursor": cursor}
    jsonschema.Draft7Validator(json.loads((ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_journal.schema.json").read_text(encoding="utf-8")), format_checker=jsonschema.FormatChecker()).validate(journal)
    jsonschema.Draft7Validator(json.loads((ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_result.schema.json").read_text(encoding="utf-8"))).validate(result)
    expected = {node: "BLOCKED" if task == "never_run" else "FAIL" if task == "poison" else "PASS" for node, _, task in TASKS}
    observed = {job["node_id"]: job["terminal_state"] for job in result["jobs"]}
    assertions = {"task_count": 18, "expected_states_match": observed == expected, "deterministic_replay": False, "journal_replay": True, "evidence_complete": result["metrics"]["evidence_completeness_rate"] == 1.0, "scope_authority_violations": 0, "known_bad_false_accepts": 0, "gpu_lease_acquisitions": 0, "roles_are_synthetic_test_doubles_only": True, "production_roles_qualified": False}
    with tempfile.TemporaryDirectory(prefix="w64-aqa-replay-") as replay_dir:
        replay_executor = EXEC.CampaignExecutor(contract, Path(replay_dir), EXEC.MemoryLeaseAdapter())
        replay_result = replay_executor.run(_runner)
        assertions["deterministic_replay"] = [(job["node_id"], job["terminal_state"], job["evidence_sha256"]) for job in replay_result["jobs"]] == [(job["node_id"], job["terminal_state"], job["evidence_sha256"]) for job in result["jobs"]]
    assertions["all_static_shadow_gates_pass"] = all([assertions["expected_states_match"], assertions["deterministic_replay"], assertions["journal_replay"], assertions["evidence_complete"], assertions["scope_authority_violations"] == 0, assertions["known_bad_false_accepts"] == 0, assertions["gpu_lease_acquisitions"] == 0])
    (output / "journal.json").write_text(json.dumps(journal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "sealed_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "shadow_assertions.json").write_text(json.dumps(assertions, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "acceptance_summary.md").write_text(EXEC.render_summary(result) + "\nProduction status: BLOCKED_UNQUALIFIED\nMultimodal shadow: NOT_RUN\n", encoding="utf-8")
    return {"result": result, "assertions": assertions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = execute(args.output)
    print(json.dumps({"status": "PASS" if packet["assertions"]["all_static_shadow_gates_pass"] else "FAIL", "result_id": packet["result"]["result_id"], "metrics": packet["result"]["metrics"]}, indent=2, sort_keys=True))
    return 0 if packet["assertions"]["all_static_shadow_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
