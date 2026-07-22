#!/usr/bin/env python3
"""Run one lease-bound LatentSync UNet load/unload canary without inference."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
from typing import Any


class CanaryError(RuntimeError):
    """Raised when the model-load-only boundary cannot be proven."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpu_snapshot() -> dict[str, Any]:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    rows = [row.strip() for row in completed.stdout.splitlines() if row.strip()]
    if len(rows) != 1:
        raise CanaryError("exactly one GPU is required")
    name, total, used, free, utilization = [part.strip() for part in rows[0].split(",")]
    return {"name": name, "total_mib": int(total), "used_mib": int(used), "free_mib": int(free), "utilization_percent": int(utilization)}


def host_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise CanaryError("MemAvailable is absent")


def validate_runtime_capacity(
    gpu: dict[str, Any], host_bytes: int, admission: dict[str, Any]
) -> dict[str, int]:
    lease = admission["lease"]
    required_vram = int(lease["required_free_vram_mib"])
    required_host = int(lease["minimum_host_available_bytes"])
    if int(gpu["free_mib"]) < required_vram:
        raise CanaryError("free VRAM is below the admitted minimum")
    if host_bytes < required_host:
        raise CanaryError("available host memory is below the admitted minimum")
    return {
        "required_free_vram_mib": required_vram,
        "minimum_host_available_bytes": required_host,
    }


