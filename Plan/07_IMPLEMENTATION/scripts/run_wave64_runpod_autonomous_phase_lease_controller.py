#!/usr/bin/env python3
"""Fail-closed, hash-chained W64-AQA phase lease and cost governor."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_phase_lease.schema.json"
ZERO_HASH = "0" * 64


class LeaseError(RuntimeError):
    """Raised when a lease operation fails closed."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PhaseLeaseController:
    """Persist one exclusive GPU phase lease with deterministic admission gates."""

    def __init__(
        self,
        state_path: Path,
        controller_id: str = "W64-AQA-CTRL-primary",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.state_path = state_path
        self.controller_id = controller_id
        self.clock = clock
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        if not state_path.exists():
            self._state = {
                "schema_version": "wave64.aqa.phase_lease.v1",
                "controller_id": controller_id,
                "revision": 0,
                "state": "IDLE",
                "lease": None,
                "blocked_reasons": [],
                "journal": [],
            }
            self._append("CONTROLLER_INITIALIZED", {"controller_id": controller_id})
            self._persist()
        else:
            self._state = json.loads(state_path.read_text(encoding="utf-8"))
            self.verify()
            if self._state["controller_id"] != controller_id:
                raise LeaseError("controller identity mismatch")

    @property
    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def _append(self, event: str, details: dict[str, Any]) -> None:
        journal = self._state["journal"]
        entry = {
            "sequence": len(journal),
            "timestamp": iso(self.clock()),
            "event": event,
            "details": details,
            "previous_hash": journal[-1]["event_hash"] if journal else ZERO_HASH,
        }
        entry["event_hash"] = hashlib.sha256(canonical_bytes(entry)).hexdigest()
        journal.append(entry)
        self._state["revision"] += 1

    def _persist(self) -> None:
        jsonschema.Draft7Validator(
            self.schema, format_checker=jsonschema.FormatChecker()
        ).validate(self._state)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        payload = json.dumps(self._state, indent=2, sort_keys=True) + "\n"
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.state_path)

    def verify(self) -> None:
        jsonschema.Draft7Validator(
            self.schema, format_checker=jsonschema.FormatChecker()
        ).validate(self._state)
        previous = ZERO_HASH
        for sequence, observed in enumerate(self._state["journal"]):
            entry = copy.deepcopy(observed)
            event_hash = entry.pop("event_hash")
            if entry["sequence"] != sequence or entry["previous_hash"] != previous:
                raise LeaseError("journal sequence or previous hash mismatch")
            expected = hashlib.sha256(canonical_bytes(entry)).hexdigest()
            if event_hash != expected:
                raise LeaseError("journal event hash mismatch")
            previous = event_hash

    @staticmethod
    def _admission_reasons(snapshot: dict[str, Any], max_cost_usd: float) -> list[str]:
        required = {
            "foreign_jobs",
            "queue_running",
            "queue_pending",
            "vram_free_mib",
            "required_free_vram_mib",
            "overlay_used_percent",
            "cost_per_hour_usd",
            "estimated_phase_seconds",
        }
        if not required.issubset(snapshot):
            return ["INVALID_RESOURCE_SNAPSHOT"]
        reasons: list[str] = []
        if snapshot["foreign_jobs"]:
            reasons.append("FOREIGN_JOB_PRESENT")
        if snapshot["queue_running"] or snapshot["queue_pending"]:
            reasons.append("QUEUE_NOT_IDLE")
        if snapshot["vram_free_mib"] < snapshot["required_free_vram_mib"]:
            reasons.append("INSUFFICIENT_FREE_VRAM")
        if snapshot["overlay_used_percent"] >= 85:
            reasons.append("OVERLAY_PRESSURE")
        values = (
            snapshot["cost_per_hour_usd"],
            snapshot["estimated_phase_seconds"],
            max_cost_usd,
        )
        if any(not isinstance(value, (int, float)) or value < 0 for value in values):
            reasons.append("INVALID_RESOURCE_SNAPSHOT")
        else:
            estimate = snapshot["cost_per_hour_usd"] * snapshot["estimated_phase_seconds"] / 3600
            if estimate > max_cost_usd:
                reasons.append("COST_BUDGET_EXCEEDED")
        return sorted(set(reasons))

    def _block(self, reasons: list[str], details: dict[str, Any]) -> None:
        self._state["state"] = "BLOCKED"
        self._state["blocked_reasons"] = sorted(set(reasons))
        self._append("LEASE_BLOCKED", {**details, "reasons": self._state["blocked_reasons"]})
        self._persist()

    def acquire(
        self,
        *,
        phase: str,
        owner: str,
        contract_id: str,
        snapshot: dict[str, Any],
        max_cost_usd: float,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        if self._state["state"] != "IDLE" or self._state["lease"] is not None:
            raise LeaseError("ACTIVE_LEASE_CONFLICT")
        if ttl_seconds < 30 or ttl_seconds > 86400:
            raise LeaseError("ttl_seconds must be between 30 and 86400")
        reasons = self._admission_reasons(snapshot, max_cost_usd)
        snapshot_hash = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()
        if reasons:
            self._block(reasons, {"phase": phase, "resource_snapshot_sha256": snapshot_hash})
            raise LeaseError(";".join(reasons))
        now = self.clock()
        estimate = snapshot["cost_per_hour_usd"] * snapshot["estimated_phase_seconds"] / 3600
        lease = {
            "lease_id": f"W64-AQA-LEASE-{uuid.uuid4().hex[:24]}",
            "phase": phase,
            "owner": owner,
            "contract_id": contract_id,
            "acquired_at": iso(now),
            "heartbeat_at": iso(now),
            "expires_at": iso(now + timedelta(seconds=ttl_seconds)),
            "max_cost_usd": max_cost_usd,
            "estimated_cost_usd": estimate,
            "resource_snapshot_sha256": snapshot_hash,
        }
        self._state["lease"] = lease
        self._state["state"] = "ACTIVE"
        self._state["blocked_reasons"] = []
        self._append("LEASE_ACQUIRED", {"lease_id": lease["lease_id"], "phase": phase})
        self._persist()
        return copy.deepcopy(lease)

    def heartbeat(self, lease_id: str) -> None:
        lease = self._require_active(lease_id)
        now = self.clock()
        if now >= parse_time(lease["expires_at"]):
            self._block(["LEASE_EXPIRED"], {"lease_id": lease_id})
            raise LeaseError("LEASE_EXPIRED")
        lease["heartbeat_at"] = iso(now)
        self._append("LEASE_HEARTBEAT", {"lease_id": lease_id})
        self._persist()

    def _require_active(self, lease_id: str) -> dict[str, Any]:
        lease = self._state.get("lease")
        if not lease or lease["lease_id"] != lease_id or self._state["state"] != "ACTIVE":
            raise LeaseError("active lease identity mismatch")
        return lease

    def complete(self, lease_id: str, *, actual_cost_usd: float, queue_idle: bool) -> None:
        lease = self._require_active(lease_id)
        self._state["state"] = "DRAINING"
        self._append("LEASE_DRAINING", {"lease_id": lease_id})
        if not queue_idle:
            self._block(["QUEUE_NOT_IDLE"], {"lease_id": lease_id})
            raise LeaseError("QUEUE_NOT_IDLE")
        if actual_cost_usd > lease["max_cost_usd"]:
            self._block(["COST_BUDGET_EXCEEDED"], {"lease_id": lease_id})
            raise LeaseError("COST_BUDGET_EXCEEDED")
        self._state["lease"] = None
        self._state["state"] = "IDLE"
        self._state["blocked_reasons"] = []
        self._append(
            "LEASE_RELEASED", {"lease_id": lease_id, "actual_cost_usd": actual_cost_usd}
        )
        self._persist()

    def fail(self, lease_id: str, reason: str) -> None:
        self._require_active(lease_id)
        if reason not in {"OOM", "PROCESS_CRASH", "PRICE_DRIFT", "STORAGE_UNAVAILABLE"}:
            raise LeaseError("unsupported runtime failure reason")
        self._block([reason], {"lease_id": lease_id})

    def reconcile_expired(self, *, queue_idle: bool, owned_process_absent: bool) -> None:
        lease = self._state.get("lease")
        if not lease or self._state["state"] not in {"ACTIVE", "BLOCKED"}:
            raise LeaseError("no lease available for recovery")
        if self.clock() < parse_time(lease["expires_at"]) and self._state["state"] == "ACTIVE":
            raise LeaseError("lease is not expired")
        self._state["state"] = "RECOVERING"
        self._append("RECOVERY_STARTED", {"lease_id": lease["lease_id"]})
        if not queue_idle or not owned_process_absent:
            reasons = []
            if not queue_idle:
                reasons.append("QUEUE_NOT_IDLE")
            if not owned_process_absent:
                reasons.append("OWNERSHIP_UNPROVEN")
            self._block(reasons, {"lease_id": lease["lease_id"]})
            raise LeaseError(";".join(reasons))
        lease_id = lease["lease_id"]
        self._state["lease"] = None
        self._state["state"] = "IDLE"
        self._state["blocked_reasons"] = []
        self._append("RECOVERY_RELEASED", {"lease_id": lease_id})
        self._persist()

    def clear_admission_block(self) -> None:
        if self._state["state"] != "BLOCKED" or self._state["lease"] is not None:
            raise LeaseError("only admission blocks without a lease can be cleared")
        previous = self._state["blocked_reasons"]
        self._state["state"] = "IDLE"
        self._state["blocked_reasons"] = []
        self._append("BLOCK_CLEARED", {"previous_reasons": previous})
        self._persist()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        controller = PhaseLeaseController(args.state)
        if args.verify:
            controller.verify()
        print(json.dumps(controller.state, indent=2, sort_keys=True))
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, LeaseError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
