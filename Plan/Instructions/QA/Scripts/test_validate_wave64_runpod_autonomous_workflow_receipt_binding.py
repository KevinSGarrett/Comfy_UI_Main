from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py"
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py"
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py"
INPUT_KINDS = ("workflow", "object_info", "contract", "model_inventory")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def object_info() -> dict:
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


def workflow() -> dict:
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


def inventory() -> dict:
    return {
        "schema_version": "wave64.aqa.model_inventory.v1",
        "eligible_model_names": ["base.safetensors"],
    }


def compile_contract(info: dict, graph: dict) -> dict:
    compiler = load(COMPILER_PATH, "w64_contract_for_receipt_binding")
    draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-workflow-receipt-test",
        "revision": 1,
        "created_at": "2026-07-21T23:00:00Z",
        "modality": "workflow",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{
            "output_id": "validation",
            "media_type": "application/json",
            "durable_relative_path": "aqa/jobs/workflow-receipt-test/validation.json",
        }],
        "quality_profile": {
            "profile_id": "workflow-receipt-binding-v1",
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
            "workflow_sha256": hashlib.sha256(
                json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "input_artifacts": [],
            "model_bindings": [{
                "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                "model_id": "deterministic-python-validator",
                "checkpoint_sha256": "b" * 64,
                "runtime_digest": "python-local-test",
                "qualification_state": "QUALIFIED",
            }],
            "calibration_ids": ["workflow-receipt-binding-test-v1"],
        },
        "workflow_spec": {
            "object_info_sha256": hashlib.sha256(
                json.dumps(info, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
            "sandbox_required": True,
            "regression_suite_id": "workflow-regression-v1",
        },
    }
    return compiler.compile_contract(draft)


def build_bound_inputs(tmp_path: Path) -> tuple[dict, dict, dict[str, bytes], dict[str, Path]]:
    validator = load(VALIDATOR_PATH, "w64_validator_bound_fixture")
    gateway = load(GATEWAY_PATH, "w64_gateway_bound_fixture")
    executor = load(EXECUTOR_PATH, "w64_executor_bound_fixture")
    info, graph, models = object_info(), workflow(), inventory()
    contract = compile_contract(info, graph)
    values = {
        "workflow": graph,
        "object_info": info,
        "contract": contract,
        "model_inventory": models,
    }
    raw_inputs: dict[str, bytes] = {}
    paths: dict[str, Path] = {}
    receipts: dict[str, dict] = {}
    for kind, value in values.items():
        target = f"jobs/{contract['job_id']}/inputs/{kind}.json"
        path = tmp_path.joinpath(*target.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        raw_inputs[kind] = raw
        paths[kind] = path
        request = {
            "schema_version": "wave64.aqa.tool_gateway_request.v1",
            "request_id": f"W64-AQA-TOOL-workflow-receipt-{kind}",
            "job_id": contract["job_id"],
            "actor_role_id": "W64-AQA-ROLE-DETERMINISTIC",
            "authority_binding_sha256": contract["contract_id"],
            "execution_mode": "shadow_qualification",
            "action_type": "artifact_read",
            "target": target,
            "parameters": {},
        }
        decision = gateway.evaluate_request(request)
        receipts[kind] = executor.execute_artifact_read(request, decision, tmp_path)
    bundle = {
        "schema_version": "wave64.aqa.workflow_input_receipt_bundle.v1",
        "bundle_id": "0" * 64,
        "job_id": contract["job_id"],
        "authority_binding_sha256": contract["contract_id"],
        "receipts": receipts,
    }
    bundle["bundle_id"] = validator.content_hash(bundle)
    return values, bundle, raw_inputs, paths


def test_all_four_executor_receipts_bind_static_workflow_validation(tmp_path: Path) -> None:
    module = load(VALIDATOR_PATH, "w64_validator_bound_pass")
    values, bundle, raw_inputs, _ = build_bound_inputs(tmp_path)
    result = module.validate_workflow(
        values["workflow"],
        values["object_info"],
        values["contract"],
        values["model_inventory"],
        input_receipt_bundle=bundle,
        input_raw_bytes=raw_inputs,
    )
    assert result["disposition"] == "PASS_STATIC_VALIDATION"
    assert result["input_binding_disposition"] == "PASS_EXECUTOR_RECEIPT_BOUND"
    assert set(result["input_executor_receipt_ids"]) == set(INPUT_KINDS)
    assert result["sandbox_execution_performed"] is False


@pytest.mark.parametrize("field", [
    "artifact_sha256",
    "normalized_target",
    "gateway_policy_sha256",
    "executor_policy_sha256",
    "authority_binding_sha256",
])
def test_tampered_executor_receipt_bindings_fail_closed(tmp_path: Path, field: str) -> None:
    module = load(VALIDATOR_PATH, f"w64_validator_tamper_{field}")
    values, bundle, raw_inputs, _ = build_bound_inputs(tmp_path)
    receipt = bundle["receipts"]["workflow"]
    receipt[field] = "f" * 64 if field != "normalized_target" else "jobs/other/inputs/workflow.json"
    bundle["bundle_id"] = "0" * 64
    bundle["bundle_id"] = module.content_hash(bundle)
    with pytest.raises(module.WorkflowValidationError, match="binding mismatch"):
        module.validate_workflow(
            values["workflow"], values["object_info"], values["contract"],
            values["model_inventory"], input_receipt_bundle=bundle, input_raw_bytes=raw_inputs,
        )


def test_bundle_identity_duplicate_receipts_and_raw_changes_fail_closed(tmp_path: Path) -> None:
    module = load(VALIDATOR_PATH, "w64_validator_bundle_negative")
    values, bundle, raw_inputs, _ = build_bound_inputs(tmp_path)
    broken = copy.deepcopy(bundle)
    broken["bundle_id"] = "f" * 64
    with pytest.raises(module.WorkflowValidationError, match="bundle identity"):
        module.validate_workflow(
            values["workflow"], values["object_info"], values["contract"],
            values["model_inventory"], input_receipt_bundle=broken, input_raw_bytes=raw_inputs,
        )
    changed = dict(raw_inputs)
    changed["workflow"] = changed["workflow"] + b" "
    with pytest.raises(module.WorkflowValidationError, match="artifact_sha256"):
        module.validate_workflow(
            values["workflow"], values["object_info"], values["contract"],
            values["model_inventory"], input_receipt_bundle=bundle, input_raw_bytes=changed,
        )
    duplicate = copy.deepcopy(bundle)
    duplicate["receipts"]["object_info"] = copy.deepcopy(duplicate["receipts"]["workflow"])
    duplicate["bundle_id"] = "0" * 64
    duplicate["bundle_id"] = module.content_hash(duplicate)
    with pytest.raises(module.WorkflowValidationError, match="object_info executor receipt normalized_target"):
        module.validate_workflow(
            values["workflow"], values["object_info"], values["contract"],
            values["model_inventory"], input_receipt_bundle=duplicate, input_raw_bytes=raw_inputs,
        )


def test_in_memory_object_cannot_diverge_from_receipt_bound_bytes(tmp_path: Path) -> None:
    module = load(VALIDATOR_PATH, "w64_validator_object_byte_divergence")
    values, bundle, raw_inputs, _ = build_bound_inputs(tmp_path)
    changed_workflow = copy.deepcopy(values["workflow"])
    changed_workflow["2"]["inputs"]["steps"] = 21
    with pytest.raises(module.WorkflowValidationError, match="parsed object does not match"):
        module.validate_workflow(
            changed_workflow,
            values["object_info"],
            values["contract"],
            values["model_inventory"],
            input_receipt_bundle=bundle,
            input_raw_bytes=raw_inputs,
        )


def test_cli_requires_receipt_bundle_and_accepts_bound_inputs(tmp_path: Path) -> None:
    values, bundle, _, paths = build_bound_inputs(tmp_path)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [
        sys.executable,
        str(VALIDATOR_PATH),
        str(paths["workflow"]),
        str(paths["object_info"]),
        str(paths["contract"]),
        str(paths["model_inventory"]),
    ]
    denied = subprocess.run(command, capture_output=True, text=True, check=False)
    assert denied.returncode == 1
    assert "requires --input-receipt-bundle" in denied.stderr
    accepted = subprocess.run(
        [*command, "--input-receipt-bundle", str(bundle_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stderr
    result = json.loads(accepted.stdout)
    assert result["input_binding_disposition"] == "PASS_EXECUTOR_RECEIPT_BOUND"
    assert result["disposition"] == "PASS_STATIC_VALIDATION"
