#!/usr/bin/env python3
"""Bounded, pod-local dispatcher for one sealed deferred visual-review job.

The dispatcher is deliberately narrow.  It watches only its immutable review
contract on the selected Pod, never coordinates across pods, never changes the
ComfyUI queue, and never submits to Serverless.  A fresh direct admission is
required before it invokes the sealed bridge exactly once.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


ZERO_HASH = "0" * 64
GENESIS_HASH = hashlib.sha256(b"W64-DEFERRED-VISUAL-DISPATCH-GENESIS-V1").hexdigest()
DISPATCH_SCHEMA = "w64.deferred_visual_review_dispatch_receipt.v1"
JOB_ID = re.compile(r"^[a-f0-9]{64}$")


class DispatcherError(RuntimeError):
    """Raised when the immutable dispatch or its durable state is unsafe."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise DispatcherError(f"immutable output already exists: {path}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def seal(value: dict[str, Any], field: str = "receipt_sha256") -> dict[str, Any]:
    result = dict(value)
    result[field] = ZERO_HASH
    result[field] = digest(result)
    return result


def _load_bridge(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("w64_deferred_visual_review_bridge", path)
    if spec is None or spec.loader is None:
        raise DispatcherError(f"cannot load bridge: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _input_manifest(paths: dict[str, Path]) -> dict[str, dict[str, str]]:
    return {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in sorted(paths.items())
    }


def _job_id(inputs: dict[str, dict[str, str]]) -> str:
    return digest(inputs)


def _dispatch_contract(job_id: str, inputs: dict[str, dict[str, str]]) -> dict[str, Any]:
    return seal(
        {
            "schema_version": "w64.deferred_visual_review_dispatch_contract.v1",
            "contract_sha256": ZERO_HASH,
            "job_id": job_id,
            "inputs": inputs,
        },
        field="contract_sha256",
    )


def _verify_seal(value: dict[str, Any], field: str) -> None:
    observed = value.get(field)
    candidate = dict(value)
    candidate[field] = ZERO_HASH
    if not isinstance(observed, str) or digest(candidate) != observed:
        raise DispatcherError(f"invalid sealed value: {field}")


def _load_journal(path: Path, job_id: str) -> tuple[int, str, list[dict[str, Any]]]:
    previous_hash = GENESIS_HASH
    events: list[dict[str, Any]] = []
    for sequence, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DispatcherError("dispatch journal is invalid JSON") from exc
        candidate = dict(event)
        observed_hash = candidate.get("event_hash")
        candidate["event_hash"] = ZERO_HASH
        if (
            event.get("job_id") != job_id
            or event.get("sequence") != sequence
            or event.get("previous_hash") != previous_hash
            or digest(event.get("payload")) != event.get("payload_sha256")
            or not isinstance(observed_hash, str)
            or digest(candidate) != observed_hash
        ):
            raise DispatcherError("dispatch journal hash or sequence mismatch")
        previous_hash = observed_hash
        events.append(event)
    if not events:
        raise DispatcherError("dispatch journal is unexpectedly empty")
    return len(events), previous_hash, events


def _append_event(
    path: Path,
    *,
    job_id: str,
    sequence: int,
    previous_hash: str,
    event_type: str,
    payload: dict[str, Any],
    at: str,
) -> tuple[int, str]:
    event = {
        "schema_version": "w64.deferred_visual_review_dispatch_event.v1",
        "job_id": job_id,
        "sequence": sequence,
        "at": at,
        "event_type": event_type,
        "payload": payload,
        "payload_sha256": digest(payload),
        "previous_hash": previous_hash,
        "event_hash": ZERO_HASH,
    }
    event["event_hash"] = digest(event)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return sequence + 1, event["event_hash"]


def _acquire_lock(path: Path, job_id: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"job_id": job_id, "pid": os.getpid(), "at": utc_now()}))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise DispatcherError("dispatch lock already exists; refusing duplicate worker") from exc


def _dispatch_receipt(
    *,
    job_id: str,
    inputs: dict[str, dict[str, str]],
    event_count: int,
    event_head: str,
    state: str,
    output_path: Path,
    bridge_receipt: dict[str, Any] | None = None,
    failure: str | None = None,
) -> dict[str, Any]:
    receipt = {
        "schema_version": DISPATCH_SCHEMA,
        "receipt_sha256": ZERO_HASH,
        "job_id": job_id,
        "state": state,
        "authority": "NONPROMOTING_UNQUALIFIED_REVIEW_ONLY",
        "serverless_submitted": False,
        "inputs": inputs,
        "event_count": event_count,
        "event_head_sha256": event_head,
        "bridge_receipt": bridge_receipt,
        "failure": failure,
    }
    sealed = seal(receipt)
    write_json_new(output_path, sealed)
    return sealed


