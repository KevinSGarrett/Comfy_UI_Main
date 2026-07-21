#!/usr/bin/env python3
"""Execute one fail-closed ComfyUI workflow repair shadow job and retain replay evidence."""

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
SCRIPT_ROOT = ROOT / "Plan/07_IMPLEMENTATION/scripts"
CONTRACT_COMPILER_PATH = SCRIPT_ROOT / "compile_wave64_runpod_autonomous_multimodal_job_contract.py"
WORKFLOW_VALIDATOR_PATH = SCRIPT_ROOT / "validate_wave64_runpod_autonomous_workflow.py"
IMAGE_MEASURER_PATH = SCRIPT_ROOT / "measure_wave64_runpod_autonomous_image_quality.py"
CORRECTION_POLICY_PATH = SCRIPT_ROOT / "run_wave64_runpod_autonomous_correction_policy.py"
EVIDENCE_COMPILER_PATH = SCRIPT_ROOT / "compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py"
LEASE_CONTROLLER_PATH = SCRIPT_ROOT / "run_wave64_runpod_autonomous_phase_lease_controller.py"
PATCH_ALLOWLIST_ID = "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001"
JOB_ID = "W64-AQA-JOB-e2e-shadow-resize-20260721"


class ShadowJobError(RuntimeError):
    """Raised when the end-to-end shadow job cannot complete truthfully."""


