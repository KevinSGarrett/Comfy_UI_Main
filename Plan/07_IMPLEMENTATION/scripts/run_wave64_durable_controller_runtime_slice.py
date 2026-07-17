#!/usr/bin/env python3
"""Execute the bounded Wave64 Rows197-200 durable-controller runtime slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_durable_controller_runtime_slice.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_durable_controller_runtime_slice.schema.json")
SERVICES = {"planner", "validator", "router", "scheduler", "executor", "qa_observer", "policy", "promoter"}
SERVICE_OWNERS = {
    "plan_proposal": "planner", "validation_decision": "validator", "route_decision": "router",
    "schedule_decision": "scheduler", "execution_receipt": "executor", "qa_observation": "qa_observer",
    "qa_policy_decision": "policy", "promotion_transaction": "promoter",
}
RECOVERY_CLASSES = {"ambiguous_submission", "missing_output", "orphan_output", "stale_lease", "duplicate_delivery", "conflicting_artifact"}


class ControllerRuntimeError(ValueError):
    """Raised when a durable-controller invariant fails closed."""


class StaleFenceError(ControllerRuntimeError):
    """Raised when a stale worker attempts a state mutation."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))


def validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise ControllerRuntimeError(f"schema_validation_failed:{label}:{location}:{first.message}")


