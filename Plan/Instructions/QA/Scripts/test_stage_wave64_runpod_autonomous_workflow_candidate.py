from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
STAGER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/stage_wave64_runpod_autonomous_workflow_candidate.py"
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_workflow_receipt_shadow.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture(tmp_path: Path) -> tuple[Path, dict, dict, bytes]:
    sandbox = tmp_path / "sandbox"
    load(PRODUCER_PATH, "w64_candidate_fixture_producer").produce(
        sandbox, "a" * 40, "2026-07-21T23:40:00Z"
    )
    job_id = "W64-AQA-JOB-workflow-receipt-shadow"
    job = sandbox / "jobs" / job_id
    (job / "proposals").mkdir()
    (job / "candidates").mkdir()
    shutil.copy2(sandbox / "input_receipt_bundle.json", job / "inputs" / "input_receipt_bundle.json")
    workflow_path = job / "inputs" / "workflow.json"
    workflow_raw = workflow_path.read_bytes()
    workflow = json.loads(workflow_raw)
    contract = json.loads((job / "inputs" / "contract.json").read_text(encoding="utf-8"))
    patch = {
        "schema_version": "wave64.aqa.workflow_patch.v1",
        "patch_id": "W64-AQA-PATCH-candidate-staging-test",
        "base_workflow_sha256": load(STAGER_PATH, "w64_hash_helper")._load_component(
            load(STAGER_PATH, "w64_stager_helper").VALIDATOR_PATH, "w64_validator_hash_helper"
        ).content_hash(workflow),
        "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
        "operations": [{
            "operation": "replace_bounded_numeric",
            "node_id": "2",
            "input_name": "cfg",
            "expected_old_value": 7.0,
            "new_value": 6.5,
        }],
    }
    write_json(job / "proposals" / "workflow.patch.json", patch)
    request = {
        "schema_version": "wave64.aqa.tool_gateway_request.v1",
        "request_id": "W64-AQA-TOOL-candidate-write-test",
        "job_id": job_id,
        "actor_role_id": "W64-AQA-ROLE-CONTROLLER",
        "authority_binding_sha256": contract["contract_id"],
        "execution_mode": "shadow_qualification",
        "action_type": "candidate_write",
        "target": f"jobs/{job_id}/candidates/workflow.candidate.json",
        "parameters": {},
    }
    decision = load(GATEWAY_PATH, "w64_candidate_fixture_gateway").evaluate_request(request)
    return sandbox, request, decision, workflow_raw


def test_exact_candidate_write_is_immutable_copy_on_write(tmp_path: Path) -> None:
    module = load(STAGER_PATH, "w64_candidate_success")
    sandbox, request, decision, workflow_raw = fixture(tmp_path)
    receipt = module.stage_candidate(request, decision, sandbox)
    job = sandbox / "jobs" / request["job_id"]
    candidate = json.loads((job / "candidates" / "workflow.candidate.json").read_text(encoding="utf-8"))
    assert candidate["2"]["inputs"]["cfg"] == 6.5
    assert (job / "inputs" / "workflow.json").read_bytes() == workflow_raw
    assert receipt["disposition"] == "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGED"
    assert receipt["candidate_write_performed"] is True
    assert receipt["base_input_write_performed"] is False
    assert receipt["overwrite_performed"] is False
    assert receipt["comfyui_execution_performed"] is False
    assert receipt["model_inference_performed"] is False
    assert receipt["network_used"] is False


def test_overwrite_and_nonexact_target_fail_closed(tmp_path: Path) -> None:
    module = load(STAGER_PATH, "w64_candidate_scope")
    gateway = load(GATEWAY_PATH, "w64_candidate_scope_gateway")
    sandbox, request, decision, _ = fixture(tmp_path)
    module.stage_candidate(request, decision, sandbox)
    with pytest.raises(module.CandidateStagingError, match="ALREADY_EXISTS"):
        module.stage_candidate(request, decision, sandbox)
    alternate = copy.deepcopy(request)
    alternate["target"] = f"jobs/{request['job_id']}/candidates/alternate.json"
    with pytest.raises(module.CandidateStagingError, match="TARGET_NOT_QUALIFIED"):
        module.stage_candidate(alternate, gateway.evaluate_request(alternate), sandbox)


def test_production_parameters_policy_weakening_and_elapsed_fail_closed(tmp_path: Path, monkeypatch) -> None:
    module = load(STAGER_PATH, "w64_candidate_controls")
    gateway = load(GATEWAY_PATH, "w64_candidate_controls_gateway")
    sandbox, request, decision, _ = fixture(tmp_path)
    production = copy.deepcopy(request)
    production["execution_mode"] = "production_release"
    with pytest.raises(module.CandidateStagingError, match="EXECUTION_MODE_NOT_QUALIFIED"):
        module.stage_candidate(production, gateway.evaluate_request(production), sandbox)
    parameters = copy.deepcopy(request)
    parameters["parameters"] = {"overwrite": False}
    with pytest.raises(module.CandidateStagingError, match="PARAMETERS_MUST_BE_EMPTY"):
        module.stage_candidate(parameters, gateway.evaluate_request(parameters), sandbox)
    weakened = json.loads(module.STAGER_POLICY_PATH.read_text(encoding="utf-8"))
    weakened["overwrite_allowed"] = True
    with pytest.raises(module.CandidateStagingError, match="changed or weakened"):
        module.stage_candidate(request, decision, sandbox, stager_policy=weakened)
    ticks = iter([0.0, 6.0])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    with pytest.raises(module.CandidateStagingError, match="TIME_LIMIT"):
        module.stage_candidate(request, decision, sandbox)


def test_invalid_typed_patch_and_reparse_root_do_not_publish(tmp_path: Path, monkeypatch) -> None:
    module = load(STAGER_PATH, "w64_candidate_invalid")
    sandbox, request, decision, _ = fixture(tmp_path)
    patch_path = sandbox / "jobs" / request["job_id"] / "proposals" / "workflow.patch.json"
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    patch["operations"][0]["new_value"] = 31.0
    write_json(patch_path, patch)
    with pytest.raises(module.CandidateStagingError, match="STATIC_VALIDATION_FAILED"):
        module.stage_candidate(request, decision, sandbox)
    assert not (sandbox / request["target"]).exists()
    monkeypatch.setattr(module, "_is_reparse", lambda value: True)
    with pytest.raises(module.CandidateStagingError, match="ROOT_NOT_PLAIN"):
        module.stage_candidate(request, decision, sandbox)


def test_publish_crash_and_source_race_leave_no_candidate(tmp_path: Path, monkeypatch) -> None:
    module = load(STAGER_PATH, "w64_candidate_faults")
    sandbox, request, decision, workflow_raw = fixture(tmp_path)
    candidate = sandbox / request["target"]
    original_link = os.link
    monkeypatch.setattr(os, "link", lambda source, destination: (_ for _ in ()).throw(OSError("injected")))
    with pytest.raises(OSError, match="injected"):
        module.stage_candidate(request, decision, sandbox)
    assert not candidate.exists()
    workflow_path = sandbox / "jobs" / request["job_id"] / "inputs" / "workflow.json"

    def mutate_then_link(source, destination):
        workflow_path.write_bytes(workflow_raw + b" ")
        return original_link(source, destination)

    monkeypatch.setattr(os, "link", mutate_then_link)
    with pytest.raises(module.CandidateStagingError, match="CHANGED_DURING_PUBLISH"):
        module.stage_candidate(request, decision, sandbox)
    assert not candidate.exists()
