#!/usr/bin/env python3
"""Fail-closed Row108 cache, batch, transfer, lease, and cost controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_row108_audio_runtime_cache_cost_policy_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_runtime_control_receipt.schema.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-108_audio_runtime_cache_cost.json")
POLICY_REVISION = "wave64_row108_audio_runtime_cache_cost_policy_v0.1.0"
HASH_FIELDS = ("source_sha256", "model_sha256", "configuration_sha256", "implementation_sha256", "decoder_sha256")
DEPENDENCY_DELTAS = {
    "TRK-W64-069": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-077": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-077_SEMANTIC_AUDIO_EMBEDDING_CURRENT_DELTA_20260719.json"),
    "TRK-W64-099": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-099_NEURAL_TEXT_TO_AUDIO_CURRENT_DELTA_20260719.json"),
    "TRK-W64-101": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-101_VIDEO_CONDITIONED_FOLEY_CURRENT_DELTA_20260719.json"),
    "TRK-W64-105": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-105_AUDIO_END_TO_END_ORCHESTRATOR_CURRENT_DELTA_20260722.json"),
}


class AudioRuntimeControlError(ValueError):
    """Raised when a Row108 control would violate bounded authority."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def stable_hash(label: str) -> str:
    return hashlib.sha256(f"row108:{label}".encode()).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_cache_key(identity: dict[str, str]) -> str:
    if set(identity) != set(HASH_FIELDS):
        raise AudioRuntimeControlError("cache_identity_fields_mismatch")
    if any(len(identity[field]) != 64 or any(char not in "0123456789abcdef" for char in identity[field]) for field in HASH_FIELDS):
        raise AudioRuntimeControlError("cache_identity_hash_invalid")
    return hashlib.sha256(canonical_bytes(identity)).hexdigest()