def run_dispatcher(
    *,
    bridge_path: Path,
    deferred_path: Path,
    execution_path: Path,
    binding_contract_path: Path,
    binding_seal_path: Path,
    model_manifest_path: Path,
    dispatch_root: Path,
    max_wait_seconds: int,
    poll_interval_seconds: int,
    probe: Callable[[], dict[str, Any]] | None = None,
    reviewer: Callable[[str, Path, list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Wait only within a bounded local budget, then invoke the bridge once."""

    if max_wait_seconds < 0 or poll_interval_seconds < 1:
        raise DispatcherError("invalid bounded dispatch timing")
    paths = {
        "bridge": bridge_path.resolve(),
        "deferred_job": deferred_path.resolve(),
        "execution_contract": execution_path.resolve(),
        "binding_contract": binding_contract_path.resolve(),
        "binding_seal": binding_seal_path.resolve(),
        "model_manifest": model_manifest_path.resolve(),
    }
    if any(not path.is_file() for path in paths.values()):
        raise DispatcherError("immutable dispatch input is missing")
    inputs = _input_manifest(paths)
    job_id = _job_id(inputs)
    if JOB_ID.fullmatch(job_id) is None:
        raise DispatcherError("derived dispatch job ID is invalid")
    root = dispatch_root.resolve()
    job_root = (root / job_id).resolve()
    try:
        job_root.relative_to(root)
    except ValueError as exc:
        raise DispatcherError("dispatch job root escapes configured root") from exc
    final_output = job_root / "dispatch_receipt.json"
    if final_output.exists():
        raise DispatcherError("terminal dispatch receipt already exists")
    job_root.mkdir(parents=True, exist_ok=True)
    contract_path = job_root / "dispatch_contract.json"
    contract = _dispatch_contract(job_id, inputs)
    if contract_path.exists():
        try:
            existing_contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DispatcherError("dispatch contract is invalid JSON") from exc
        _verify_seal(existing_contract, "contract_sha256")
        if existing_contract != contract:
            raise DispatcherError("dispatch contract does not match immutable inputs")
    else:
        write_json_new(contract_path, contract)
    lock_path = job_root / "active.lock"
    event_path = job_root / "events.jsonl"
    if event_path.exists():
        sequence, event_head, prior_events = _load_journal(event_path, job_id)
    else:
        sequence, event_head, prior_events = 0, GENESIS_HASH, []
    _acquire_lock(lock_path, job_id)
    started = clock()
    last_snapshot_sha: str | None = None
    try:
        bridge = _load_bridge(paths["bridge"])
        bridge_probe = probe or bridge.local_probe
        bridge_reviewer = reviewer or bridge.default_reviewer
        validated = bridge.validate_contracts(
            paths["deferred_job"],
            paths["execution_contract"],
            paths["binding_contract"],
            paths["binding_seal"],
            paths["model_manifest"],
        )
        execution = validated["execution"]
        if prior_events:
            sequence, event_head = _append_event(
                event_path,
                job_id=job_id,
                sequence=sequence,
                previous_hash=event_head,
                event_type="DISPATCH_RESUMED",
                payload={"previous_event_type": prior_events[-1]["event_type"]},
                at=utc_now(),
            )
            if any(event["event_type"] == "DIRECT_ADMISSION_GRANTED" for event in prior_events):
                bridge_output = job_root / "bridge_execution_receipt.json"
                if bridge_output.is_file():
                    bridge_receipt = json.loads(bridge_output.read_text(encoding="utf-8"))
                    _verify_seal(bridge_receipt, "receipt_sha256")
                    sequence, event_head = _append_event(
                        event_path,
                        job_id=job_id,
                        sequence=sequence,
                        previous_hash=event_head,
                        event_type="RECOVERED_BRIDGE_RECEIPT",
                        payload={
                            "state": bridge_receipt["state"],
                            "receipt_sha256": bridge_receipt["receipt_sha256"],
                        },
                        at=utc_now(),
                    )
                    return _dispatch_receipt(
                        job_id=job_id,
                        inputs=inputs,
                        event_count=sequence,
                        event_head=event_head,
                        state=bridge_receipt["state"],
                        output_path=final_output,
                        bridge_receipt={
                            "path": str(bridge_output),
                            "receipt_sha256": bridge_receipt["receipt_sha256"],
                            "gpu_model_load_attempted": bridge_receipt["gpu_model_load_attempted"],
                            "gpu_models_loaded": bridge_receipt["gpu_models_loaded"],
                        },
                    )
                sequence, event_head = _append_event(
                    event_path,
                    job_id=job_id,
                    sequence=sequence,
                    previous_hash=event_head,
                    event_type="DISPATCH_CRASH_UNCERTAIN_AFTER_ADMISSION",
                    payload={"retry_permitted": False},
                    at=utc_now(),
                )
                return _dispatch_receipt(
                    job_id=job_id,
                    inputs=inputs,
                    event_count=sequence,
                    event_head=event_head,
                    state="FAILED_DISPATCH_CRASH_AFTER_ADMISSION",
                    output_path=final_output,
                    failure="CRASH_AFTER_DIRECT_ADMISSION",
                )
        else:
            sequence, event_head = _append_event(
                event_path,
                job_id=job_id,
                sequence=sequence,
                previous_hash=event_head,
                event_type="DISPATCH_ADMITTED",
                payload={
                    "max_wait_seconds": max_wait_seconds,
                    "poll_interval_seconds": poll_interval_seconds,
                },
                at=utc_now(),
            )
        while True:
            snapshot = bridge_probe()
            reasons = bridge.admission(snapshot, execution)
            snapshot_sha = digest({"snapshot": snapshot, "reasons": reasons})
            if not reasons:
                sequence, event_head = _append_event(
                    event_path,
                    job_id=job_id,
                    sequence=sequence,
                    previous_hash=event_head,
                    event_type="DIRECT_ADMISSION_GRANTED",
                    payload={"snapshot": snapshot},
                    at=utc_now(),
                )
                bridge_output = job_root / "bridge_execution_receipt.json"
                bridge_receipt = bridge.run_bridge(
                    deferred_path=paths["deferred_job"],
                    execution_path=paths["execution_contract"],
                    binding_contract_path=paths["binding_contract"],
                    binding_seal_path=paths["binding_seal"],
                    model_manifest_path=paths["model_manifest"],
                    output_path=bridge_output,
                    execute=True,
                    probe=bridge_probe,
                    reviewer=bridge_reviewer,
                )
                sequence, event_head = _append_event(
                    event_path,
                    job_id=job_id,
                    sequence=sequence,
                    previous_hash=event_head,
                    event_type="BRIDGE_RETURNED",
                    payload={
                        "state": bridge_receipt["state"],
                        "receipt_sha256": bridge_receipt["receipt_sha256"],
                    },
                    at=utc_now(),
                )
                return _dispatch_receipt(
                    job_id=job_id,
                    inputs=inputs,
                    event_count=sequence,
                    event_head=event_head,
                    state=bridge_receipt["state"],
                    output_path=final_output,
                    bridge_receipt={
                        "path": str(bridge_output),
                        "receipt_sha256": bridge_receipt["receipt_sha256"],
                        "gpu_model_load_attempted": bridge_receipt["gpu_model_load_attempted"],
                        "gpu_models_loaded": bridge_receipt["gpu_models_loaded"],
                    },
                )
            if snapshot_sha != last_snapshot_sha:
                sequence, event_head = _append_event(
                    event_path,
                    job_id=job_id,
                    sequence=sequence,
                    previous_hash=event_head,
                    event_type="WAITING_FOR_DIRECT_ADMISSION",
                    payload={"snapshot": snapshot, "reasons": reasons},
                    at=utc_now(),
                )
                last_snapshot_sha = snapshot_sha
            remaining = max_wait_seconds - (clock() - started)
            if remaining <= 0:
                sequence, event_head = _append_event(
                    event_path,
                    job_id=job_id,
                    sequence=sequence,
                    previous_hash=event_head,
                    event_type="DISPATCH_DEFERRED_TIMEOUT",
                    payload={"last_reasons": reasons, "last_snapshot": snapshot},
                    at=utc_now(),
                )
                return _dispatch_receipt(
                    job_id=job_id,
                    inputs=inputs,
                    event_count=sequence,
                    event_head=event_head,
                    state="DEFERRED_WAITING_FOR_EXCLUSIVE_LOCAL_A6000",
                    output_path=final_output,
                )
            sleeper(min(float(poll_interval_seconds), remaining))
    except Exception as exc:
        sequence, event_head = _append_event(
            event_path,
            job_id=job_id,
            sequence=sequence,
            previous_hash=event_head,
            event_type="DISPATCH_FAILED",
            payload={"failure_type": type(exc).__name__},
            at=utc_now(),
        )
        return _dispatch_receipt(
            job_id=job_id,
            inputs=inputs,
            event_count=sequence,
            event_head=event_head,
            state="FAILED_UNQUALIFIED_REVIEW_DISPATCH",
            output_path=final_output,
            failure=type(exc).__name__,
        )
    finally:
        if lock_path.exists():
            lock_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--deferred-job", type=Path, required=True)
    parser.add_argument("--execution-contract", type=Path, required=True)
    parser.add_argument("--binding-contract", type=Path, required=True)
    parser.add_argument("--binding-seal", type=Path, required=True)
    parser.add_argument("--model-tree-manifest", type=Path, required=True)
    parser.add_argument("--dispatch-root", type=Path, required=True)
    parser.add_argument("--max-wait-seconds", type=int, default=7200)
    parser.add_argument("--poll-interval-seconds", type=int, default=30)
    args = parser.parse_args()
    try:
        receipt = run_dispatcher(
            bridge_path=args.bridge,
            deferred_path=args.deferred_job,
            execution_path=args.execution_contract,
            binding_contract_path=args.binding_contract,
            binding_seal_path=args.binding_seal,
            model_manifest_path=args.model_tree_manifest,
            dispatch_root=args.dispatch_root,
            max_wait_seconds=args.max_wait_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
    except DispatcherError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps({"status": receipt["state"], "receipt_sha256": receipt["receipt_sha256"]}, sort_keys=True))
    return 1 if receipt["state"].startswith("FAILED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
