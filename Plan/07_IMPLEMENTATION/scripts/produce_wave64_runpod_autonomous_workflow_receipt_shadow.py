#!/usr/bin/env python3
"""Produce a retained receipt-bound W64-AQA workflow inspection shadow."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py"
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py"
VALIDATOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py"
JOB_ID = "W64-AQA-JOB-workflow-receipt-shadow"
INPUT_KINDS = ("workflow", "object_info", "contract", "model_inventory")
GIT_OBJECT_ID_PATTERN = re.compile(r"^[a-f0-9]{40}$")
TIMESTAMP_PATTERN = re.compile(r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ShadowProducerError(ValueError):
    """Raised when the bounded retained shadow cannot be produced safely."""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ShadowProducerError(f"cannot load required component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _render(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_new(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            raw = _render(value)
            handle.write(raw)
    except FileExistsError as exc:
        raise ShadowProducerError(f"immutable output already exists: {path}") from exc
    return hashlib.sha256(raw).hexdigest()


def _object_info() -> dict[str, Any]:
    return {
        "CheckpointLoaderSimple": {
            "input": {"required": {"ckpt_name": [["base.safetensors"]]}},
            "output": ["MODEL"],
            "output_node": False,
        },
        "Sampler": {
            "input": {"required": {
                "model": ["MODEL"],
                "steps": ["INT", {"min": 1, "max": 1000}],
                "cfg": ["FLOAT", {"min": 0, "max": 100}],
                "text": ["STRING"],
            }},
            "output": ["IMAGE"],
            "output_node": False,
        },
        "SaveImage": {
            "input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING"]}},
            "output": [],
            "output_node": True,
        },
    }


def _workflow() -> dict[str, Any]:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "base.safetensors"}},
        "2": {
            "class_type": "Sampler",
            "inputs": {"model": ["1", 0], "steps": 20, "cfg": 7.0, "text": "portrait"},
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {"images": ["2", 0], "filename_prefix": "jobs/output"},
        },
    }


def _model_inventory() -> dict[str, Any]:
    return {
        "schema_version": "wave64.aqa.model_inventory.v1",
        "eligible_model_names": ["base.safetensors"],
    }


def _contract_draft(info: dict[str, Any], graph: dict[str, Any], observed_at: str) -> dict[str, Any]:
    return {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": JOB_ID,
        "revision": 1,
        "created_at": observed_at,
        "modality": "workflow",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{
            "output_id": "validation",
            "media_type": "application/json",
            "durable_relative_path": "aqa/jobs/workflow-receipt-shadow/validation.json",
        }],
        "quality_profile": {
            "profile_id": "workflow-receipt-binding-shadow-v1",
            "hard_gates": [{
                "gate_id": "static_graph",
                "metric": "static_graph_valid",
                "operator": "eq",
                "threshold": True,
                "on_failure": "REJECT",
            }],
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
            "max_gpu_seconds": 60,
            "max_gpu_hour_usd": 0.7,
            "max_output_bytes": 1048576,
            "deadline_seconds": 120,
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
            "workflow_sha256": _canonical_hash(graph),
            "input_artifacts": [],
            "model_bindings": [{
                "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                "model_id": "deterministic-python-validator",
                "checkpoint_sha256": "b" * 64,
                "runtime_digest": "python-local-shadow",
                "qualification_state": "QUALIFIED",
            }],
            "calibration_ids": ["workflow-receipt-binding-shadow-v1"],
        },
        "workflow_spec": {
            "object_info_sha256": _canonical_hash(info),
            "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
            "sandbox_required": True,
            "regression_suite_id": "workflow-regression-v1",
        },
    }


def produce(output_root: Path, source_head: str, observed_at: str) -> dict[str, Any]:
    if output_root.exists():
        raise ShadowProducerError("output root already exists; retained shadows are immutable")
    if not GIT_OBJECT_ID_PATTERN.fullmatch(source_head):
        raise ShadowProducerError("source_head must be a lowercase 40-character Git object ID")
    if not TIMESTAMP_PATTERN.fullmatch(observed_at):
        raise ShadowProducerError("observed_at must be UTC RFC3339 seconds")
    output_root.mkdir(parents=True)
    compiler = _load(COMPILER_PATH, "w64_shadow_contract_compiler")
    gateway = _load(GATEWAY_PATH, "w64_shadow_tool_gateway")
    executor = _load(EXECUTOR_PATH, "w64_shadow_tool_executor")
    validator = _load(VALIDATOR_PATH, "w64_shadow_workflow_validator")

    info, graph, models = _object_info(), _workflow(), _model_inventory()
    contract = compiler.compile_contract(_contract_draft(info, graph, observed_at))
    values = {
        "workflow": graph,
        "object_info": info,
        "contract": contract,
        "model_inventory": models,
    }
    raw_hashes: dict[str, str] = {}
    raw_inputs: dict[str, bytes] = {}
    receipts: dict[str, dict[str, Any]] = {}
    file_manifest: dict[str, str] = {}
    for kind, value in values.items():
        target = f"jobs/{JOB_ID}/inputs/{kind}.json"
        input_path = output_root.joinpath(*target.split("/"))
        raw_inputs[kind] = _render(value)
        raw_hashes[kind] = _write_new(input_path, value)
        file_manifest[target] = raw_hashes[kind]
        request = {
            "schema_version": "wave64.aqa.tool_gateway_request.v1",
            "request_id": f"W64-AQA-TOOL-workflow-shadow-{kind}",
            "job_id": JOB_ID,
            "actor_role_id": "W64-AQA-ROLE-DETERMINISTIC",
            "authority_binding_sha256": contract["contract_id"],
            "execution_mode": "shadow_qualification",
            "action_type": "artifact_read",
            "target": target,
            "parameters": {},
        }
        decision = gateway.evaluate_request(request)
        receipt = executor.execute_artifact_read(request, decision, output_root)
        receipts[kind] = receipt
        request_path = output_root / "requests" / f"{kind}.request.json"
        decision_path = output_root / "decisions" / f"{kind}.decision.json"
        receipt_path = output_root / "receipts" / f"{kind}.receipt.json"
        file_manifest[str(request_path.relative_to(output_root)).replace("\\", "/")] = _write_new(request_path, request)
        file_manifest[str(decision_path.relative_to(output_root)).replace("\\", "/")] = _write_new(decision_path, decision)
        file_manifest[str(receipt_path.relative_to(output_root)).replace("\\", "/")] = _write_new(receipt_path, receipt)

    bundle = {
        "schema_version": "wave64.aqa.workflow_input_receipt_bundle.v1",
        "bundle_id": "0" * 64,
        "job_id": JOB_ID,
        "authority_binding_sha256": contract["contract_id"],
        "receipts": receipts,
    }
    bundle["bundle_id"] = validator.content_hash(bundle)
    validation = validator.validate_workflow(
        graph,
        info,
        contract,
        models,
        input_receipt_bundle=bundle,
        input_raw_bytes=raw_inputs,
    )
    bundle_path = output_root / "input_receipt_bundle.json"
    validation_path = output_root / "workflow_validation.json"
    file_manifest["input_receipt_bundle.json"] = _write_new(bundle_path, bundle)
    file_manifest["workflow_validation.json"] = _write_new(validation_path, validation)
    evidence = {
        "schema_version": "wave64.aqa.workflow_receipt_shadow_evidence.v1",
        "program_id": "W64-AQA",
        "tracker_id": "W64-AQA-010",
        "observed_at_utc": observed_at,
        "source_head": source_head,
        "job_id": JOB_ID,
        "contract_id": contract["contract_id"],
        "input_receipt_bundle_id": bundle["bundle_id"],
        "workflow_validation_id": validation["validation_id"],
        "input_binding_disposition": validation["input_binding_disposition"],
        "validation_disposition": validation["disposition"],
        "sandbox_execution_performed": validation["sandbox_execution_performed"],
        "receipt_count": len(receipts),
        "file_manifest_sha256": dict(sorted(file_manifest.items())),
        "runtime_claims": {
            "runpod_contacted": False,
            "gpu_used": False,
            "comfyui_execution_performed": False,
            "model_inference_performed": False,
            "candidate_write_performed": False,
            "product_promotion_granted": False,
        },
        "disposition": "PASS_RECEIPT_BOUND_STATIC_WORKFLOW_INSPECTION_ONLY",
        "remaining_unqualified": [
            "workflow_inspect_tool_action",
            "validator_run_tool_action",
            "typed_patch_sandbox_execution",
            "object_info_runtime_read",
            "shadow_generation_submit",
            "coder_proposal_authority",
        ],
    }
    _write_new(output_root / "evidence.json", evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    try:
        evidence = produce(args.output_root, args.source_head, args.observed_at)
        sys.stdout.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    except (ShadowProducerError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
