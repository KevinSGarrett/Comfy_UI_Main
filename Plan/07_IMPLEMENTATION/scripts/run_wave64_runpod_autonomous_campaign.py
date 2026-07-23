#!/usr/bin/env python3
"""Deterministic, fail-closed W64-AQA campaign scheduler and evidence compiler."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, NamedTuple, Protocol


ZERO_HASH = "0" * 64
GENESIS_HASH = hashlib.sha256(b"W64-AQA-CAMPAIGN-GENESIS-V1").hexdigest()
RESULT_ID_PLACEHOLDER = "0" * 64
TERMINAL = {"PASS", "FAIL", "BLOCKED", "ABSTAINED", "QUARANTINED", "ROLLED_BACK"}
LEGAL_EVENT_TRANSITIONS = {
    None: {"CAMPAIGN_CREATED"},
    "CAMPAIGN_CREATED": {"ADMITTED", "BLOCKED"},
    "ADMITTED": {"CPU_PHASE_ACTIVE", "GPU_LEASE_WAIT", "JOB_TERMINAL", "CAMPAIGN_TERMINAL"},
    "CPU_PHASE_ACTIVE": {"JOB_DISPATCH", "JOB_TERMINAL"},
    "GPU_LEASE_WAIT": {"JOB_DISPATCH", "JOB_TERMINAL"},
    "JOB_DISPATCH": {"JOB_DISPATCH", "JOB_TERMINAL"},
    "JOB_TERMINAL": {"CPU_PHASE_ACTIVE", "GPU_LEASE_WAIT", "JOB_TERMINAL", "CAMPAIGN_TERMINAL", "RESTART_REPLAY"},
    "RESTART_REPLAY": {"CPU_PHASE_ACTIVE", "GPU_LEASE_WAIT", "JOB_TERMINAL", "CAMPAIGN_TERMINAL"},
    "BLOCKED": {"JOB_TERMINAL", "RESTART_REPLAY", "CAMPAIGN_TERMINAL"},
    "CAMPAIGN_TERMINAL": set(),
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


class LeaseAdapter(Protocol):
    def acquire(self, campaign_id: str, node_id: str) -> str | None: ...
    def validate(self, lease_id: str) -> bool: ...
    def release(self, lease_id: str, outcome: str) -> None: ...


class JobOutcome(NamedTuple):
    state: str
    artifact: bytes
    reason: str = ""
    repairable: bool = False


class MemoryLeaseAdapter:
    """Test/shadow adapter; production must replace it with the shared coordinator."""

    def __init__(self, *, grant: bool = True, lose_after_acquire: bool = False) -> None:
        self.grant = grant
        self.lose_after_acquire = lose_after_acquire
        self.releases: list[tuple[str, str]] = []

    def acquire(self, campaign_id: str, node_id: str) -> str | None:
        return f"shadow-{campaign_id[:8]}-{node_id}" if self.grant else None

    def validate(self, lease_id: str) -> bool:
        return not self.lose_after_acquire

    def release(self, lease_id: str, outcome: str) -> None:
        self.releases.append((lease_id, outcome))


class CoordinatorLeaseAdapter:
    """Authenticated shared-coordinator adapter supplied with exact request functions."""

    def __init__(self, request: Callable[[str, str], dict[str, Any]], status: Callable[[str], dict[str, Any]], release: Callable[[str, str], None], cancel: Callable[[dict[str, Any]], bool]) -> None:
        self._request = request
        self._status = status
        self._release = release
        self._cancel = cancel
        self._campaign_by_lease: dict[str, str] = {}

    def acquire(self, campaign_id: str, node_id: str) -> str | None:
        receipt = self._request(campaign_id, node_id)
        if receipt.get("state") == "QUEUED":
            if self._cancel(receipt) is not True:
                raise RuntimeError("queued coordinator request was not canceled")
            return None
        if receipt.get("state") != "GRANTED" or receipt.get("foreign_override_allowed") is not False:
            return None
        lease_id = receipt.get("lease_id")
        if not isinstance(lease_id, str) or not lease_id:
            return None
        self._campaign_by_lease[lease_id] = campaign_id
        return lease_id

    def validate(self, lease_id: str) -> bool:
        receipt = self._status(lease_id)
        return receipt.get("state") == "VALID" and receipt.get("campaign_id") == self._campaign_by_lease.get(lease_id)

    def release(self, lease_id: str, outcome: str) -> None:
        self._release(lease_id, outcome)
        self._campaign_by_lease.pop(lease_id, None)


class CampaignExecutor:
    def __init__(self, contract: dict[str, Any], workspace: Path, lease_adapter: LeaseAdapter, *, measurements: dict[str, Any] | None = None, cleanup: dict[str, Any] | None = None) -> None:
        self.contract = copy.deepcopy(contract)
        self.workspace = workspace.resolve()
        self.cas = self.workspace / "cas" / "sha256"
        self.lease_adapter = lease_adapter
        self.events: list[dict[str, Any]] = []
        self.results: dict[str, dict[str, Any]] = {}
        self.model_reloads = 0
        self.coordinator_churn = 0
        self.measurements = copy.deepcopy(measurements or {})
        self.cleanup = copy.deepcopy(cleanup or {"measured": False, "complete": None, "residual_paths": [], "measurement_sha256": None})

    def _event(self, event_type: str, state: str, *, node_id: str | None = None, phase: str = "NONE", payload: dict[str, Any] | None = None) -> None:
        payload_hash = digest(payload or {})
        event = {
            "sequence": len(self.events), "timestamp": "1970-01-01T00:00:00Z",
            "event_type": event_type, "state": state, "node_id": node_id, "phase": phase,
            "payload_sha256": payload_hash,
            "previous_hash": self.events[-1]["event_hash"] if self.events else GENESIS_HASH,
            "event_hash": ZERO_HASH,
        }
        event["event_hash"] = digest(event)
        self.events.append(event)

    @staticmethod
    def verify_journal(events: list[dict[str, Any]]) -> None:
        previous = GENESIS_HASH
        previous_type: str | None = None
        for sequence, observed in enumerate(events):
            if observed["sequence"] != sequence or observed["previous_hash"] != previous:
                raise ValueError("journal fork or sequence discontinuity")
            candidate = copy.deepcopy(observed)
            actual = candidate["event_hash"]
            candidate["event_hash"] = ZERO_HASH
            if digest(candidate) != actual:
                raise ValueError("journal event hash mismatch")
            if observed["event_type"] not in LEGAL_EVENT_TRANSITIONS.get(previous_type, set()):
                raise ValueError(f"illegal journal state transition: {previous_type}->{observed['event_type']}")
            previous = actual
            previous_type = observed["event_type"]

    def _store(self, artifact: bytes) -> tuple[str, str]:
        sha = digest(artifact)
        path = self.cas / sha[:2] / sha
        try:
            resolved_path = path.resolve()
            resolved_path.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("content-addressed artifact path escaped workspace") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != artifact:
            raise ValueError("content-address collision")
        if not path.exists():
            path.write_bytes(artifact)
        return sha, resolved_path.relative_to(self.workspace).as_posix()

    def _ordered_ready(self, remaining: set[str], dependencies: dict[str, set[str]], jobs: dict[str, dict[str, Any]], current_checkpoint: str | None) -> list[str]:
        completed = {node for node, result in self.results.items() if result["terminal_state"] == "PASS"}
        ready = [node for node in remaining if dependencies[node].issubset(completed)]
        binding = {item["role_id"]: item["checkpoint_sha256"] for item in self.contract["model_bindings"]}
        return sorted(ready, key=lambda node: (jobs[node]["phase"] == "GPU", current_checkpoint is not None and binding[jobs[node]["role_id"]] != current_checkpoint, jobs[node].get("environment_sha256", ""), binding[jobs[node]["role_id"]], node))

    def run(self, runner: Callable[[dict[str, Any], int, bool], JobOutcome]) -> dict[str, Any]:
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._event("CAMPAIGN_CREATED", "CAMPAIGN_CREATED")
        if self.contract.get("admission_disposition") == "BLOCKED_UNQUALIFIED":
            self._event("BLOCKED", "BLOCKED", payload={"reason": "BLOCKED_UNQUALIFIED"})
        else:
            self._event("ADMITTED", "ADMITTED")
        jobs = {job["node_id"]: job for job in self.contract["jobs"]}
        dependencies = {node["node_id"]: set(node["depends_on"]) for node in self.contract["dag"]}
        if self.contract.get("admission_disposition") == "BLOCKED_UNQUALIFIED":
            for node in sorted(jobs):
                artifact = canonical_bytes({"node": node, "reason": "BLOCKED_UNQUALIFIED"})
                sha, path = self._store(artifact)
                self.results[node] = {"node_id": node, "terminal_state": "ABSTAINED", "attempts": 0, "evidence_sha256": sha, "evidence_path": path, "reason": "BLOCKED_UNQUALIFIED"}
                self._event("JOB_TERMINAL", "DAG_ADVANCE", node_id=node, phase=jobs[node]["phase"], payload=self.results[node])
            return self._result()
        remaining = set(jobs)
        current_checkpoint: str | None = None
        bindings = {item["role_id"]: item for item in self.contract["model_bindings"]}
        max_attempts = self.contract["policy"]["max_attempts"]
        repair_attempts = self.contract["policy"]["repair_attempts"]
        while remaining:
            progressed = False
            failed = {node for node, result in self.results.items() if result["terminal_state"] != "PASS"}
            for node in sorted(remaining):
                if dependencies[node] & failed:
                    artifact = canonical_bytes({"node": node, "reason": "FAILED_DEPENDENCY"})
                    sha, path = self._store(artifact)
                    self.results[node] = {"node_id": node, "terminal_state": "BLOCKED", "attempts": 0, "evidence_sha256": sha, "evidence_path": path, "reason": "FAILED_DEPENDENCY"}
                    remaining.remove(node)
                    progressed = True
            ready = self._ordered_ready(remaining, dependencies, jobs, current_checkpoint)
            if not ready and remaining:
                if progressed:
                    continue
                raise ValueError("DAG cannot advance")
            for node in ready[:1]:
                job = jobs[node]
                role = bindings[job["role_id"]]
                if role["qualification_state"] != "QUALIFIED":
                    outcome = JobOutcome("ABSTAINED", canonical_bytes({"node": node, "reason": "ROLE_UNQUALIFIED"}), "ROLE_UNQUALIFIED")
                    attempts = 0
                else:
                    if current_checkpoint != role["checkpoint_sha256"]:
                        current_checkpoint = role["checkpoint_sha256"]
                        self.model_reloads += 1
                    lease_id: str | None = None
                    if job["phase"] == "GPU":
                        self._event("GPU_LEASE_WAIT", "GPU_LEASE_WAIT", node_id=node, phase="GPU")
                        lease_id = self.lease_adapter.acquire(self.contract["campaign_id"], node)
                        self.coordinator_churn += 1
                        if not lease_id or not self.lease_adapter.validate(lease_id):
                            if lease_id:
                                self.lease_adapter.release(lease_id, "lease_lost")
                            outcome = JobOutcome("BLOCKED", canonical_bytes({"node": node, "reason": "LEASE_UNAVAILABLE_OR_LOST"}), "LEASE_UNAVAILABLE_OR_LOST")
                            attempts = 0
                        else:
                            outcome, attempts = self._attempt(job, runner, max_attempts, repair_attempts)
                            self.lease_adapter.release(lease_id, outcome.state)
                    else:
                        self._event("CPU_PHASE_ACTIVE", "CPU_PHASE_ACTIVE", node_id=node, phase="CPU")
                        outcome, attempts = self._attempt(job, runner, max_attempts, repair_attempts)
                if outcome.state not in TERMINAL:
                    outcome = JobOutcome("FAIL", canonical_bytes({"node": node, "reason": "INVALID_OUTCOME"}), "INVALID_OUTCOME")
                sha, path = self._store(outcome.artifact)
                self.results[node] = {"node_id": node, "terminal_state": outcome.state, "attempts": attempts, "evidence_sha256": sha, "evidence_path": path, "reason": outcome.reason}
                self._event("JOB_TERMINAL", "DAG_ADVANCE", node_id=node, phase=job["phase"], payload=self.results[node])
                remaining.remove(node)
        return self._result()

    def _attempt(self, job: dict[str, Any], runner: Callable[[dict[str, Any], int, bool], JobOutcome], max_attempts: int, repair_attempts: int) -> tuple[JobOutcome, int]:
        last = JobOutcome("FAIL", b"", "NO_ATTEMPT")
        for attempt in range(1, max_attempts + 1):
            self._event("JOB_DISPATCH", "JOB_DISPATCH", node_id=job["node_id"], phase=job["phase"], payload={"attempt": attempt})
            last = runner(job, attempt, False)
            if last.state == "PASS":
                return last, attempt
            if last.repairable and attempt <= repair_attempts:
                repaired = runner(job, attempt, True)
                if repaired.state == "PASS":
                    return repaired, attempt + 1
                last = repaired
        if last.reason in {"OOM", "TIMEOUT", "ROLLBACK_REQUIRED"}:
            last = JobOutcome("ROLLED_BACK", last.artifact, last.reason)
        return last, max_attempts

    def restart_cursor(self) -> dict[str, Any]:
        self.verify_journal(self.events)
        return {"last_sequence": len(self.events) - 1, "last_event_hash": self.events[-1]["event_hash"], "completed_nodes": sorted(node for node, result in self.results.items() if result["terminal_state"] == "PASS"), "in_flight_nodes_assumed_complete": False}

    @classmethod
    def restore(cls, contract: dict[str, Any], workspace: Path, lease_adapter: LeaseAdapter, events: list[dict[str, Any]], results: dict[str, dict[str, Any]]) -> "CampaignExecutor":
        cls.verify_journal(events)
        if events and events[-1]["event_type"] == "JOB_DISPATCH":
            raise ValueError("restart refuses to assume an in-flight job completed")
        restored = cls(contract, workspace, lease_adapter)
        restored.events = copy.deepcopy(events)
        restored.results = copy.deepcopy(results)
        restored._event("RESTART_REPLAY", "RESTART_REPLAY", payload={"completed_nodes": sorted(results)})
        return restored

    @staticmethod
    def _merkle_root(hashes: list[str]) -> str:
        level = sorted(hashes)
        if not level:
            return digest(b"")
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [digest(bytes.fromhex(level[index]) + bytes.fromhex(level[index + 1])) for index in range(0, len(level), 2)]
        return level[0]

    @staticmethod
    def verify_result_identity(result: dict[str, Any]) -> None:
        candidate = copy.deepcopy(result)
        observed = candidate["result_id"]
        candidate["result_id"] = RESULT_ID_PLACEHOLDER
        if digest(candidate) != observed:
            raise ValueError("result_id does not match canonical result content")
        if CampaignExecutor._merkle_root([item["sha256"] for item in candidate["evidence"]]) != candidate["merkle_root_sha256"]:
            raise ValueError("result Merkle root mismatch")

    @staticmethod
    def seal_result(result: dict[str, Any]) -> dict[str, Any]:
        sealed = copy.deepcopy(result)
        sealed["merkle_root_sha256"] = CampaignExecutor._merkle_root([item["sha256"] for item in sealed["evidence"]])
        sealed["result_id"] = RESULT_ID_PLACEHOLDER
        sealed["result_id"] = digest(sealed)
        CampaignExecutor.verify_result_identity(sealed)
        return sealed

    def _result(self) -> dict[str, Any]:
        self.verify_journal(self.events)
        jobs = [self.results[node] for node in sorted(self.results)]
        passed = sum(item["terminal_state"] == "PASS" for item in jobs)
        complete = passed == len(jobs)
        evidence = [{"sha256": item["evidence_sha256"], "relative_path": item["evidence_path"], "media_type": "application/json", "size_bytes": (self.workspace / item["evidence_path"]).stat().st_size} for item in jobs]
        total = len(jobs)
        abstained = sum(item["terminal_state"] == "ABSTAINED" for item in jobs)
        first_pass = sum(item["terminal_state"] == "PASS" and item["attempts"] == 1 for item in jobs)
        evidence_bytes = sum(item["size_bytes"] for item in evidence)
        nullable = {
            "interruption_rate": None, "restart_replay_rate": None,
            "scope_authority_violations": None, "known_bad_false_accepts": None,
            "known_good_false_rejects": None, "codex_agreement_rate": None,
            "juror_disagreement_rate": None, "regression_escape_rate": None,
            "accepted_artifacts_per_hour": None, "gpu_seconds_per_accepted_artifact": None,
            "cpu_seconds_per_accepted_artifact": None, "storage_growth_bytes": None,
            "lease_wait_seconds": None, "interruption_count": None,
            "raw_evidence_bytes": evidence_bytes, "compacted_evidence_bytes": None,
        }
        nullable.update(self.measurements)
        metrics = {
            "autonomous_terminalization_rate": total / total,
            "evidence_completeness_rate": len(evidence) / total,
            "abstention_rate": abstained / total,
            "first_pass_validation_rate": first_pass / total,
            "repair_success_rate": sum(item["terminal_state"] == "PASS" and item["attempts"] > 1 for item in jobs) / max(1, sum(item["attempts"] > 1 for item in jobs)),
            "rework_rate": sum(item["attempts"] > 1 for item in jobs) / total,
            "model_reloads": self.model_reloads,
            "coordinator_churn": self.coordinator_churn,
            **nullable,
        }
        result = {
            "schema_version": "wave64.aqa.campaign_result.v1", "result_id": RESULT_ID_PLACEHOLDER, "campaign_id": self.contract["campaign_id"],
            "contract_sha256": digest(self.contract), "journal_head_sha256": self.events[-1]["event_hash"],
            "merkle_root_sha256": self._merkle_root([item["sha256"] for item in evidence]),
            "disposition": "COMPLETE" if complete else "PARTIAL_BLOCKED", "jobs": jobs, "evidence": evidence,
            "metrics": metrics,
            "cleanup": self.cleanup,
            "authority": {"self_promoted": False, "git_pushed": False, "thresholds_weakened": False, "final_acceptance_authority": "CODEX"},
            "proposed_delta": None,
        }
        self._event("CAMPAIGN_TERMINAL", result["disposition"], payload={"result_sha256": digest(result)})
        result["journal_head_sha256"] = self.events[-1]["event_hash"]
        return self.seal_result(result)


def render_summary(result: dict[str, Any]) -> str:
    anomalies = [f"{job['node_id']}={job['terminal_state']}:{job.get('reason', '')}" for job in result["jobs"] if job["terminal_state"] != "PASS"]
    completeness = result["metrics"]["evidence_completeness_rate"]
    return "\n".join([f"Campaign: {result['campaign_id']}", f"Result: {result['result_id']}", f"Disposition: {result['disposition']}", f"Terminalized: {len(result['jobs'])}", f"Evidence completeness: {completeness:.1%}" if completeness is not None else "Evidence completeness: NOT_MEASURED", "Anomalies: " + (", ".join(anomalies) if anomalies else "none")]) + "\n"