def validate_lease(lease: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    if any("token" in key.lower() or "secret" in key.lower() for key in lease):
        raise AudioRuntimeControlError("lease_secret_material_forbidden")
    required = {"lease_id", "project", "profile", "expires_at", "valid", "lease_mode"}
    if set(lease) != required:
        raise AudioRuntimeControlError("lease_fields_mismatch")
    if lease["valid"] is not True or lease["project"] != "comfyui_main" or lease["lease_mode"] != "exclusive":
        raise AudioRuntimeControlError("lease_authority_invalid")
    if lease["profile"] != "comfyui_model_qualification":
        raise AudioRuntimeControlError("lease_profile_invalid")
    current = now or datetime.now(timezone.utc)
    expiry = datetime.fromisoformat(str(lease["expires_at"]).replace("Z", "+00:00"))
    if expiry <= current:
        raise AudioRuntimeControlError("lease_expired")
    return {"required": True, "validated": True, "lease_id": lease["lease_id"], "project": lease["project"], "profile": lease["profile"], "expires_at": lease["expires_at"]}


def plan_batch(items: list[dict[str, Any]], *, maximum_usd: float, policy: dict[str, Any]) -> dict[str, Any]:
    limits = policy["batch_limits"]
    if not items or len(items) > limits["maximum_items"]:
        raise AudioRuntimeControlError("batch_item_count_invalid")
    ids = [item["item_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise AudioRuntimeControlError("duplicate_batch_item")
    peak = max(float(item["estimated_peak_vram_gib"]) for item in items)
    estimate = sum(float(item["estimated_cost_usd"]) for item in items)
    if peak > limits["maximum_estimated_peak_vram_gib"]:
        raise AudioRuntimeControlError("batch_peak_vram_exceeded")
    if estimate > maximum_usd:
        raise AudioRuntimeControlError("estimated_cost_budget_exceeded")
    normalized = []
    for item in items:
        normalized.append({**item, "state": "pending", "attempts": 0, "output_sha256": None})
    digest = stable_hash(json.dumps(normalized, sort_keys=True))[:24]
    return {"batch_id": f"audio-batch-{digest}", "items": normalized, "estimated_peak_vram_gib": peak, "budget": {"currency": "USD", "maximum_usd": maximum_usd, "estimated_usd": estimate, "actual_usd": None}}


def resume_batch(batch: dict[str, Any], retained: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = deepcopy(batch)
    for item in result["items"]:
        prior = retained.get(item["item_id"])
        if not prior:
            continue
        if prior.get("input_sha256") != item["input_sha256"]:
            raise AudioRuntimeControlError("retained_item_identity_changed")
        if prior.get("state") in {"passed", "reused"}:
            if not prior.get("output_sha256"):
                raise AudioRuntimeControlError("retained_output_hash_absent")
            item.update({"state": "reused", "attempts": int(prior.get("attempts", 0)), "output_sha256": prior["output_sha256"]})
    return result


def validate_transfer_manifest(entries: list[dict[str, Any]]) -> None:
    destinations = set()
    for entry in entries:
        if len(entry.get("source_sha256", "")) != 64 or entry.get("bytes", -1) < 0 or not entry.get("destination"):
            raise AudioRuntimeControlError("transfer_manifest_entry_invalid")
        if entry["destination"] in destinations:
            raise AudioRuntimeControlError("duplicate_transfer_destination")
        destinations.add(entry["destination"])


def build_receipt(root: Path, *, synthetic: bool, lease: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = load_json(root / POLICY_PATH)
    identity = {field: stable_hash(field) for field in HASH_FIELDS}
    cache_key = compute_cache_key(identity)
    items = [
        {"item_id": "feature-001", "input_sha256": stable_hash("input-1"), "estimated_peak_vram_gib": 4.0, "estimated_cost_usd": 0.02},
        {"item_id": "feature-002", "input_sha256": stable_hash("input-2"), "estimated_peak_vram_gib": 4.0, "estimated_cost_usd": 0.02},
    ]
    batch = plan_batch(items, maximum_usd=0.10, policy=policy)
    retained = {"feature-001": {**batch["items"][0], "state": "passed", "attempts": 1, "output_sha256": stable_hash("output-1")}}
    batch = resume_batch(batch, retained)
    transfer = [{"source_sha256": stable_hash("transfer-1"), "bytes": 1024, "destination": "/workspace/audio/transfer-1", "verified": synthetic}]
    validate_transfer_manifest(transfer)
    lease_record = {"required": True, "validated": False, "lease_id": None, "project": None, "profile": None, "expires_at": None}
    blockers = []
    if lease is not None:
        lease_record = validate_lease(lease)
    elif not synthetic:
        blockers.append("EXACT_COORDINATOR_LEASE_ABSENT")
    if not synthetic:
        blockers.extend(["TTL_WATCHDOG_RECEIPT_ABSENT", "FINAL_LEASE_RELEASE_RECEIPT_ABSENT"])
    receipt = {
        "schema_version": "1.0.0", "tracker_id": "TRK-W64-108", "item_id": "ITEM-W64-108",
        "record_type": "audio_runtime_control_receipt", "policy_revision": POLICY_REVISION,
        "batch_id": batch["batch_id"], "provider": "runpod", "pod_id": "1q4ji0gg1fkhvt",
        "is_synthetic": synthetic,
        "cache_entries": [{"cache_key": cache_key, "identity": identity, "output_sha256": stable_hash("cached-output"), "state": "hit"}],
        "items": batch["items"], "transfer_manifest": transfer, "budget": batch["budget"],
        "lease": lease_record, "ttl": {"deadline": None, "watchdog_armed": False, "final_release_verified": False},
        "decision": {"status": "ready" if synthetic else "blocked", "runtime_allowed": False,
                     "runtime_completion": False, "row108_acceptance": "fixture_only" if synthetic else "held", "blocker_codes": blockers},
    }
    receipt["receipt_sha256"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    validate_receipt(root, receipt)
    return receipt


def validate_receipt(root: Path, receipt: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(receipt)
    candidate = deepcopy(receipt)
    observed = candidate.pop("receipt_sha256")
    if observed != hashlib.sha256(canonical_bytes(candidate)).hexdigest():
        raise AudioRuntimeControlError("receipt_sha256_mismatch")
    if receipt["decision"]["runtime_allowed"] and not receipt["lease"]["validated"]:
        raise AudioRuntimeControlError("runtime_without_lease_forbidden")
    if receipt["decision"]["runtime_completion"]:
        if receipt["budget"]["actual_usd"] is None or not receipt["ttl"]["watchdog_armed"] or not receipt["ttl"]["final_release_verified"]:
            raise AudioRuntimeControlError("runtime_completion_proof_incomplete")
    for entry in receipt["cache_entries"]:
        if entry["cache_key"] != compute_cache_key(entry["identity"]):
            raise AudioRuntimeControlError("cache_key_recompute_mismatch")


def dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for tracker, relative in DEPENDENCY_DELTAS.items():
        path = root / relative
        payload = load_json(path) if path.is_file() else {}
        complete = payload.get("row_complete") is True
        status = str(payload.get("status", "ABSENT"))
        result[tracker] = {"path": relative.as_posix(), "sha256": sha256_file(path) if path.is_file() else "0" * 64,
                           "row_complete": complete, "dependency_satisfied": complete and not status.lower().startswith("hold"), "status": status}
    return result


def build_evidence(root: Path) -> dict[str, Any]:
    fixture = build_receipt(root, synthetic=True)
    live = build_receipt(root, synthetic=False)
    admissions = dependency_admissions(root)
    blockers = list(live["decision"]["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blockers.insert(0, "ROW108_DEPENDENCIES_NOT_ACCEPTED")
    return {
        "schema_version": "1.0.0", "evidence_id": "TRK-W64-108_audio_runtime_cache_cost",
        "tracker_id": "TRK-W64-108", "item_id": "ITEM-W64-108",
        "status": "HOLD_DEPENDENCIES_AND_LIVE_LEASE_TTL_RUNTIME_ABSENT_WITH_FAIL_CLOSED_CONTROL_SLICE_PRESENT",
        "row_complete": False, "implementation_completion_claimed": True, "runtime_completion_claimed": False,
        "sole_current_runtime": {"provider": "runpod", "pod_id": "1q4ji0gg1fkhvt"},
        "dependency_admissions": admissions, "fixture_proof": fixture, "live_hold_receipt": live,
        "implementation": {"script": str(Path(__file__).resolve().relative_to(root)).replace("\\", "/"), "script_sha256": sha256_file(Path(__file__).resolve()),
                           "schema": SCHEMA_PATH.as_posix(), "schema_sha256": sha256_file(root / SCHEMA_PATH),
                           "policy": POLICY_PATH.as_posix(), "policy_sha256": sha256_file(root / POLICY_PATH)},
        "decision": {"status": "blocked", "row108_acceptance": "held", "product_completion": False, "blocker_codes": blockers},
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