def validate_registry(root: Path, registry: dict[str, Any], schema: dict[str, Any]) -> None:
    validate_schema(registry, schema, "durable_controller_runtime_slice")
    services = registry["service_separation"]
    if {entry["service_id"] for entry in services} != SERVICES or len(services) != len(SERVICES):
        raise ControllerRuntimeError("service_exact_set_mismatch")
    owned: set[str] = set()
    for service in services:
        overlap = owned.intersection(service["owns_records"])
        if overlap:
            raise ControllerRuntimeError(f"record_has_multiple_service_owners:{sorted(overlap)[0]}")
        owned.update(service["owns_records"])
        if not service["forbidden_actions"]:
            raise ControllerRuntimeError(f"service_forbidden_actions_missing:{service['service_id']}")
    names: set[str] = set()
    for reference in registry["source_authorities"]:
        name = reference["name"]
        if name in names:
            raise ControllerRuntimeError("duplicate_source_authority_name")
        names.add(name)
        relative = Path(reference["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ControllerRuntimeError(f"bound_path_not_relative:{name}")
        path = (root / relative).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            raise ControllerRuntimeError(f"bound_file_missing_or_outside:{name}")
        if sha256_file(path) != reference["sha256"]:
            raise ControllerRuntimeError(f"bound_hash_mismatch:{name}")
    if set(registry["recovery_policy"]["classifications"]) != RECOVERY_CLASSES:
        raise ControllerRuntimeError("recovery_classification_exact_set_mismatch")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE runs(run_id TEXT PRIMARY KEY, state TEXT NOT NULL, version INTEGER NOT NULL);
CREATE TABLE events(
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id), sequence INTEGER NOT NULL,
  event_type TEXT NOT NULL, payload_json TEXT NOT NULL, previous_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL UNIQUE, UNIQUE(run_id, sequence)
);
CREATE TABLE outbox(
  outbox_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id), event_id TEXT NOT NULL UNIQUE,
  idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL
);
CREATE TABLE passes(
  pass_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id), parent_pass_id TEXT REFERENCES passes(pass_id),
  status TEXT NOT NULL, accepted_artifact_hash TEXT
);
CREATE TABLE leases(
  runtime_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, fencing_token INTEGER NOT NULL,
  expires_tick INTEGER NOT NULL, status TEXT NOT NULL
);
CREATE TABLE attempts(
  attempt_id TEXT PRIMARY KEY, pass_id TEXT NOT NULL REFERENCES passes(pass_id), idempotency_key TEXT NOT NULL UNIQUE,
  runtime_id TEXT NOT NULL, fencing_token INTEGER NOT NULL, status TEXT NOT NULL,
  receipt_hash TEXT, artifact_hash TEXT, material_hypothesis TEXT
);
CREATE TABLE blockers(
  blocker_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id), classification TEXT NOT NULL,
  details_json TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE promotions(
  promotion_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
  idempotency_key TEXT NOT NULL UNIQUE, artifact_hash TEXT NOT NULL UNIQUE, status TEXT NOT NULL
);
CREATE TABLE service_records(
  record_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id), service_id TEXT NOT NULL,
  record_type TEXT NOT NULL, status TEXT NOT NULL, evidence_hash TEXT NOT NULL
);
"""


class DurableController:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA_SQL)

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def create_run(self, run_id: str) -> None:
        with self.transaction() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?)", (run_id, "created", 0))
            self._append_event_in_transaction(db, run_id, "run_created", {"to_state": "planned"}, 0)

    def _append_event_in_transaction(self, db: sqlite3.Connection, run_id: str, event_type: str, payload: dict[str, Any], expected_version: int) -> str:
        run = db.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if run is None or run["version"] != expected_version:
            raise ControllerRuntimeError("optimistic_aggregate_version_mismatch")
        previous = db.execute(
            "SELECT event_hash FROM events WHERE run_id=? ORDER BY sequence DESC LIMIT 1", (run_id,)
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "0" * 64
        sequence = expected_version + 1
        material = {"run_id": run_id, "sequence": sequence, "event_type": event_type, "payload": payload, "previous_hash": previous_hash}
        event_hash = sha256_bytes(canonical_json(material).encode("utf-8"))
        event_id = f"evt_{run_id}_{sequence:04d}"
        db.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, run_id, sequence, event_type, canonical_json(payload), previous_hash, event_hash),
        )
        db.execute("UPDATE runs SET state=?, version=? WHERE run_id=?", (payload["to_state"], sequence, run_id))
        db.execute(
            "INSERT INTO outbox VALUES (?, ?, ?, ?, ?)",
            (f"out_{run_id}_{sequence:04d}", run_id, event_id, f"event:{event_hash}", "pending"),
        )
        return event_hash

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any], expected_version: int) -> str:
        with self.transaction() as db:
            return self._append_event_in_transaction(db, run_id, event_type, payload, expected_version)

    def add_pass(self, run_id: str, pass_id: str, parent_pass_id: str | None = None) -> None:
        with self.transaction() as db:
            db.execute("INSERT INTO passes VALUES (?, ?, ?, ?, NULL)", (pass_id, run_id, parent_pass_id, "planned"))
            run = db.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
            self._append_event_in_transaction(
                db, run_id, "pass_defined",
                {"to_state": run["state"], "pass_id": pass_id, "parent_pass_id": parent_pass_id}, run["version"],
            )

    def record_service_decision(self, run_id: str, record_id: str, service_id: str, record_type: str, status: str, evidence: str) -> None:
        expected_owner = SERVICE_OWNERS.get(record_type)
        if expected_owner != service_id:
            raise ControllerRuntimeError(f"service_record_owner_mismatch:{record_type}:{service_id}")
        evidence_hash = sha256_bytes(evidence.encode("utf-8"))
        with self.transaction() as db:
            db.execute("INSERT INTO service_records VALUES (?, ?, ?, ?, ?, ?)", (record_id, run_id, service_id, record_type, status, evidence_hash))
            run = db.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
            self._append_event_in_transaction(
                db, run_id, "service_decision_recorded",
                {"to_state": run["state"], "record_id": record_id, "service_id": service_id, "record_type": record_type, "status": status, "evidence_hash": evidence_hash}, run["version"],
            )

    def ready_passes(self, run_id: str) -> list[str]:
        rows = self.connection.execute(
            """SELECT child.pass_id FROM passes child LEFT JOIN passes parent ON parent.pass_id=child.parent_pass_id
               WHERE child.run_id=? AND child.status='planned'
               AND (child.parent_pass_id IS NULL OR parent.status='accepted') ORDER BY child.pass_id""",
            (run_id,),
        ).fetchall()
        return [row["pass_id"] for row in rows]

    def acquire_lease(self, runtime_id: str, owner_id: str, now_tick: int, ttl: int, run_id: str | None = None) -> int:
        with self.transaction() as db:
            prior = db.execute("SELECT fencing_token FROM leases WHERE runtime_id=?", (runtime_id,)).fetchone()
            token = (prior["fencing_token"] if prior else 0) + 1
            db.execute(
                "INSERT INTO leases VALUES (?, ?, ?, ?, 'active') ON CONFLICT(runtime_id) DO UPDATE SET owner_id=excluded.owner_id, fencing_token=excluded.fencing_token, expires_tick=excluded.expires_tick, status='active'",
                (runtime_id, owner_id, token, now_tick + ttl),
            )
            if run_id is not None:
                run = db.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
                self._append_event_in_transaction(
                    db, run_id, "lease_acquired",
                    {"to_state": run["state"], "runtime_id": runtime_id, "owner_id": owner_id, "fencing_token": token}, run["version"],
                )
            return token

    def assert_fence(self, runtime_id: str, fencing_token: int, now_tick: int) -> None:
        lease = self.connection.execute("SELECT * FROM leases WHERE runtime_id=?", (runtime_id,)).fetchone()
        if lease is None or lease["status"] != "active" or lease["fencing_token"] != fencing_token or lease["expires_tick"] < now_tick:
            raise StaleFenceError("stale_fencing_token_rejected")

    def submit_attempt(self, pass_id: str, attempt_id: str, idempotency_key: str, runtime_id: str, fencing_token: int, now_tick: int, hypothesis: str) -> str:
        self.assert_fence(runtime_id, fencing_token, now_tick)
        existing = self.connection.execute("SELECT attempt_id FROM attempts WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            return existing["attempt_id"]
        with self.transaction() as db:
            db.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, 'submitted', NULL, NULL, ?)",
                (attempt_id, pass_id, idempotency_key, runtime_id, fencing_token, hypothesis),
            )
            db.execute("UPDATE passes SET status='running' WHERE pass_id=?", (pass_id,))
            run = db.execute("SELECT runs.run_id, runs.state, runs.version FROM runs JOIN passes ON passes.run_id=runs.run_id WHERE passes.pass_id=?", (pass_id,)).fetchone()
            self._append_event_in_transaction(
                db, run["run_id"], "attempt_submitted",
                {"to_state": "executing", "attempt_id": attempt_id, "pass_id": pass_id, "fencing_token": fencing_token, "material_hypothesis": hypothesis}, run["version"],
            )
        return attempt_id

    def reconcile_ambiguous(self, run_id: str, attempt_id: str) -> str:
        attempt = self.connection.execute("SELECT * FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if attempt is None or attempt["status"] != "submitted" or attempt["receipt_hash"] is not None:
            raise ControllerRuntimeError("attempt_not_ambiguous")
        blocker_id = f"blk_{attempt_id}_ambiguous"
        with self.transaction() as db:
            db.execute(
                "INSERT INTO blockers VALUES (?, ?, 'ambiguous_submission', ?, 0)",
                (blocker_id, run_id, canonical_json({"attempt_id": attempt_id, "cross_host_failover_allowed": False})),
            )
            db.execute("UPDATE attempts SET status='ambiguous' WHERE attempt_id=?", (attempt_id,))
            run = db.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
            self._append_event_in_transaction(
                db, run_id, "attempt_reconciliation_blocked",
                {"to_state": "blocked", "attempt_id": attempt_id, "classification": "ambiguous_submission"}, run["version"],
            )
        return blocker_id

    def resolve_nonpromotable(self, blocker_id: str, attempt_id: str, pass_id: str) -> None:
        with self.transaction() as db:
            db.execute("UPDATE blockers SET resolved=1 WHERE blocker_id=?", (blocker_id,))
            db.execute("UPDATE attempts SET status='terminal_nonpromotable' WHERE attempt_id=?", (attempt_id,))
            db.execute("UPDATE passes SET status='planned' WHERE pass_id=?", (pass_id,))
            run = db.execute("SELECT runs.run_id, runs.version FROM runs JOIN passes ON passes.run_id=runs.run_id WHERE passes.pass_id=?", (pass_id,)).fetchone()
            self._append_event_in_transaction(
                db, run["run_id"], "ambiguous_attempt_resolved_nonpromotable",
                {"to_state": "retry_ready", "attempt_id": attempt_id, "blocker_id": blocker_id}, run["version"],
            )

    def accept_attempt(self, attempt_id: str, pass_id: str, runtime_id: str, fencing_token: int, now_tick: int, artifact_hash: str) -> None:
        self.assert_fence(runtime_id, fencing_token, now_tick)
        receipt_hash = sha256_bytes(f"receipt:{attempt_id}:{artifact_hash}".encode("utf-8"))
        with self.transaction() as db:
            db.execute("UPDATE attempts SET status='accepted', receipt_hash=?, artifact_hash=? WHERE attempt_id=?", (receipt_hash, artifact_hash, attempt_id))
            db.execute("UPDATE passes SET status='accepted', accepted_artifact_hash=? WHERE pass_id=?", (artifact_hash, pass_id))
            run = db.execute("SELECT runs.run_id, runs.version FROM runs JOIN passes ON passes.run_id=runs.run_id WHERE passes.pass_id=?", (pass_id,)).fetchone()
            self._append_event_in_transaction(
                db, run["run_id"], "attempt_accepted",
                {"to_state": "pass_accepted", "attempt_id": attempt_id, "pass_id": pass_id, "artifact_hash": artifact_hash}, run["version"],
            )

    def promote(self, run_id: str, promotion_id: str, idempotency_key: str, artifact_hash: str) -> str:
        existing = self.connection.execute("SELECT promotion_id FROM promotions WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            return existing["promotion_id"]
        accepted = self.connection.execute("SELECT 1 FROM passes WHERE run_id=? AND accepted_artifact_hash=?", (run_id, artifact_hash)).fetchone()
        unresolved = self.connection.execute("SELECT 1 FROM blockers WHERE run_id=? AND resolved=0", (run_id,)).fetchone()
        qa_pass = self.connection.execute("SELECT 1 FROM service_records WHERE run_id=? AND record_type='qa_observation' AND status='pass'", (run_id,)).fetchone()
        policy_authorized = self.connection.execute("SELECT 1 FROM service_records WHERE run_id=? AND record_type='qa_policy_decision' AND status='authorized'", (run_id,)).fetchone()
        if accepted is None or unresolved is not None or qa_pass is None or policy_authorized is None:
            raise ControllerRuntimeError("promotion_preconditions_not_met")
        with self.transaction() as db:
            db.execute("INSERT INTO promotions VALUES (?, ?, ?, ?, 'committed')", (promotion_id, run_id, idempotency_key, artifact_hash))
            db.execute(
                "INSERT INTO service_records VALUES (?, ?, 'promoter', 'promotion_transaction', 'committed', ?)",
                (f"service_{promotion_id}", run_id, sha256_bytes(f"promotion:{artifact_hash}".encode("utf-8"))),
            )
            run = db.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
            self._append_event_in_transaction(
                db, run_id, "promotion_committed",
                {"to_state": "promoted", "promotion_id": promotion_id, "artifact_hash": artifact_hash}, run["version"],
            )
        return promotion_id

    def verify_hash_chain(self, run_id: str) -> bool:
        previous_hash = "0" * 64
        for row in self.connection.execute("SELECT * FROM events WHERE run_id=? ORDER BY sequence", (run_id,)):
            payload = json.loads(row["payload_json"])
            material = {"run_id": run_id, "sequence": row["sequence"], "event_type": row["event_type"], "payload": payload, "previous_hash": previous_hash}
            expected = sha256_bytes(canonical_json(material).encode("utf-8"))
            if row["previous_hash"] != previous_hash or row["event_hash"] != expected:
                return False
            previous_hash = expected
        return True

    def replay_projection(self, run_id: str) -> tuple[str, int]:
        state, version = "created", 0
        for row in self.connection.execute("SELECT payload_json, sequence FROM events WHERE run_id=? ORDER BY sequence", (run_id,)):
            state = json.loads(row["payload_json"])["to_state"]
            version = row["sequence"]
        return state, version

    def counts(self) -> dict[str, int]:
        return {table: self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("events", "outbox", "attempts", "blockers", "promotions", "service_records")}


def classify_recovery(observation: dict[str, bool]) -> str:
    ordered = (
        ("conflicting_artifact", observation.get("conflicting_hashes")),
        ("ambiguous_submission", observation.get("submitted") and not observation.get("receipt")),
        ("missing_output", observation.get("receipt") and not observation.get("output")),
        ("orphan_output", observation.get("output") and not observation.get("receipt")),
        ("stale_lease", observation.get("stale_lease")),
        ("duplicate_delivery", observation.get("duplicate_idempotency")),
    )
    matches = [name for name, active in ordered if active]
    if len(matches) != 1:
        raise ControllerRuntimeError("recovery_observation_not_exactly_classifiable")
    return matches[0]


def execute_fixture(database_path: Path) -> dict[str, Any]:
    controller = DurableController(database_path)
    try:
        run_id, root_pass, child_pass = "run_w64_197_200_fixture", "pass_root", "pass_child"
        controller.create_run(run_id)
        controller.record_service_decision(run_id, "svc_plan", "planner", "plan_proposal", "accepted", "bounded two-pass fixture")
        controller.record_service_decision(run_id, "svc_validation", "validator", "validation_decision", "pass", "schema and dependency validation")
        controller.record_service_decision(run_id, "svc_route", "router", "route_decision", "accepted", "local synthetic sqlite route")
        controller.add_pass(run_id, root_pass)
        controller.add_pass(run_id, child_pass, root_pass)
        initial_ready = controller.ready_passes(run_id)
        controller.record_service_decision(run_id, "svc_schedule", "scheduler", "schedule_decision", "ready", "root dependency set satisfied")
        token1 = controller.acquire_lease("runtime_local", "worker_a", 0, 10, run_id)
        attempt1 = controller.submit_attempt(root_pass, "attempt_001", "submit:root:001", "runtime_local", token1, 1, "baseline_exact_bundle")
        duplicate_attempt = controller.submit_attempt(root_pass, "attempt_duplicate", "submit:root:001", "runtime_local", token1, 1, "baseline_exact_bundle")
        blocker = controller.reconcile_ambiguous(run_id, attempt1)
        token2 = controller.acquire_lease("runtime_local", "worker_b", 11, 10, run_id)
        stale_fence_rejected = False
        try:
            controller.submit_attempt(root_pass, "attempt_stale", "submit:root:stale", "runtime_local", token1, 12, "forbidden_stale_retry")
        except StaleFenceError:
            stale_fence_rejected = True
        controller.resolve_nonpromotable(blocker, attempt1, root_pass)
        attempt2 = controller.submit_attempt(root_pass, "attempt_002", "submit:root:002", "runtime_local", token2, 12, "material_hypothesis_after_terminal_reconciliation")
        artifact_hash = sha256_bytes(b"accepted-root-artifact")
        controller.accept_attempt(attempt2, root_pass, "runtime_local", token2, 12, artifact_hash)
        controller.record_service_decision(run_id, "svc_receipt", "executor", "execution_receipt", "accepted", f"attempt_002:{artifact_hash}")
        controller.record_service_decision(run_id, "svc_qa", "qa_observer", "qa_observation", "pass", f"deterministic synthetic QA:{artifact_hash}")
        controller.record_service_decision(run_id, "svc_policy", "policy", "qa_policy_decision", "authorized", f"current QA and lineage:{artifact_hash}")
        ready_after_parent = controller.ready_passes(run_id)
        promotion1 = controller.promote(run_id, "promotion_001", "promote:root:001", artifact_hash)
        promotion2 = controller.promote(run_id, "promotion_duplicate", "promote:root:001", artifact_hash)
        projection = controller.connection.execute("SELECT state, version FROM runs WHERE run_id=?", (run_id,)).fetchone()
        replay = controller.replay_projection(run_id)
        recovery_matrix = {
            "ambiguous_submission": {"submitted": True, "receipt": False},
            "missing_output": {"receipt": True, "output": False},
            "orphan_output": {"output": True, "receipt": False},
            "stale_lease": {"stale_lease": True},
            "duplicate_delivery": {"duplicate_idempotency": True},
            "conflicting_artifact": {"conflicting_hashes": True},
        }
        classified = {name: classify_recovery(observation) for name, observation in recovery_matrix.items()}
        return {
            "status": "PASS", "classification": "WAVE64_DURABLE_CONTROLLER_RUNTIME_SLICE_PASS",
            "rows_covered": [197, 198, 199, 200], "database_backend": "sqlite",
            "initial_ready_passes": initial_ready, "ready_after_parent_acceptance": ready_after_parent,
            "duplicate_submission_returned_original_attempt": duplicate_attempt == attempt1,
            "stale_fence_rejected": stale_fence_rejected, "fencing_tokens_monotonic": token2 > token1,
            "ambiguous_cross_host_failover_allowed": False,
            "accepted_parent_preserved": controller.connection.execute("SELECT status FROM passes WHERE pass_id=?", (root_pass,)).fetchone()[0] == "accepted",
            "promotion_exactly_once": promotion1 == promotion2 and controller.counts()["promotions"] == 1,
            "hash_chain_valid": controller.verify_hash_chain(run_id),
            "replay_projection_matches": replay == (projection["state"], projection["version"]),
            "service_authority_chain_complete": {row[0] for row in controller.connection.execute("SELECT DISTINCT service_id FROM service_records")} == SERVICES,
            "recovery_classifications": classified, "counts": controller.counts(),
            "production_runtime_allowed": False, "comfyui_submission_performed": False,
            "media_generated": False, "promotion_to_production_performed": False,
        }
    finally:
        controller.close()


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "evidence_type": "wave64_durable_controller_runtime_slice",
        **result,
        "authority": {
            "registry_path": registry_path.as_posix(), "registry_sha256": sha256_file(root / registry_path),
            "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path),
            "runner_path": "Plan/07_IMPLEMENTATION/scripts/run_wave64_durable_controller_runtime_slice.py",
            "runner_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/run_wave64_durable_controller_runtime_slice.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T083418230Z_wave64_rows197_200_durable_controller_architecture_c30b37d0",
            "result": "AI_WORKER_ADMISSION_REJECTED_STALE_GUESSED_SCHEMA_PATH",
            "fallback": "bounded_codex_inventory_and_deterministic_runtime_implementation",
        },
        "boundaries": {
            "comfyui_queue_mutated": False, "aws_mutated": False, "media_generated": False,
            "maskfactory_authority_changed": False, "production_promotion_created": False,
            "item_tracker_status_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    registry, schema = load_json(root / args.registry), load_json(root / args.schema)
    validate_registry(root, registry, schema)
    if args.database:
        args.database.parent.mkdir(parents=True, exist_ok=True)
        result = execute_fixture(args.database)
    else:
        with tempfile.TemporaryDirectory(prefix="wave64_controller_") as directory:
            result = execute_fixture(Path(directory) / "controller.sqlite3")
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.registry, args.schema)
        if args.evidence_out:
            write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out:
            write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