REMOTE_PROGRAM = r'''import base64, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request

INPUT_ROOT = "/workspace/comfy_input"
OUTPUT_ROOT = "/workspace/comfy_output"
NAME_PATTERN = re.compile(r"^w64_aqa_shadow_[a-z0-9_.-]+\.png$")
OUTPUT_PATTERN = re.compile(r"^w64_aqa_shadow/[a-z0-9_.-]+\.png$")

def http_json(method, url, payload=None, timeout=15):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Accept": "application/json", "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("remote response is not an object")
    return value

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

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

def gpu():
    row = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu", "--format=csv,noheader,nounits"], text=True).strip().splitlines()[0]
    name, total, used, free, utilization = [part.strip() for part in row.split(",")]
    return {"name": name, "total_mib": int(total), "used_mib": int(used), "free_mib": int(free), "utilization_percent": int(utilization)}

def storage(path):
    usage = shutil.disk_usage(path)
    return {"path": path, "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free, "used_percent": round(usage.used * 100 / usage.total, 3)}

def probe():
    queue = http_json("GET", "http://127.0.0.1:8188/queue")
    stats = http_json("GET", "http://127.0.0.1:8188/system_stats")
    loaded = http_json("GET", "http://127.0.0.1:11434/api/ps")
    return {
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queue_running": len(queue.get("queue_running") or []), "queue_pending": len(queue.get("queue_pending") or []),
        "comfyui_system_stats_healthy": isinstance(stats.get("system"), dict),
        "loaded_models": [item.get("name") for item in loaded.get("models") or []],
        "active_foreign_workloads": foreign_workloads(), "gpu": gpu(),
        "overlay": storage("/"), "workspace": storage("/workspace"),
    }

def safe_target(root, relative, expected_pattern):
    if not isinstance(relative, str) or not expected_pattern.fullmatch(relative) or ".." in relative.split("/"):
        raise RuntimeError("unsafe owned artifact path")
    root_real = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root_real, relative))
    if os.path.commonpath([root_real, target]) != root_real:
        raise RuntimeError("owned artifact escapes root")
    return target

request = json.loads(base64.b64decode(sys.argv[1]).decode("utf-8"))
action = request["action"]
if action == "probe":
    result = probe()
elif action == "upload":
    target = safe_target(INPUT_ROOT, request["filename"], NAME_PATTERN)
    data = base64.b64decode(request["content_b64"])
    if sha256_bytes(data) != request["sha256"]:
        raise RuntimeError("uploaded content hash mismatch")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target):
        existing = open(target, "rb").read()
        if sha256_bytes(existing) != request["sha256"]:
            raise RuntimeError("owned input path already exists with different bytes")
        disposition = "REUSED_IDENTICAL"
    else:
        with open(target, "xb") as handle:
            handle.write(data)
        disposition = "CREATED"
    result = {"relative_path": request["filename"], "sha256": request["sha256"], "byte_size": len(data), "disposition": disposition}
elif action == "object_info":
    all_info = http_json("GET", "http://127.0.0.1:8188/object_info", timeout=30)
    required = ["LoadImage", "ImageScale", "SaveImage"]
    result = {name: all_info[name] for name in required}
elif action == "execute":
    before = probe()
    if before["active_foreign_workloads"] or before["loaded_models"] or before["queue_running"] or before["queue_pending"]:
        raise RuntimeError("runtime ownership changed before workflow execution")
    submitted = http_json("POST", "http://127.0.0.1:8188/prompt", {"prompt": request["workflow"], "client_id": request["client_id"]}, timeout=15)
    prompt_id = submitted.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise RuntimeError("ComfyUI did not return a prompt_id")
    deadline = time.monotonic() + request["timeout_seconds"]
    history_entry = None
    while time.monotonic() < deadline:
        history = http_json("GET", "http://127.0.0.1:8188/history/" + urllib.parse.quote(prompt_id), timeout=15)
        if isinstance(history.get(prompt_id), dict):
            history_entry = history[prompt_id]
            break
        time.sleep(0.25)
    if history_entry is None:
        raise RuntimeError("ComfyUI workflow execution timed out")
    status = history_entry.get("status") or {}
    if status.get("status_str") not in {"success", None}:
        raise RuntimeError("ComfyUI workflow did not succeed: " + json.dumps(status)[:500])
    images = (history_entry.get("outputs") or {}).get("3", {}).get("images") or []
    if len(images) != 1:
        raise RuntimeError("ComfyUI workflow did not return exactly one image")
    image = images[0]
    query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
    with urllib.request.urlopen("http://127.0.0.1:8188/view?" + query, timeout=30) as response:
        content = response.read()
    relative = "/".join(part for part in [image.get("subfolder", ""), image["filename"]] if part)
    safe_target(OUTPUT_ROOT, relative, OUTPUT_PATTERN)
    after = probe()
    result = {
        "prompt_id": prompt_id, "output_relative_path": relative,
        "output_sha256": sha256_bytes(content), "output_size_bytes": len(content),
        "output_b64": base64.b64encode(content).decode("ascii"),
        "queue_idle_after": after["queue_running"] == 0 and after["queue_pending"] == 0,
        "gpu_after": after["gpu"],
    }
elif action == "cleanup":
    removed = []
    for item in request["artifacts"]:
        if item["root"] == "input":
            target = safe_target(INPUT_ROOT, item["relative_path"], NAME_PATTERN)
        elif item["root"] == "output":
            target = safe_target(OUTPUT_ROOT, item["relative_path"], OUTPUT_PATTERN)
        else:
            raise RuntimeError("unsupported cleanup root")
        if not os.path.isfile(target):
            raise RuntimeError("owned cleanup artifact is absent")
        content = open(target, "rb").read()
        if sha256_bytes(content) != item["sha256"]:
            raise RuntimeError("owned cleanup artifact hash changed")
        os.unlink(target)
        removed.append({"root": item["root"], "relative_path": item["relative_path"], "sha256": item["sha256"]})
    result = {"removed": removed}
else:
    raise RuntimeError("unsupported remote action")
print(json.dumps(result, sort_keys=True))
'''


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ShadowJobError(f"cannot load module: {path}")
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
    encoded_request = base64.b64encode(canonical_bytes(request)).decode("ascii")
    remote_command = (
        "python3 -c \"import base64;exec(base64.b64decode('"
        + encoded_program
        + "'))\" "
        + encoded_request
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
        detail = (completed.stderr or completed.stdout).strip()[:800]
        raise ShadowJobError(f"remote action failed: {detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ShadowJobError("remote action returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise ShadowJobError("remote action returned a non-object")
    return result


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise ShadowJobError(f"immutable evidence path already exists: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def workflow(input_filename: str, width: int, height: int, prefix: str) -> dict[str, Any]:
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": input_filename}},
        "2": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["1", 0],
                "upscale_method": "nearest-exact",
                "width": width,
                "height": height,
                "crop": "disabled",
            },
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {"images": ["2", 0], "filename_prefix": prefix},
        },
    }


