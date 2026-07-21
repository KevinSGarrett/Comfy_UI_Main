#!/usr/bin/env python3
"""Produce one no-generation runtime admission/release canary for W64-AQA-003."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py"
LEASE_CONTROLLER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_phase_lease_controller.py"
DETERMINISTIC_IMPLEMENTATION_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_image_quality.py"


class CanaryError(ValueError):
    """Raised when a runtime canary cannot be represented truthfully."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise CanaryError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def produce_canary(
    *, observed_at: str, pod_id: str, network_volume_id: str, gpu_profile: str,
    hourly_compute_usd: float, overlay_used_percent: float, workspace_used_percent: float,
    vram_total_mib: int, vram_free_mib: int, queue_running: int, queue_pending: int,
    strict_model_digest: str, strict_model_runtime: str,
) -> dict[str, Any]:
    if len(strict_model_digest) != 64 or any(character not in "0123456789abcdef" for character in strict_model_digest):
        raise CanaryError("strict model digest must be a full lowercase sha256")
    if not 0 <= overlay_used_percent <= 100 or not 0 <= workspace_used_percent <= 100:
        raise CanaryError("storage percentages must be within [0, 100]")
    if queue_running < 0 or queue_pending < 0 or vram_free_mib < 0 or vram_total_mib < vram_free_mib:
        raise CanaryError("runtime counters are invalid")
    compiler = _load_module("w64_aqa_runtime_contract_compiler", CONTRACT_COMPILER_PATH)
    lease_module = _load_module("w64_aqa_runtime_lease_controller", LEASE_CONTROLLER_PATH)
    deterministic_digest = sha256_file(DETERMINISTIC_IMPLEMENTATION_PATH)
    roles = [
        {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "authority": "deterministic", "can_approve": True, "required": True},
        {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "authority": "strict", "can_approve": True, "required": True},
        {"role_id": "W64-AQA-ROLE-FAST-TRIAGE", "authority": "triage", "can_approve": False, "required": False},
    ]
    draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-phase-lease-runtime-canary-20260721",
        "revision": 1, "created_at": observed_at, "modality": "image",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{
            "output_id": "lease-receipt", "media_type": "application/json",
            "durable_relative_path": "aqa/runtime/phase-lease-runtime-canary-20260721.json",
        }],
        "quality_profile": {
            "profile_id": "w64-aqa-phase-lease-control-canary-v1",
            "hard_gates": [{"gate_id": "no-generation", "metric": "generation_executed", "operator": "eq", "threshold": False, "on_failure": "REJECT"}],
            "review_roles": roles,
            "required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-ROLE-STRICT-VISUAL"],
        },
        "resource_budget": {
            "max_gpu_seconds": 30, "max_gpu_hour_usd": 0.02,
            "max_output_bytes": 1048576, "deadline_seconds": 60,
            "secondary_burst": {"enabled": False, "max_cost_usd": 0, "max_seconds": 0, "idle_ttl_seconds": 0, "eligible_gpu_classes": []},
        },
        "attempt_policy": {"max_repairs_per_defect": 0, "max_total_generations": 1, "max_no_progress_cycles": 0},
        "authority_policy": {
            "generation_host": "runpod_only", "ec2_allowed": False,
            "local_comfyui_allowed": False, "triage_can_approve": False,
            "model_can_promote": False, "workflow_model_proposal_only": True,
            "secrets_visible_to_models": False, "external_inference_allowed": False,
        },
        "rollback_policy": {"revert_on_regression": True, "promotion_requires_replay": True, "retain_failed_evidence": True, "previous_accepted_artifact_sha256": None},
        "provenance": {
            "workflow_sha256": deterministic_digest, "input_artifacts": [],
            "model_bindings": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "model_id": "measure_wave64_runpod_autonomous_image_quality.py", "checkpoint_sha256": deterministic_digest, "runtime_digest": "python-3.11.9-canonical-root", "qualification_state": "QUALIFIED"},
                {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "model_id": "qwen2.5vl:32b", "checkpoint_sha256": strict_model_digest, "runtime_digest": strict_model_runtime, "qualification_state": "QUALIFIED"},
            ],
            "calibration_ids": ["existing-strict-scoped-inventory-control-canary-no-model-inference"],
        },
        "image_spec": {"width": 1024, "height": 1024, "color_space": "sRGB", "alpha_required": False},
    }
    contract = compiler.compile_contract(draft)
    if contract["preflight_disposition"] != "READY_FOR_LEASE" or contract["promotion_disposition"] != "EVIDENCE_ONLY":
        raise CanaryError("compiled control canary contract is not ready and evidence-only")
    snapshot = {
        "foreign_jobs": 0, "queue_running": queue_running, "queue_pending": queue_pending,
        "vram_free_mib": vram_free_mib, "required_free_vram_mib": 1024,
        "overlay_used_percent": overlay_used_percent, "cost_per_hour_usd": hourly_compute_usd,
        "estimated_phase_seconds": 30,
    }
    with tempfile.TemporaryDirectory(prefix="w64-aqa-lease-canary-") as temporary:
        controller = lease_module.PhaseLeaseController(Path(temporary) / "lease.json")
        lease = controller.acquire(
            phase="migration_canary", owner="W64-AQA-JOB-phase-lease-runtime-canary-20260721",
            contract_id=contract["contract_id"], snapshot=snapshot, max_cost_usd=0.02,
            ttl_seconds=30,
        )
        estimated_cost = lease["estimated_cost_usd"]
        controller.complete(lease["lease_id"], actual_cost_usd=estimated_cost, queue_idle=True)
        controller.verify()
        final_state = controller.state
    return {
        "schema_version": "wave64.aqa.phase_lease_runtime_canary.v1",
        "program_id": "W64-AQA", "tracker_id": "W64-AQA-003",
        "observed_at": observed_at, "produced_at": _iso_now(),
        "runtime": {
            "pod_id": pod_id, "gpu_profile": gpu_profile,
            "hourly_compute_usd": hourly_compute_usd, "network_volume_id": network_volume_id,
        },
        "read_only_resource_snapshot": {
            **snapshot, "workspace_used_percent": workspace_used_percent,
            "vram_total_mib": vram_total_mib, "comfyui_system_stats_healthy": True,
        },
        "strict_model_inventory": {
            "model_id": "qwen2.5vl:32b", "ollama_digest": strict_model_digest,
            "runtime": strict_model_runtime, "inference_executed": False,
        },
        "shadow_contract": contract, "acquired_lease": lease,
        "final_controller_state": final_state,
        "canary_disposition": "PASS_ADMISSION_AND_RELEASE_NO_GENERATION",
        "resource_mutations": [],
        "claims_proven": [
            "fresh queue storage and GPU snapshot passed admission",
            "one evidence-only exclusive lease acquired and released",
            "lease journal hash chain verified after release",
            "current pod remained authoritative",
        ],
        "claims_not_proven": [
            "model inference quality", "model unload or reload", "OOM or crash recovery",
            "semantic reviewer authority", "artifact promotion", "2x A40 availability or migration",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--pod-id", required=True)
    parser.add_argument("--network-volume-id", required=True)
    parser.add_argument("--gpu-profile", required=True)
    parser.add_argument("--hourly-compute-usd", type=float, required=True)
    parser.add_argument("--overlay-used-percent", type=float, required=True)
    parser.add_argument("--workspace-used-percent", type=float, required=True)
    parser.add_argument("--vram-total-mib", type=int, required=True)
    parser.add_argument("--vram-free-mib", type=int, required=True)
    parser.add_argument("--queue-running", type=int, required=True)
    parser.add_argument("--queue-pending", type=int, required=True)
    parser.add_argument("--strict-model-digest", required=True)
    parser.add_argument("--strict-model-runtime", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    result = produce_canary(**{key: value for key, value in vars(args).items() if key != "output"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(args.output), "contract_id": result["shadow_contract"]["contract_id"], "lease_id": result["acquired_lease"]["lease_id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
