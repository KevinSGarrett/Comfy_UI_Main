#!/usr/bin/env python3
"""Durable fail-closed mission controller for the RunPod autonomous work-cell."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
MISSION_SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_mission_envelope.schema.json"
STATE_SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_mission_queue_state.schema.json"
CAMPAIGN_COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_contract.py"
CAMPAIGN_EXECUTOR = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign.py"
ID_PLACEHOLDER = "0" * 64
GENESIS_HASH = hashlib.sha256(b"W64-AQA-MISSION-JOURNAL-GENESIS-V1").hexdigest()
MISSION_ID = re.compile(r"^[a-f0-9]{64}$")
WORKER_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
LEGAL_TRANSITIONS = {
    None: {"MISSION_ADMITTED"},
    "MISSION_ADMITTED": {"MISSION_CLAIMED"},
    "MISSION_CLAIMED": {
        "MISSION_HEARTBEAT",
        "MISSION_CHECKPOINTED",
        "MISSION_DEFERRED",
        "MISSION_RECOVERED",
        "MISSION_TERMINALIZED",
    },
    "MISSION_HEARTBEAT": {
        "MISSION_HEARTBEAT",
        "MISSION_CHECKPOINTED",
        "MISSION_DEFERRED",
        "MISSION_RECOVERED",
        "MISSION_TERMINALIZED",
    },
    "MISSION_CHECKPOINTED": {
        "MISSION_HEARTBEAT",
        "MISSION_CHECKPOINTED",
        "MISSION_DEFERRED",
        "MISSION_RECOVERED",
        "MISSION_TERMINALIZED",
    },
    "MISSION_DEFERRED": {"MISSION_CLAIMED"},
    "MISSION_RECOVERED": {"MISSION_CLAIMED"},
    "MISSION_TERMINALIZED": set(),
}


class MissionError(ValueError):
    """Raised when a mission violates an immutable or durable invariant."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MissionError(f"cannot load required control module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_relative(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return bool(path.parts) and not path.is_absolute() and ":" not in path.parts[0] and ".." not in path.parts


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissionError("timestamp must be RFC3339") from exc
    if parsed.tzinfo is None:
        raise MissionError("timestamp must include an offset")
    return value


def _schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bound_campaign(mission: dict[str, Any], repository_root: Path) -> tuple[dict[str, Any], bytes]:
    binding = mission["campaign"]
    if not _safe_relative(binding["relative_path"]):
        raise MissionError("campaign path escapes repository")
    root = repository_root.resolve()
    path = (root / binding["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise MissionError("campaign path escapes repository") from exc
    if not path.is_file():
        raise MissionError("bound campaign contract is missing")
    payload = path.read_bytes()
    if digest(payload) != binding["sha256"]:
        raise MissionError("bound campaign contract hash mismatch")
    try:
        contract = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise MissionError("bound campaign contract is invalid JSON") from exc
    if contract.get("campaign_id") != binding["campaign_id"]:
        raise MissionError("bound campaign_id mismatch")
    compiler = _load_module(CAMPAIGN_COMPILER, "w64_campaign_contract_compiler")
    try:
        compiler.verify_contract(contract)
    except (jsonschema.ValidationError, ValueError) as exc:
        raise MissionError(f"bound campaign contract is invalid: {exc}") from exc
    return contract, payload


def compile_mission(draft: dict[str, Any], repository_root: Path) -> dict[str, Any]:
    if "mission_id" in draft:
        raise MissionError("mission draft must not supply mission_id")
    mission = copy.deepcopy(draft)
    mission["mission_id"] = ID_PLACEHOLDER
    validator = jsonschema.Draft7Validator(
        _schema(MISSION_SCHEMA), format_checker=jsonschema.FormatChecker()
    )
    try:
        validator.validate(mission)
    except jsonschema.ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "$"
        raise MissionError(f"mission schema violation at {location}: {exc.message}") from exc
    if any(not _safe_relative(path) for path in mission["execution"]["allowed_paths"]):
        raise MissionError("allowed path escapes repository")
    _bound_campaign(mission, repository_root)
    mission["mission_id"] = digest(mission)
    validator.validate(mission)
    return mission


def verify_mission(mission: dict[str, Any], repository_root: Path) -> tuple[dict[str, Any], bytes]:
    jsonschema.Draft7Validator(
        _schema(MISSION_SCHEMA), format_checker=jsonschema.FormatChecker()
    ).validate(mission)
    candidate = copy.deepcopy(mission)
    observed = candidate["mission_id"]
    candidate["mission_id"] = ID_PLACEHOLDER
    if digest(candidate) != observed:
        raise MissionError("mission_id does not match canonical mission content")
    if any(not _safe_relative(path) for path in mission["execution"]["allowed_paths"]):
        raise MissionError("allowed path escapes repository")
    return _bound_campaign(mission, repository_root)


class MissionQueue:
    """SQLite-backed queue with atomic snapshots and an append-only hash journal."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.cas = self.root / "cas" / "sha256"
        self.database = self.root / "mission_queue.sqlite3"
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    contract_sha256 TEXT NOT NULL,
                    mission_json BLOB NOT NULL,
                    campaign_json BLOB NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','TERMINAL')),
                    worker_id TEXT,
                    heartbeat_at TEXT,
                    checkpoint_sha256 TEXT,
                    result_id TEXT,
                    event_count INTEGER NOT NULL,
                    journal_head_sha256 TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mission_events (
                    mission_id TEXT NOT NULL REFERENCES missions(mission_id),
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    PRIMARY KEY(mission_id, sequence)
                );
                CREATE TRIGGER IF NOT EXISTS mission_events_no_update
                BEFORE UPDATE ON mission_events BEGIN
                    SELECT RAISE(ABORT, 'MISSION_JOURNAL_APPEND_ONLY');
                END;
                CREATE TRIGGER IF NOT EXISTS mission_events_no_delete
                BEFORE DELETE ON mission_events BEGIN
                    SELECT RAISE(ABORT, 'MISSION_JOURNAL_APPEND_ONLY');
                END;
                CREATE TRIGGER IF NOT EXISTS missions_immutable_identity
                BEFORE UPDATE OF mission_id,campaign_id,contract_sha256,mission_json,campaign_json
                ON missions BEGIN
                    SELECT RAISE(ABORT, 'MISSION_IDENTITY_IMMUTABLE');
                END;
                CREATE TRIGGER IF NOT EXISTS missions_no_delete
                BEFORE DELETE ON missions BEGIN
                    SELECT RAISE(ABORT, 'MISSION_RECORD_RETENTION_REQUIRED');
                END;
                """
            )

    @staticmethod
    def _require_mission_id(mission_id: str) -> None:
        if MISSION_ID.fullmatch(mission_id) is None:
            raise MissionError("invalid mission_id")

    @staticmethod
    def _require_worker(worker_id: str) -> None:
        if WORKER_ID.fullmatch(worker_id) is None:
            raise MissionError("invalid worker_id")

    def _append(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row | dict[str, Any],
        event_type: str,
        state: str,
        at: str,
        payload: dict[str, Any],
    ) -> tuple[int, str]:
        sequence = int(row["event_count"])
        previous_hash = str(row["journal_head_sha256"])
        previous_type = None
        if sequence:
            previous = connection.execute(
                "SELECT event_type FROM mission_events WHERE mission_id=? AND sequence=?",
                (row["mission_id"], sequence - 1),
            ).fetchone()
            if previous is None:
                raise MissionError("mission journal head is missing")
            previous_type = previous["event_type"]
        if event_type not in LEGAL_TRANSITIONS.get(previous_type, set()):
            raise MissionError(f"illegal mission transition: {previous_type}->{event_type}")
        event = {
            "schema_version": "wave64.aqa.mission_event.v1",
            "mission_id": row["mission_id"],
            "sequence": sequence,
            "at": _timestamp(at),
            "event_type": event_type,
            "state": state,
            "payload": payload,
            "payload_sha256": digest(payload),
            "previous_hash": previous_hash,
            "event_hash": ID_PLACEHOLDER,
        }
        event["event_hash"] = digest(event)
        connection.execute(
            "INSERT INTO mission_events(mission_id,sequence,event_type,event_json,event_hash) VALUES(?,?,?,?,?)",
            (
                row["mission_id"],
                sequence,
                event_type,
                canonical_bytes(event).decode(),
                event["event_hash"],
            ),
        )
        return sequence + 1, event["event_hash"]

    def admit(
        self, mission: dict[str, Any], repository_root: Path, *, at: str
    ) -> dict[str, Any]:
        contract, campaign_payload = verify_mission(mission, repository_root)
        mission_payload = canonical_bytes(mission)
        mission_id = mission["mission_id"]
        self._require_mission_id(mission_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if existing is not None:
                if bytes(existing["mission_json"]) != mission_payload or bytes(
                    existing["campaign_json"]
                ) != campaign_payload:
                    raise MissionError("mission identity collision")
                connection.commit()
                return self.status(mission_id)
            seed = {
                "mission_id": mission_id,
                "event_count": 0,
                "journal_head_sha256": GENESIS_HASH,
            }
            connection.execute(
                "INSERT INTO missions VALUES(?,?,?,?,?,'QUEUED',NULL,NULL,NULL,NULL,0,?)",
                (
                    mission_id,
                    contract["campaign_id"],
                    digest(campaign_payload),
                    mission_payload,
                    campaign_payload,
                    GENESIS_HASH,
                ),
            )
            count, head = self._append(
                connection,
                seed,
                "MISSION_ADMITTED",
                "QUEUED",
                at,
                {"campaign_id": contract["campaign_id"]},
            )
            connection.execute(
                "UPDATE missions SET event_count=?,journal_head_sha256=? WHERE mission_id=?",
                (count, head, mission_id),
            )
            connection.commit()
        return self.status(mission_id)

    def claim(self, mission_id: str, worker_id: str, *, at: str) -> dict[str, Any]:
        self._require_mission_id(mission_id)
        self._require_worker(worker_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if row is None:
                raise MissionError("mission not found")
            if row["state"] == "RUNNING" and row["worker_id"] == worker_id:
                connection.commit()
                return self.status(mission_id)
            if row["state"] != "QUEUED":
                raise MissionError("mission is not claimable")
            count, head = self._append(
                connection,
                row,
                "MISSION_CLAIMED",
                "RUNNING",
                at,
                {"worker_id": worker_id},
            )
            connection.execute(
                "UPDATE missions SET state='RUNNING',worker_id=?,heartbeat_at=?,event_count=?,journal_head_sha256=? WHERE mission_id=?",
                (worker_id, at, count, head, mission_id),
            )
            connection.commit()
        return self.status(mission_id)

    def heartbeat(self, mission_id: str, worker_id: str, *, at: str) -> dict[str, Any]:
        return self._owned_event(mission_id, worker_id, "MISSION_HEARTBEAT", at, {})

    def checkpoint(
        self,
        mission_id: str,
        worker_id: str,
        checkpoint: dict[str, Any],
        *,
        at: str,
    ) -> dict[str, Any]:
        self._assert_owner(mission_id, worker_id)
        sha, relative_path = self._store(canonical_bytes(checkpoint))
        return self._owned_event(
            mission_id,
            worker_id,
            "MISSION_CHECKPOINTED",
            at,
            {"checkpoint_sha256": sha, "relative_path": relative_path},
            checkpoint_sha256=sha,
        )

    def _assert_owner(self, mission_id: str, worker_id: str) -> sqlite3.Row:
        self._require_mission_id(mission_id)
        self._require_worker(worker_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None or row["state"] != "RUNNING" or row["worker_id"] != worker_id:
            raise MissionError("mission ownership mismatch")
        return row

    def _owned_event(
        self,
        mission_id: str,
        worker_id: str,
        event_type: str,
        at: str,
        payload: dict[str, Any],
        *,
        checkpoint_sha256: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission_id(mission_id)
        self._require_worker(worker_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if (
                row is None
                or row["state"] != "RUNNING"
                or row["worker_id"] != worker_id
            ):
                raise MissionError("mission ownership mismatch")
            count, head = self._append(connection, row, event_type, "RUNNING", at, payload)
            checkpoint_value = checkpoint_sha256 or row["checkpoint_sha256"]
            connection.execute(
                "UPDATE missions SET heartbeat_at=?,checkpoint_sha256=?,event_count=?,journal_head_sha256=? WHERE mission_id=?",
                (at, checkpoint_value, count, head, mission_id),
            )
            connection.commit()
        return self.status(mission_id)

    def recover_stale(
        self, mission_id: str, *, stale_before: str, at: str
    ) -> dict[str, Any]:
        """Retired compatibility entry point.

        A missed local heartbeat must never reclaim or requeue work that may be
        running on a separately selected RunPod.  Completion/release is now an
        explicit action by that session.
        """
        self._require_mission_id(mission_id)
        _timestamp(stale_before)
        # Verify that the requested mission exists but intentionally preserve
        # its owner/state.  ``stale_before`` is retained only for CLI backward
        # compatibility and has no scheduling effect.
        self.status(mission_id)
        return self.status(mission_id)

    def recover_confirmed_crash(
        self,
        mission_id: str,
        worker_id: str,
        *,
        at: str,
    ) -> dict[str, Any]:
        """Requeue an exact checkpointed mission after its owner confirms a crash.

        This is deliberately not a timeout or cross-session reclaim. The exact
        current owner must identify itself, a durable checkpoint must exist, and
        the recovery event records that no in-flight child is assumed complete.
        """
        self._require_mission_id(mission_id)
        self._require_worker(worker_id)
        _timestamp(at)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if row is None:
                raise MissionError("mission not found")
            if row["state"] != "RUNNING" or row["worker_id"] != worker_id:
                raise MissionError("confirmed crash ownership mismatch")
            if row["checkpoint_sha256"] is None:
                raise MissionError("confirmed crash requires a durable checkpoint")
            count, head = self._append(
                connection,
                row,
                "MISSION_RECOVERED",
                "QUEUED",
                at,
                {
                    "previous_worker_id": worker_id,
                    "checkpoint_sha256": row["checkpoint_sha256"],
                    "recovery_reason": "OWNER_CONFIRMED_CRASH",
                    "in_flight_assumed_complete": False,
                },
            )
            connection.execute(
                "UPDATE missions SET state='QUEUED',worker_id=NULL,heartbeat_at=NULL,"
                "event_count=?,journal_head_sha256=? WHERE mission_id=?",
                (count, head, mission_id),
            )
            connection.commit()
        return self.status(mission_id)

    def defer(
        self,
        mission_id: str,
        worker_id: str,
        checkpoint: dict[str, Any],
        *,
        reason: str,
        at: str,
    ) -> dict[str, Any]:
        """Return a claimed mission to the durable queue after a clean deferral.

        A GPU admission failure is neither a crash nor a terminal result.  The
        exact owner records a durable checkpoint and explicitly returns the
        mission to ``QUEUED`` without assuming any in-flight child completed.
        A future direct admission may then claim it; no timeout or unrelated
        session is allowed to perform that transition.
        """

        self._require_mission_id(mission_id)
        self._require_worker(worker_id)
        _timestamp(at)
        if not isinstance(reason, str) or not reason or len(reason) > 256:
            raise MissionError("deferral reason is invalid")
        if not isinstance(checkpoint, dict):
            raise MissionError("deferral checkpoint must be an object")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if row is None or row["state"] != "RUNNING" or row["worker_id"] != worker_id:
                raise MissionError("mission ownership mismatch")
            checkpoint_payload = copy.deepcopy(checkpoint)
            checkpoint_payload["in_flight_nodes_assumed_complete"] = False
            checkpoint_sha, checkpoint_path = self._store(
                canonical_bytes(checkpoint_payload)
            )
            count, head = self._append(
                connection,
                row,
                "MISSION_DEFERRED",
                "QUEUED",
                at,
                {
                    "worker_id": worker_id,
                    "reason": reason,
                    "checkpoint_sha256": checkpoint_sha,
                    "relative_path": checkpoint_path,
                    "in_flight_nodes_assumed_complete": False,
                },
            )
            connection.execute(
                "UPDATE missions SET state='QUEUED',worker_id=NULL,heartbeat_at=NULL,"
                "checkpoint_sha256=?,event_count=?,journal_head_sha256=? WHERE mission_id=?",
                (checkpoint_sha, count, head, mission_id),
            )
            connection.commit()
        return self.status(mission_id)

    def terminalize(
        self,
        mission_id: str,
        worker_id: str,
        result: dict[str, Any],
        evidence_root: Path,
        *,
        at: str,
    ) -> dict[str, Any]:
        self._require_mission_id(mission_id)
        self._require_worker(worker_id)
        owned = self._assert_owner(mission_id, worker_id)
        executor = _load_module(CAMPAIGN_EXECUTOR, "w64_campaign_executor")
        try:
            executor.CampaignExecutor.verify_result_identity(result)
        except ValueError as exc:
            raise MissionError(f"campaign result identity invalid: {exc}") from exc
        if result.get("campaign_id") != owned["campaign_id"]:
            raise MissionError("result campaign_id mismatch")
        self._verify_result_evidence(result, evidence_root)
        mission = json.loads(bytes(owned["mission_json"]))
        if result.get("disposition") not in mission["execution"]["terminal_states"]:
            raise MissionError("result disposition is not an allowed terminal state")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if row is None or row["state"] != "RUNNING" or row["worker_id"] != worker_id:
                raise MissionError("mission ownership mismatch")
            if result.get("campaign_id") != row["campaign_id"]:
                raise MissionError("result campaign_id mismatch")
            # Materialize the sealed result only after the write transaction has
            # revalidated ownership.  A concurrent stale-worker recovery cannot
            # pass this lock and leave an unreferenced result in CAS.
            result_sha, result_path = self._store(canonical_bytes(result))
            count, head = self._append(
                connection,
                row,
                "MISSION_TERMINALIZED",
                "TERMINAL",
                at,
                {
                    "result_id": result["result_id"],
                    "result_sha256": result_sha,
                    "relative_path": result_path,
                },
            )
            connection.execute(
                "UPDATE missions SET state='TERMINAL',result_id=?,event_count=?,journal_head_sha256=? WHERE mission_id=?",
                (result["result_id"], count, head, mission_id),
            )
            connection.commit()
        return self.status(mission_id)

    @staticmethod
    def _verify_result_evidence(result: dict[str, Any], evidence_root: Path) -> None:
        root = evidence_root.resolve()
        for item in result.get("evidence", []):
            relative_path = item.get("relative_path")
            if not isinstance(relative_path, str) or not _safe_relative(relative_path):
                raise MissionError("result evidence path escapes evidence root")
            path = (root / relative_path).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise MissionError("result evidence path escapes evidence root") from exc
            if not path.is_file():
                raise MissionError("result evidence file is missing")
            payload = path.read_bytes()
            if len(payload) != item.get("size_bytes"):
                raise MissionError("result evidence size mismatch")
            if digest(payload) != item.get("sha256"):
                raise MissionError("result evidence SHA-256 mismatch")

    def _store(self, payload: bytes) -> tuple[str, str]:
        sha = digest(payload)
        path = (self.cas / sha[:2] / sha).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise MissionError("CAS path escaped mission root") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise MissionError("CAS content collision")
        else:
            temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        return sha, path.relative_to(self.root).as_posix()

    def status(self, mission_id: str) -> dict[str, Any]:
        self._require_mission_id(mission_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise MissionError("mission not found")
        result = {
            "schema_version": "wave64.aqa.mission_queue_state.v1",
            "mission_id": row["mission_id"],
            "campaign_id": row["campaign_id"],
            "contract_sha256": row["contract_sha256"],
            "state": row["state"],
            "event_count": row["event_count"],
            "journal_head_sha256": row["journal_head_sha256"],
            "worker_id": row["worker_id"],
            "heartbeat_at": row["heartbeat_at"],
            "checkpoint_sha256": row["checkpoint_sha256"],
            "result_id": row["result_id"],
            "in_flight_assumed_complete": False,
        }
        jsonschema.Draft7Validator(
            _schema(STATE_SCHEMA), format_checker=jsonschema.FormatChecker()
        ).validate(result)
        return result

    def verify(self, mission_id: str) -> dict[str, Any]:
        state = self.status(mission_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM mission_events WHERE mission_id=? ORDER BY sequence",
                (mission_id,),
            ).fetchall()
        previous_hash = GENESIS_HASH
        previous_type: str | None = None
        for sequence, row in enumerate(rows):
            event = json.loads(row["event_json"])
            if canonical_bytes(event).decode() != row["event_json"]:
                raise MissionError("mission journal event is not canonical")
            observed_hash = event["event_hash"]
            candidate = copy.deepcopy(event)
            candidate["event_hash"] = ID_PLACEHOLDER
            if (
                event["sequence"] != sequence
                or event["previous_hash"] != previous_hash
                or digest(event.get("payload")) != event.get("payload_sha256")
                or digest(candidate) != observed_hash
                or observed_hash != row["event_hash"]
            ):
                raise MissionError("mission journal hash or sequence mismatch")
            if event["event_type"] not in LEGAL_TRANSITIONS.get(previous_type, set()):
                raise MissionError("illegal mission journal transition")
            previous_hash = observed_hash
            previous_type = event["event_type"]
        if len(rows) != state["event_count"] or previous_hash != state["journal_head_sha256"]:
            raise MissionError("mission snapshot does not match journal head")
        return state

    def journal(self, mission_id: str) -> list[dict[str, Any]]:
        """Return a verified canonical journal export for sealed evidence."""

        self.verify(mission_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_json FROM mission_events WHERE mission_id=? ORDER BY sequence",
                (mission_id,),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("draft", type=Path)
    compile_parser.add_argument("--repository-root", type=Path, required=True)
    compile_parser.add_argument("--output", type=Path)
    admit_parser = subparsers.add_parser("admit")
    admit_parser.add_argument("mission", type=Path)
    admit_parser.add_argument("--repository-root", type=Path, required=True)
    admit_parser.add_argument("--at", required=True)
    for name in ("claim", "heartbeat"):
        action = subparsers.add_parser(name)
        action.add_argument("mission_id")
        action.add_argument("--worker-id", required=True)
        action.add_argument("--at", required=True)
    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("mission_id")
    checkpoint_parser.add_argument("checkpoint", type=Path)
    checkpoint_parser.add_argument("--worker-id", required=True)
    checkpoint_parser.add_argument("--at", required=True)
    defer_parser = subparsers.add_parser("defer")
    defer_parser.add_argument("mission_id")
    defer_parser.add_argument("checkpoint", type=Path)
    defer_parser.add_argument("--reason", required=True)
    defer_parser.add_argument("--worker-id", required=True)
    defer_parser.add_argument("--at", required=True)
    recover_parser = subparsers.add_parser("recover")
    recover_parser.add_argument("mission_id")
    recover_parser.add_argument("--stale-before", required=True)
    recover_parser.add_argument("--at", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("mission_id")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("mission_id")
    terminal_parser = subparsers.add_parser("terminalize")
    terminal_parser.add_argument("mission_id")
    terminal_parser.add_argument("result", type=Path)
    terminal_parser.add_argument("--evidence-root", type=Path, required=True)
    terminal_parser.add_argument("--worker-id", required=True)
    terminal_parser.add_argument("--at", required=True)
    args = parser.parse_args()
    try:
        if args.command == "compile":
            result = compile_mission(_read_json(args.draft), args.repository_root)
            rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
            if args.output:
                if args.output.exists():
                    raise MissionError("mission output already exists")
                args.output.write_text(rendered, encoding="utf-8", newline="\n")
            else:
                print(rendered, end="")
            return 0
        if args.queue_root is None:
            raise MissionError("--queue-root is required for queue operations")
        queue = MissionQueue(args.queue_root)
        if args.command == "admit":
            result = queue.admit(
                _read_json(args.mission), args.repository_root, at=args.at
            )
        elif args.command == "claim":
            result = queue.claim(args.mission_id, args.worker_id, at=args.at)
        elif args.command == "heartbeat":
            result = queue.heartbeat(args.mission_id, args.worker_id, at=args.at)
        elif args.command == "checkpoint":
            result = queue.checkpoint(
                args.mission_id,
                args.worker_id,
                _read_json(args.checkpoint),
                at=args.at,
            )
        elif args.command == "defer":
            result = queue.defer(
                args.mission_id,
                args.worker_id,
                _read_json(args.checkpoint),
                reason=args.reason,
                at=args.at,
            )
        elif args.command == "recover":
            result = queue.recover_stale(
                args.mission_id, stale_before=args.stale_before, at=args.at
            )
        elif args.command == "status":
            result = queue.status(args.mission_id)
        elif args.command == "verify":
            result = queue.verify(args.mission_id)
        else:
            result = queue.terminalize(
                args.mission_id,
                args.worker_id,
                _read_json(args.result),
                args.evidence_root,
                at=args.at,
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (MissionError, OSError, sqlite3.Error, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
