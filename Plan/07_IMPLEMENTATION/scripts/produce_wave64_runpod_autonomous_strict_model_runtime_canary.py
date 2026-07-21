#!/usr/bin/env python3
"""Run one bounded qwen2.5vl:32b load/refusal/unload canary on the current pod."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[3]
LEASE_CONTROLLER_PATH = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_phase_lease_controller.py"
)
MODEL_ID = "qwen2.5vl:32b"
EXPECTED_DIGEST = "3edc3a52fe988de3e8ba4f99ac1f21a1bbc35e1af32a74983fe4e1667d6b6188"
PROMPT_ID = "w64-aqa-missing-media-refusal-v1"
PROMPT = (
    "You are evaluating an image, but no image was supplied. Return only JSON with "
    'decision "REFUSE" and reason_code "MISSING_MEDIA". Do not infer image content.'
)


class ModelCanaryError(RuntimeError):
    """Raised when the bounded runtime canary cannot pass truthfully."""


REMOTE_PROGRAM = r'''import json, shutil, subprocess, sys, time, urllib.request

def http(method, url, payload=None, timeout=15):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("remote response is not an object")
    return value

def gpu():
    row = subprocess.check_output([
        "nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ], text=True).strip().splitlines()[0]
    name, total, used, free, utilization = [part.strip() for part in row.split(",")]
    return {"name": name, "total_mib": int(total), "used_mib": int(used), "free_mib": int(free), "utilization_percent": int(utilization)}

def storage(path):
    usage = shutil.disk_usage(path)
    return {"path": path, "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free, "used_percent": round(usage.used * 100 / usage.total, 3)}

def foreign_workloads():
    rows = subprocess.check_output(["ps", "-eo", "pid=,args="], text=True).splitlines()
    patterns = {
        "run_tournament_mvc_visual_hard_qa.py": "maskfactory_strict_visual_burst",
        "_pod_hand_tournament_": "maskfactory_hand_tournament",
    }
    observed = []
    for row in rows:
        stripped = row.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        for marker, workload_class in patterns.items():
            if marker in command:
                observed.append({"pid": int(pid_text), "workload_class": workload_class})
                break
    return sorted(observed, key=lambda item: (item["workload_class"], item["pid"]))

def probe():
    queue = http("GET", "http://127.0.0.1:8188/queue")
    system_stats = http("GET", "http://127.0.0.1:8188/system_stats")
    tags = http("GET", "http://127.0.0.1:11434/api/tags")
    loaded = http("GET", "http://127.0.0.1:11434/api/ps")
    return {
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queue_running": len(queue.get("queue_running") or []),
        "queue_pending": len(queue.get("queue_pending") or []),
        "comfyui_system_stats_healthy": isinstance(system_stats.get("system"), dict),
        "gpu": gpu(), "overlay": storage("/"), "workspace": storage("/workspace"),
        "installed_models": [{"name": item.get("name"), "digest": item.get("digest")} for item in tags.get("models") or []],
        "loaded_models": [item.get("name") for item in loaded.get("models") or []],
        "active_foreign_workloads": foreign_workloads(),
    }

request = json.loads(sys.argv[1])
if request["action"] == "probe":
    result = probe()
elif request["action"] == "infer":
    active_foreign = foreign_workloads()
    if active_foreign:
        raise RuntimeError("foreign workload appeared before inference: " + json.dumps(active_foreign))
    schema = {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["REFUSE"]},
            "reason_code": {"type": "string", "enum": ["MISSING_MEDIA"]},
        },
        "required": ["decision", "reason_code"],
        "additionalProperties": False,
    }
    started = time.monotonic()
    response = http("POST", "http://127.0.0.1:11434/api/generate", {
        "model": request["model"], "prompt": request["prompt"], "stream": False,
        "format": schema, "keep_alive": 0,
        "options": {"temperature": 0, "seed": 64008, "num_predict": 64},
    }, timeout=request["timeout_seconds"])
    result = {
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "done": response.get("done"), "done_reason": response.get("done_reason"),
        "response": response.get("response"), "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"), "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }
elif request["action"] == "unload":
    response = http("POST", "http://127.0.0.1:11434/api/generate", {
        "model": request["model"], "prompt": "", "stream": False, "keep_alive": 0,
    }, timeout=60)
    result = {"done": response.get("done"), "done_reason": response.get("done_reason")}
else:
    raise RuntimeError("unsupported remote action")
print(json.dumps(result, sort_keys=True))
'''


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ModelCanaryError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ssh_json(
    host: str,
    port: int,
    request: dict[str, Any],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    encoded_program = base64.b64encode(REMOTE_PROGRAM.encode("utf-8")).decode("ascii")
    remote_command = (
        "python3 -c \"import base64;exec(base64.b64decode('"
        + encoded_program
        + "'))\" '"
        + json.dumps(request, separators=(",", ":"))
        + "'"
    )
    completed = subprocess.run(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-p", str(port), host, remote_command,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:500]
        raise ModelCanaryError(f"remote action failed: {detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ModelCanaryError("remote action returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise ModelCanaryError("remote action returned a non-object")
    return result


def _installed_digest(snapshot: dict[str, Any], model_id: str) -> str | None:
    for model in snapshot.get("installed_models", []):
        if model.get("name") == model_id:
            return model.get("digest")
    return None


def _preflight_reasons(snapshot: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if snapshot.get("queue_running") or snapshot.get("queue_pending"):
        reasons.append("COMFYUI_QUEUE_NOT_IDLE")
    if snapshot.get("comfyui_system_stats_healthy") is not True:
        reasons.append("COMFYUI_SYSTEM_STATS_UNHEALTHY")
    if snapshot.get("loaded_models"):
        reasons.append("UNOWNED_OLLAMA_RESIDENCY_PRESENT")
    if snapshot.get("active_foreign_workloads"):
        reasons.append("ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT")
    if snapshot.get("overlay", {}).get("used_percent", 100) >= 85:
        reasons.append("OVERLAY_PRESSURE")
    if snapshot.get("gpu", {}).get("free_mib", 0) < 30000:
        reasons.append("INSUFFICIENT_FREE_VRAM")
    if _installed_digest(snapshot, MODEL_ID) != EXPECTED_DIGEST:
        reasons.append("STRICT_MODEL_DIGEST_ABSENT_OR_CHANGED")
    return sorted(set(reasons))


def _assert_safe_preflight(snapshot: dict[str, Any]) -> None:
    reasons = _preflight_reasons(snapshot)
    if reasons:
        raise ModelCanaryError("preflight blocked: " + ";".join(reasons))


def capture_admission_snapshot(
    *,
    host: str,
    port: int,
    pod_id: str,
    network_volume_id: str,
    hourly_compute_usd: float,
    remote: Callable[..., dict[str, Any]] = ssh_json,
) -> dict[str, Any]:
    snapshot = remote(host, port, {"action": "probe"}, timeout_seconds=30)
    reasons = _preflight_reasons(snapshot)
    return {
        "schema_version": "wave64.aqa.strict_model_admission_snapshot.v1",
        "program_id": "W64-AQA",
        "tracker_ids": ["W64-AQA-003", "W64-AQA-008"],
        "produced_at": _iso_now(),
        "runtime": {
            "pod_id": pod_id,
            "network_volume_id": network_volume_id,
            "hourly_compute_usd": hourly_compute_usd,
            "remote_endpoint_retained": False,
        },
        "resource_snapshot": snapshot,
        "admission_disposition": (
            "READY_NO_ACTION" if not reasons else "BLOCKED_NO_ACTION"
        ),
        "blocker_codes": reasons,
        "inference_executed": False,
        "model_load_executed": False,
        "lease_acquired": False,
        "resource_mutations": [],
        "product_approval_granted": False,
        "next_action": (
            "Run the bounded load/refusal/unload canary"
            if not reasons
            else "Switch lanes and retry only after every blocker clears"
        ),
    }


def run_canary(
    *,
    host: str,
    port: int,
    pod_id: str,
    network_volume_id: str,
    hourly_compute_usd: float,
    remote: Callable[..., dict[str, Any]] = ssh_json,
) -> dict[str, Any]:
    if hourly_compute_usd <= 0:
        raise ModelCanaryError("hourly compute price must be positive")
    pre = remote(host, port, {"action": "probe"}, timeout_seconds=30)
    _assert_safe_preflight(pre)
    lease_module = _load_module("w64_aqa_model_canary_lease", LEASE_CONTROLLER_PATH)
    request_contract = {
        "schema_version": "wave64.aqa.strict_model_runtime_canary.v1",
        "pod_id": pod_id,
        "model_id": MODEL_ID,
        "model_digest": EXPECTED_DIGEST,
        "prompt_id": PROMPT_ID,
        "decision_authority": "capacity_and_refusal_control_only",
        "media_generation": False,
        "product_approval": False,
    }
    contract_id = hashlib.sha256(_canonical_bytes(request_contract)).hexdigest()
    snapshot = {
        "foreign_jobs": 0,
        "queue_running": pre["queue_running"],
        "queue_pending": pre["queue_pending"],
        "vram_free_mib": pre["gpu"]["free_mib"],
        "required_free_vram_mib": 30000,
        "overlay_used_percent": pre["overlay"]["used_percent"],
        "cost_per_hour_usd": hourly_compute_usd,
        "estimated_phase_seconds": 300,
    }
    with tempfile.TemporaryDirectory(prefix="w64-aqa-strict-model-canary-") as temporary:
        controller = lease_module.PhaseLeaseController(Path(temporary) / "lease.json")
        lease = controller.acquire(
            phase="model_load",
            owner="W64-AQA-JOB-strict-model-runtime-canary-20260721",
            contract_id=contract_id,
            snapshot=snapshot,
            max_cost_usd=0.07,
            ttl_seconds=600,
        )
        started = time.monotonic()
        inference: dict[str, Any] | None = None
        cleanup: dict[str, Any] | None = None
        try:
            inference = remote(
                host,
                port,
                {
                    "action": "infer", "model": MODEL_ID, "prompt": PROMPT,
                    "timeout_seconds": 300,
                },
                timeout_seconds=330,
            )
            try:
                decision = json.loads(inference.get("response", ""))
            except json.JSONDecodeError as exc:
                raise ModelCanaryError("strict model returned invalid JSON") from exc
            if decision != {"decision": "REFUSE", "reason_code": "MISSING_MEDIA"}:
                raise ModelCanaryError("strict model did not return the exact refusal contract")
        finally:
            cleanup = remote(
                host,
                port,
                {"action": "unload", "model": MODEL_ID},
                timeout_seconds=90,
            )
        post = remote(host, port, {"action": "probe"}, timeout_seconds=30)
        if post.get("queue_running") or post.get("queue_pending"):
            raise ModelCanaryError("ComfyUI queue changed during the model canary")
        if MODEL_ID in (post.get("loaded_models") or []):
            raise ModelCanaryError("owned strict model did not unload")
        if post.get("comfyui_system_stats_healthy") is not True:
            raise ModelCanaryError("ComfyUI became unhealthy during the model canary")
        if post.get("gpu", {}).get("free_mib", 0) < pre["gpu"]["free_mib"] - 2048:
            raise ModelCanaryError("VRAM did not return within the bounded unload tolerance")
        actual_seconds = time.monotonic() - started
        actual_cost_usd = hourly_compute_usd * actual_seconds / 3600
        controller.complete(
            lease["lease_id"],
            actual_cost_usd=actual_cost_usd,
            queue_idle=True,
        )
        controller.verify()
        final_state = controller.state
    assert inference is not None and cleanup is not None
    parsed_response = json.loads(inference.pop("response"))
    return {
        "schema_version": "wave64.aqa.strict_model_runtime_canary.v1",
        "program_id": "W64-AQA",
        "tracker_ids": ["W64-AQA-003", "W64-AQA-008"],
        "produced_at": _iso_now(),
        "runtime": {
            "pod_id": pod_id,
            "network_volume_id": network_volume_id,
            "gpu_profile": pre["gpu"]["name"],
            "hourly_compute_usd": hourly_compute_usd,
            "remote_endpoint_retained": False,
        },
        "request_contract": request_contract,
        "contract_id": contract_id,
        "preflight_snapshot": pre,
        "lease": lease,
        "inference_receipt": {
            **inference,
            "response_sha256": hashlib.sha256(_canonical_bytes(parsed_response)).hexdigest(),
            "parsed_response": parsed_response,
            "prompt_id": PROMPT_ID,
            "media_supplied": False,
            "media_generation_executed": False,
        },
        "cleanup_receipt": {**cleanup, "method": "ollama_keep_alive_zero_exact_owned_model"},
        "postflight_snapshot": post,
        "final_controller_state": final_state,
        "canary_disposition": "PASS_MODEL_LOAD_REFUSAL_AND_UNLOAD",
        "authority_granted": "CAPACITY_AND_MISSING_MEDIA_REFUSAL_CONTROL_ONLY",
        "product_approval_granted": False,
        "resource_mutations": [
            {
                "type": "ephemeral_model_residency",
                "model_id": MODEL_ID,
                "action": "load_infer_keep_alive_zero_unload",
                "owned": True,
            }
        ],
        "claims_not_proven": [
            "image review quality",
            "sampled-video review quality",
            "full strict visual role qualification",
            "independent reviewer authority",
            "OOM or crash recovery",
            "artifact promotion",
            "2x A40 availability or migration",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--pod-id", required=True)
    parser.add_argument("--network-volume-id", required=True)
    parser.add_argument("--hourly-compute-usd", type=float, required=True)
    parser.add_argument("--admission-only", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    runner = capture_admission_snapshot if args.admission_only else run_canary
    evidence = runner(
        host=args.host, port=args.port, pod_id=args.pod_id,
        network_volume_id=args.network_volume_id,
        hourly_compute_usd=args.hourly_compute_usd,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(args.output),
                "lease_id": evidence.get("lease", {}).get("lease_id"),
                "disposition": evidence.get(
                    "canary_disposition", evidence.get("admission_disposition")
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