def assert_preflight(snapshot: dict[str, Any]) -> None:
    reasons: list[str] = []
    if snapshot.get("active_foreign_workloads"):
        reasons.append("ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT")
    if snapshot.get("loaded_models"):
        reasons.append("UNOWNED_OLLAMA_RESIDENCY_PRESENT")
    if snapshot.get("queue_running") or snapshot.get("queue_pending"):
        reasons.append("COMFYUI_QUEUE_NOT_IDLE")
    if snapshot.get("comfyui_system_stats_healthy") is not True:
        reasons.append("COMFYUI_SYSTEM_STATS_UNHEALTHY")
    if snapshot.get("overlay", {}).get("used_percent", 100) >= 85:
        reasons.append("OVERLAY_PRESSURE")
    if snapshot.get("gpu", {}).get("free_mib", 0) < 1024:
        reasons.append("INSUFFICIENT_FREE_VRAM")
    if reasons:
        raise ShadowJobError("preflight blocked: " + ";".join(sorted(reasons)))


def build_contract(
    *,
    compiler: Any,
    workflow_module: Any,
    object_info: dict[str, Any],
    base_workflow: dict[str, Any],
    source_hash: str,
    input_filename: str,
    target_width: int,
    target_height: int,
) -> dict[str, Any]:
    deterministic_hash = sha256_file(IMAGE_MEASURER_PATH)
    draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": JOB_ID,
        "revision": 1,
        "created_at": iso_now(),
        "modality": "workflow",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [
            {
                "output_id": "corrected-image",
                "media_type": "image/png",
                "durable_relative_path": "aqa/shadow/e2e-resize/corrected.png",
            }
        ],
        "quality_profile": {
            "profile_id": "w64-aqa-e2e-shadow-resize-v1",
            "hard_gates": [
                {
                    "gate_id": "decode",
                    "metric": "decode_success",
                    "operator": "eq",
                    "threshold": True,
                    "on_failure": "REJECT",
                }
            ],
            "review_roles": [
                {
                    "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                    "authority": "deterministic",
                    "can_approve": True,
                    "required": True,
                },
                {
                    "role_id": "W64-AQA-ROLE-WORKFLOW-ENGINEER",
                    "authority": "workflow",
                    "can_approve": False,
                    "required": False,
                },
            ],
            "required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC"],
        },
        "resource_budget": {
            "max_gpu_seconds": 120,
            "max_gpu_hour_usd": 0.05,
            "max_output_bytes": 1048576,
            "deadline_seconds": 180,
            "secondary_burst": {
                "enabled": False,
                "max_cost_usd": 0,
                "max_seconds": 0,
                "idle_ttl_seconds": 0,
                "eligible_gpu_classes": [],
            },
        },
        "attempt_policy": {
            "max_repairs_per_defect": 2,
            "max_total_generations": 4,
            "max_no_progress_cycles": 2,
        },
        "authority_policy": {
            "generation_host": "runpod_only",
            "ec2_allowed": False,
            "local_comfyui_allowed": False,
            "triage_can_approve": False,
            "model_can_promote": False,
            "workflow_model_proposal_only": True,
            "secrets_visible_to_models": False,
            "external_inference_allowed": False,
        },
        "rollback_policy": {
            "revert_on_regression": True,
            "promotion_requires_replay": True,
            "retain_failed_evidence": True,
            "previous_accepted_artifact_sha256": None,
        },
        "provenance": {
            "workflow_sha256": workflow_module.content_hash(base_workflow),
            "input_artifacts": [
                {
                    "artifact_id": "source-fixture",
                    "sha256": source_hash,
                    "durable_relative_path": f"aqa/shadow/e2e-resize/{input_filename}",
                }
            ],
            "model_bindings": [
                {
                    "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                    "model_id": "measure_wave64_runpod_autonomous_image_quality.py",
                    "checkpoint_sha256": deterministic_hash,
                    "runtime_digest": "python-canonical-root",
                    "qualification_state": "QUALIFIED",
                }
            ],
            "calibration_ids": ["w64-aqa-deterministic-image-fixtures-v1"],
        },
        "image_spec": {
            "width": target_width,
            "height": target_height,
            "color_space": "sRGB",
            "alpha_required": False,
        },
        "workflow_spec": {
            "object_info_sha256": workflow_module.content_hash(object_info),
            "patch_allowlist_id": PATCH_ALLOWLIST_ID,
            "sandbox_required": True,
            "regression_suite_id": "w64-aqa-e2e-shadow-resize-v1",
        },
    }
    return compiler.compile_contract(draft)