def validate_lease(receipt: dict[str, Any], admission: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    lease = admission["lease"]
    if "lease_token" in receipt or "token" in receipt:
        raise CanaryError("lease receipt must not contain a token")
    if receipt.get("valid") is not True:
        raise CanaryError("coordinator receipt is not valid")
    for field in ("project", "profile", "lease_mode"):
        expected = lease["mode"] if field == "lease_mode" else lease[field]
        if receipt.get(field) != expected:
            raise CanaryError(f"coordinator receipt {field} mismatch")
    if float(receipt.get("reserved_peak_gib", 0)) < float(lease["minimum_reserved_peak_gib"]):
        raise CanaryError("coordinator reservation is too small")
    current = now or datetime.now(timezone.utc)
    expiry = datetime.fromisoformat(str(receipt.get("expires_at", "")).replace("Z", "+00:00"))
    if expiry <= current:
        raise CanaryError("coordinator receipt is expired")
    return {name: receipt[name] for name in ("valid", "lease_id", "project", "profile", "lease_mode", "reserved_peak_gib", "safety_reserve_gib", "expires_at")}


def validate_inputs(admission: dict[str, Any]) -> dict[str, Any]:
    environment = admission["environment"]
    code = admission["code"]
    model = admission["model"]
    if Path(sys.prefix).as_posix() != environment["root"]:
        raise CanaryError("canary is not running in the admitted environment")
    checks = [
        (Path(environment["receipt_path"]), environment["receipt_sha256"], None),
        (Path(environment["import_receipt_path"]), environment["import_receipt_sha256"], None),
        (Path(code["root"]) / code["config_path"], code["config_sha256"], None),
        (Path(code["root"]) / code["unet_source_path"], code["unet_source_sha256"], None),
        (Path(model["root"]) / model["checkpoint_path"], model["checkpoint_sha256"], model["checkpoint_bytes"]),
    ]
    verified = []
    for path, expected_hash, expected_size in checks:
        if not path.is_file() or path.is_symlink():
            raise CanaryError(f"missing or unsafe admitted input: {path}")
        if expected_size is not None and path.stat().st_size != expected_size:
            raise CanaryError(f"admitted input size mismatch: {path}")
        observed = sha256(path)
        if observed != expected_hash:
            raise CanaryError(f"admitted input hash mismatch: {path}")
        verified.append({"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": observed})
    code_root = Path(code["root"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=code_root, check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=code_root, check=True, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=code_root, check=True, capture_output=True, text=True).stdout
    if head != code["commit"] or tree != code["tree"] or dirty:
        raise CanaryError("LatentSync checkout identity or cleanliness mismatch")
    return {"verified_inputs": verified, "code_commit": head, "code_tree": tree}


def run_inner(admission: dict[str, Any], lease: dict[str, Any]) -> tuple[dict[str, Any], int]:
    identity = validate_inputs(admission)
    validate_lease(lease, admission)
    before = gpu_snapshot()
    host_before = host_available_bytes()
    capacity_gate = validate_runtime_capacity(before, host_before, admission)
    model = None
    loaded = None
    error = None
    details: dict[str, Any] = {}
    started = time.monotonic()
    try:
        import torch
        from omegaconf import OmegaConf
        from latentsync.models.unet import UNet3DConditionModel

        config = OmegaConf.load(str(Path(admission["code"]["root"]) / admission["code"]["config_path"]))
        model, global_step = UNet3DConditionModel.from_pretrained(
            OmegaConf.to_container(config.model),
            str(Path(admission["model"]["root"]) / admission["model"]["checkpoint_path"]),
            device="cpu",
        )
        cpu_load_seconds = time.monotonic() - started
        parameter_count = sum(parameter.numel() for parameter in model.parameters())
        model = model.to(device="cuda:0", dtype=torch.float16)
        torch.cuda.synchronize()
        loaded = gpu_snapshot()
        first_name, first_parameter = next(iter(model.named_parameters()))
        sample = first_parameter.detach().reshape(-1)[:32].float().cpu().numpy().tobytes()
        details = {
            "config_resolution": int(config.data.resolution),
            "global_step": int(global_step),
            "parameter_count": parameter_count,
            "parameter_devices": sorted({str(parameter.device) for parameter in model.parameters()}),
            "parameter_dtypes": sorted({str(parameter.dtype) for parameter in model.parameters()}),
            "first_parameter_name": first_name,
            "first_parameter_sample_sha256": hashlib.sha256(sample).hexdigest(),
            "cpu_load_seconds": cpu_load_seconds,
            "cuda_residency_seconds": time.monotonic() - started - cpu_load_seconds,
        }
    except Exception as exc:  # noqa: BLE001 - runtime failures must be retained.
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if model is not None:
            del model
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        except Exception:  # noqa: BLE001 - outer process exit is authoritative cleanup.
            pass
    after_in_process = gpu_snapshot()
    evidence = {
        "schema_version": "wave64.aqa.latentsync_model_load_worker.v1",
        "identity": identity,
        "lease": validate_lease(lease, admission),
        "gpu_before": before,
        "gpu_loaded": loaded,
        "gpu_after_in_process_cleanup": after_in_process,
        "host_available_before_bytes": host_before,
        "capacity_gate": capacity_gate,
        "model": details,
        "error": error,
        "forward_inference_performed": False,
        "fixture_consumed": False,
    }
    return evidence, 0 if error is None and loaded is not None else 1


def finalize(admission: dict[str, Any], worker: dict[str, Any], before: dict[str, Any], after: dict[str, Any], returncode: int) -> tuple[dict[str, Any], int]:
    execution = admission["execution"]
    loaded = worker.get("gpu_loaded") or before
    loaded_delta = loaded["used_mib"] - before["used_mib"]
    cleanup_delta = after["used_mib"] - before["used_mib"]
    passed = (
        returncode == 0
        and worker.get("error") is None
        and worker.get("model", {}).get("parameter_count", 0) > 0
        and worker.get("model", {}).get("config_resolution") == 512
        and worker.get("model", {}).get("parameter_devices") == ["cuda:0"]
        and worker.get("model", {}).get("parameter_dtypes") == ["torch.float16"]
        and loaded_delta >= execution["minimum_loaded_delta_mib"]
        and loaded_delta <= admission["lease"]["minimum_reserved_peak_gib"] * 1024
        and cleanup_delta <= execution["cleanup_tolerance_mib"]
        and worker.get("forward_inference_performed") is False
        and worker.get("fixture_consumed") is False
    )
    result = {
        "schema_version": "wave64.aqa.latentsync_model_load_canary.v1",
        "program_id": "W64-AQA",
        "tracker_id": "TRK-W64-137",
        "status": "PASS_MODEL_LOAD_AND_PROCESS_EXIT_CLEANUP" if passed else "FAIL_MODEL_LOAD_OR_PROCESS_EXIT_CLEANUP",
        "worker": worker,
        "gpu_before_worker": before,
        "gpu_after_worker_exit": after,
        "loaded_delta_mib": loaded_delta,
        "process_exit_cleanup_delta_mib": cleanup_delta,
        "authority": {"model_load": passed, "runtime_capacity": passed, "inference": False, "fixture_quality": False, "identity_preservation": False, "av_sync": False, "product_approval": False},
    }
    return result, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--lease-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; canary evidence is immutable")
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    lease = json.loads(args.lease_receipt.read_text(encoding="utf-8"))
    validate_lease(lease, admission)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.inner_worker:
        result, code = run_inner(admission, lease)
    else:
        validate_inputs(admission)
        before = gpu_snapshot()
        worker_path = args.output.parent / f".{args.output.name}.{uuid.uuid4().hex}.worker"
        command = [sys.executable, str(Path(__file__).resolve()), "--inner-worker", "--admission", str(args.admission), "--lease-receipt", str(args.lease_receipt), "--output", str(worker_path)]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=admission["execution"]["timeout_seconds"])
        if not worker_path.is_file():
            raise CanaryError(f"worker emitted no evidence: {completed.stderr[-1000:]}")
        try:
            worker = json.loads(worker_path.read_text(encoding="utf-8"))
        finally:
            worker_path.unlink(missing_ok=True)
        time.sleep(admission["execution"]["post_exit_wait_seconds"])
        result, code = finalize(admission, worker, before, gpu_snapshot(), completed.returncode)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.get("status", "WORKER_COMPLETE"), "output": str(args.output)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