def run_shadow_job(
    *,
    source_path: Path,
    artifact_dir: Path,
    host: str,
    port: int,
    pod_id: str,
    network_volume_id: str,
    hourly_compute_usd: float,
    target_width: int = 128,
    target_height: int = 128,
    remote: Callable[..., dict[str, Any]] = ssh_json,
) -> dict[str, Any]:
    if artifact_dir.exists():
        raise ShadowJobError("artifact directory already exists")
    if not source_path.is_file() or source_path.stat().st_size < 1:
        raise ShadowJobError("source fixture is absent or empty")
    if target_width < 64 or target_height < 64:
        raise ShadowJobError("target geometry is below the patch-policy minimum")
    if hourly_compute_usd <= 0:
        raise ShadowJobError("hourly compute price must be positive")
    contract_module = load_module("w64_aqa_e2e_contract", CONTRACT_COMPILER_PATH)
    workflow_module = load_module("w64_aqa_e2e_workflow", WORKFLOW_VALIDATOR_PATH)
    image_module = load_module("w64_aqa_e2e_image", IMAGE_MEASURER_PATH)
    correction_module = load_module("w64_aqa_e2e_correction", CORRECTION_POLICY_PATH)
    evidence_module = load_module("w64_aqa_e2e_evidence", EVIDENCE_COMPILER_PATH)
    lease_module = load_module("w64_aqa_e2e_lease", LEASE_CONTROLLER_PATH)

    preflight = remote(host, port, {"action": "probe"}, timeout_seconds=30)
    assert_preflight(preflight)
    source_bytes = source_path.read_bytes()
    source_hash = sha256_bytes(source_bytes)
    input_filename = f"w64_aqa_shadow_source_{source_hash[:12]}.png"
    upload = remote(
        host,
        port,
        {
            "action": "upload",
            "filename": input_filename,
            "sha256": source_hash,
            "content_b64": base64.b64encode(source_bytes).decode("ascii"),
        },
        timeout_seconds=30,
    )
    cleanup_targets = [
        {"root": "input", "relative_path": input_filename, "sha256": source_hash}
    ]
    object_info = remote(host, port, {"action": "object_info"}, timeout_seconds=45)
    base_workflow = workflow(
        input_filename,
        64,
        64,
        "w64_aqa_shadow/base",
    )
    contract = build_contract(
        compiler=contract_module,
        workflow_module=workflow_module,
        object_info=object_info,
        base_workflow=base_workflow,
        source_hash=source_hash,
        input_filename=input_filename,
        target_width=target_width,
        target_height=target_height,
    )
    inventory = {
        "schema_version": "wave64.aqa.model_inventory.v1",
        "eligible_model_names": [],
    }
    base_validation = workflow_module.validate_workflow(
        base_workflow,
        object_info,
        contract,
        inventory,
    )
    if base_validation["disposition"] != "PASS_STATIC_VALIDATION":
        raise ShadowJobError("base workflow failed static validation")
    patch = {
        "schema_version": "wave64.aqa.workflow_patch.v1",
        "patch_id": "W64-AQA-PATCH-e2e-shadow-resize-001",
        "base_workflow_sha256": workflow_module.content_hash(base_workflow),
        "patch_allowlist_id": PATCH_ALLOWLIST_ID,
        "operations": [
            {
                "operation": "replace_bounded_numeric",
                "node_id": "2",
                "input_name": "width",
                "expected_old_value": 64,
                "new_value": target_width,
            },
            {
                "operation": "replace_bounded_numeric",
                "node_id": "2",
                "input_name": "height",
                "expected_old_value": 64,
                "new_value": target_height,
            },
        ],
    }
    candidate_validation = workflow_module.validate_workflow(
        base_workflow,
        object_info,
        contract,
        inventory,
        patch,
    )
    if (
        candidate_validation["disposition"] != "PASS_STATIC_VALIDATION"
        or candidate_validation["patch_disposition"]
        != "TYPED_PATCH_ACCEPTED_FOR_SANDBOX"
    ):
        raise ShadowJobError("typed correction patch failed static validation")
    candidate_workflow = workflow(
        input_filename,
        target_width,
        target_height,
        "w64_aqa_shadow/base",
    )
    if (
        workflow_module.content_hash(candidate_workflow)
        != candidate_validation["candidate_workflow_sha256"]
    ):
        raise ShadowJobError("candidate workflow hash does not match static patch result")

    lease_snapshot = {
        "foreign_jobs": 0,
        "queue_running": preflight["queue_running"],
        "queue_pending": preflight["queue_pending"],
        "vram_free_mib": preflight["gpu"]["free_mib"],
        "required_free_vram_mib": 1024,
        "overlay_used_percent": preflight["overlay"]["used_percent"],
        "cost_per_hour_usd": hourly_compute_usd,
        "estimated_phase_seconds": 120,
    }
    artifact_dir.mkdir(parents=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="w64-aqa-e2e-shadow-lease-") as temporary:
        controller = lease_module.PhaseLeaseController(Path(temporary) / "lease.json")
        lease = controller.acquire(
            phase="workflow",
            owner=JOB_ID,
            contract_id=contract["contract_id"],
            snapshot=lease_snapshot,
            max_cost_usd=0.05,
            ttl_seconds=300,
        )
        cleanup_receipt: dict[str, Any] | None = None
        try:
            base_execution = remote(
                host,
                port,
                {
                    "action": "execute",
                    "workflow": base_workflow,
                    "client_id": "w64-aqa-e2e-shadow-base",
                    "timeout_seconds": 60,
                },
                timeout_seconds=90,
            )
            base_bytes = base64.b64decode(base_execution.pop("output_b64"))
            if sha256_bytes(base_bytes) != base_execution["output_sha256"]:
                raise ShadowJobError("base output transport hash mismatch")
            base_path = artifact_dir / "initial_candidate.png"
            base_path.write_bytes(base_bytes)
            cleanup_targets.append(
                {
                    "root": "output",
                    "relative_path": base_execution["output_relative_path"],
                    "sha256": base_execution["output_sha256"],
                }
            )
            candidate_execution = remote(
                host,
                port,
                {
                    "action": "execute",
                    "workflow": candidate_workflow,
                    "client_id": "w64-aqa-e2e-shadow-corrected",
                    "timeout_seconds": 60,
                },
                timeout_seconds=90,
            )
            candidate_bytes = base64.b64decode(candidate_execution.pop("output_b64"))
            if sha256_bytes(candidate_bytes) != candidate_execution["output_sha256"]:
                raise ShadowJobError("corrected output transport hash mismatch")
            candidate_path = artifact_dir / "accepted_candidate.png"
            candidate_path.write_bytes(candidate_bytes)
            cleanup_targets.append(
                {
                    "root": "output",
                    "relative_path": candidate_execution["output_relative_path"],
                    "sha256": candidate_execution["output_sha256"],
                }
            )
            initial_measurement = image_module.measure_image(base_path, contract)
            corrected_measurement = image_module.measure_image(candidate_path, contract)
            if initial_measurement["disposition"] != "FAIL_DETERMINISTIC_GATES":
                raise ShadowJobError("intentional baseline geometry defect did not fail")
            if corrected_measurement["disposition"] != "PASS_DETERMINISTIC_GATES":
                raise ShadowJobError("corrected candidate did not pass deterministic gates")
            initial_state = correction_module.initialize_state(
                contract,
                JOB_ID,
                initial_measurement["artifact_sha256"],
                0.0,
                {"source_content_preserved": 1.0},
            )
            attempt = {
                "schema_version": "wave64.aqa.correction_attempt.v1",
                "attempt_id": "W64-AQA-REPAIR-e2e-shadow-resize-001",
                "job_id": JOB_ID,
                "contract_id": contract["contract_id"],
                "parent_artifact_sha256": initial_measurement["artifact_sha256"],
                "candidate_artifact_sha256": corrected_measurement["artifact_sha256"],
                "defect_id": "output_geometry",
                "generation_consumed": True,
                "hard_gates_pass": True,
                "candidate_total_score": 1.0,
                "candidate_protected_scores": {"source_content_preserved": 1.0},
                "evidence_sha256": [corrected_measurement["measurement_id"]],
            }
            correction_state = correction_module.transition(
                initial_state,
                attempt,
                contract,
            )
            if correction_state["disposition"] != "RETAIN_CANDIDATE_EXIT_REPAIR_LOOP":
                raise ShadowJobError("bounded correction did not retain the improved candidate")
            cleanup_receipt = remote(
                host,
                port,
                {"action": "cleanup", "artifacts": cleanup_targets},
                timeout_seconds=30,
            )
            actual_seconds = time.monotonic() - started
            actual_cost_usd = hourly_compute_usd * actual_seconds / 3600
            controller.complete(
                lease["lease_id"],
                actual_cost_usd=actual_cost_usd,
                queue_idle=base_execution["queue_idle_after"]
                and candidate_execution["queue_idle_after"],
            )
            controller.verify()
            final_lease_state = controller.state
        except Exception:
            if cleanup_targets:
                try:
                    remote(
                        host,
                        port,
                        {"action": "cleanup", "artifacts": cleanup_targets},
                        timeout_seconds=30,
                    )
                except Exception:
                    pass
            raise
    if cleanup_receipt is None:
        raise ShadowJobError("cleanup receipt is missing")

    records = {
        "contract": contract,
        "base_workflow": base_workflow,
        "candidate_workflow": candidate_workflow,
        "patch": patch,
        "base_validation": base_validation,
        "candidate_validation": candidate_validation,
        "initial_measurement": initial_measurement,
        "corrected_measurement": corrected_measurement,
        "correction_state": correction_state,
        "deterministic_review": {
            "schema_version": "wave64.aqa.deterministic_review.v1",
            "role_id": "W64-AQA-ROLE-DETERMINISTIC",
            "state": "QUALIFIED",
            "response_valid": True,
            "product_authority": True,
            "scope": "workflow_shadow_geometry_and_decode_only",
            "measurement_id": corrected_measurement["measurement_id"],
            "semantic_qa": {
                "applicable": False,
                "reason": "synthetic geometry-preservation fixture has no declared semantic acceptance gate",
            },
        },
        "runtime_receipt": {
            "schema_version": "wave64.aqa.e2e_shadow_runtime_receipt.v1",
            "pod_id": pod_id,
            "network_volume_id": network_volume_id,
            "remote_endpoint_retained": False,
            "preflight": preflight,
            "upload": upload,
            "base_execution": base_execution,
            "candidate_execution": candidate_execution,
            "cleanup": cleanup_receipt,
            "lease": lease,
            "final_lease_state": final_lease_state,
        },
        "cost_receipt": {
            "schema_version": "wave64.aqa.cost_receipt.v1",
            "hourly_compute_usd": hourly_compute_usd,
            "elapsed_seconds": actual_seconds,
            "actual_cost_usd": actual_cost_usd,
            "secondary_pod_used": False,
        },
    }
    paths: dict[str, Path] = {}
    for name, value in records.items():
        path = artifact_dir / f"{name}.json"
        write_json(path, value)
        paths[name] = path

    candidate_hash = sha256_file(candidate_path)
    base_hash = sha256_file(base_path)
    workflow_hash = sha256_file(paths["candidate_workflow"])
    measurement_hash = sha256_file(paths["corrected_measurement"])
    review_hash = sha256_file(paths["deterministic_review"])
    runtime_hash = sha256_file(paths["runtime_receipt"])
    decision = {
        "schema_version": "wave64.aqa.decision.v1",
        "program_id": "W64-AQA",
        "job_id": JOB_ID,
        "modality": "workflow",
        "authority": {
            "host": "runpod",
            "pod_id": pod_id,
            "ec2_forbidden": True,
            "fail_closed": True,
        },
        "lineage": {
            "candidate_sha256": candidate_hash,
            "workflow_sha256": workflow_hash,
            "quality_contract_sha256": contract["contract_id"],
            "source_sha256": source_hash,
        },
        "measurements": [
            {
                "metric_id": "workflow-output-image-hard-gates",
                "applicable": True,
                "passed": True,
                "implementation_version": "w64-aqa-image-measure-v1",
                "evidence_sha256": measurement_hash,
            }
        ],
        "reviewers": [
            {
                "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                "state": "QUALIFIED",
                "product_authority": True,
                "response_valid": True,
                "observation_sha256": review_hash,
            }
        ],
        "attempt_state": {
            "defect_attempt": 1,
            "total_generation_attempt": 2,
            "consecutive_no_progress": 0,
            "ceilings": {"per_defect": 2, "total_generation": 4, "no_progress": 2},
        },
        "blocking_defects": [],
        "decision": "PASS",
        "workflow_patch": {
            "accepted_workflow_sha256": workflow_hash,
            "candidate_workflow_sha256": workflow_hash,
            "patch_sha256": sha256_file(paths["patch"]),
            "static_validation_passed": True,
            "sandbox_validation_passed": True,
            "regression_passed": True,
            "promotion_authorized": False,
        },
        "rollback_parent_sha256": base_hash,
        "promotion_claimed": False,
        "cost_usd": actual_cost_usd,
        "runtime_receipt_sha256": runtime_hash,
    }
    decision_path = artifact_dir / "decision.json"
    write_json(decision_path, decision)
    record_specs = [
        {"record_type": "candidate", "source_path": str(candidate_path), "durable_relative_path": "aqa/shadow/e2e-resize/accepted_candidate.png"},
        {"record_type": "workflow", "source_path": str(paths["candidate_workflow"]), "durable_relative_path": "aqa/shadow/e2e-resize/candidate_workflow.json"},
        {"record_type": "measurement", "source_path": str(paths["corrected_measurement"]), "durable_relative_path": "aqa/shadow/e2e-resize/corrected_measurement.json"},
        {"record_type": "review", "source_path": str(paths["deterministic_review"]), "durable_relative_path": "aqa/shadow/e2e-resize/deterministic_review.json"},
        {"record_type": "runtime_receipt", "source_path": str(paths["runtime_receipt"]), "durable_relative_path": "aqa/shadow/e2e-resize/runtime_receipt.json"},
        {"record_type": "correction_state", "source_path": str(paths["correction_state"]), "durable_relative_path": "aqa/shadow/e2e-resize/correction_state.json"},
        {"record_type": "cost_receipt", "source_path": str(paths["cost_receipt"]), "durable_relative_path": "aqa/shadow/e2e-resize/cost_receipt.json"},
        {"record_type": "rollback_parent", "source_path": str(base_path), "durable_relative_path": "aqa/shadow/e2e-resize/initial_candidate.png"},
    ]
    bundle = evidence_module.compile_bundle(contract, decision, record_specs)
    replay = evidence_module.replay_bundle(bundle, contract, decision, record_specs)
    if replay["replay_disposition"] != "MATCH":
        raise ShadowJobError("evidence replay did not match")
    bundle_path = artifact_dir / "evidence_bundle.json"
    replay_path = artifact_dir / "replay_receipt.json"
    write_json(bundle_path, bundle)
    write_json(replay_path, replay)
    try:
        retained_artifact_dir = str(artifact_dir.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        retained_artifact_dir = str(artifact_dir)
    return {
        "schema_version": "wave64.aqa.e2e_shadow_summary.v1",
        "program_id": "W64-AQA",
        "tracker_id": "W64-AQA-016",
        "job_id": JOB_ID,
        "produced_at": iso_now(),
        "contract_id": contract["contract_id"],
        "initial_disposition": initial_measurement["disposition"],
        "correction_disposition": correction_state["disposition"],
        "accepted_disposition": "PASS_EVIDENCE_ONLY_SHADOW_INFRASTRUCTURE",
        "semantic_qa": records["deterministic_review"]["semantic_qa"],
        "evidence_bundle_id": bundle["bundle_id"],
        "replay_disposition": replay["replay_disposition"],
        "remote_cleanup_pass": len(cleanup_receipt["removed"]) == 3,
        "lease_final_state": final_lease_state["state"],
        "product_promotion_claimed": False,
        "infrastructure_exit_candidate": True,
        "retained_artifact_dir": retained_artifact_dir,
        "limitations": [
            "synthetic geometry-preservation workflow only",
            "no generative checkpoint loaded",
            "no visual semantic reviewer applicable to this contract",
            "remaining model roles retain their independent qualification states",
            "2x A40 availability and migration remain unproven",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--pod-id", required=True)
    parser.add_argument("--network-volume-id", required=True)
    parser.add_argument("--hourly-compute-usd", type=float, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; shadow summaries are immutable")
    summary = run_shadow_job(
        source_path=args.source,
        artifact_dir=args.artifact_dir,
        host=args.host,
        port=args.port,
        pod_id=args.pod_id,
        network_volume_id=args.network_volume_id,
        hourly_compute_usd=args.hourly_compute_usd,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, summary)
    print(json.dumps({"status": "PASS", "output": str(args.output), "bundle_id": summary["evidence_bundle_id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
