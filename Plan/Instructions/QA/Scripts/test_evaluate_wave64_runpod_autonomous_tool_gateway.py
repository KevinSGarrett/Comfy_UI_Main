from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"


def load_gateway():
    spec = importlib.util.spec_from_file_location("w64_aqa_tool_gateway", GATEWAY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(
    *, action: str = "artifact_read", target: str = "jobs/W64-AQA-JOB-test/inputs/input.png",
    role: str = "W64-AQA-ROLE-WORKFLOW-ENGINEER", mode: str = "shadow_qualification",
    parameters: dict | None = None,
) -> dict:
    return {
        "schema_version": "wave64.aqa.tool_gateway_request.v1",
        "request_id": "W64-AQA-TOOL-test-001",
        "job_id": "W64-AQA-JOB-test",
        "actor_role_id": role,
        "authority_binding_sha256": "a" * 64,
        "execution_mode": mode,
        "action_type": action,
        "target": target,
        "parameters": parameters or {},
    }


def test_exact_scoped_read_is_deterministically_admitted_without_execution() -> None:
    module = load_gateway()
    first = module.evaluate_request(request())
    second = module.evaluate_request(request())
    assert first == second
    assert first["admission_disposition"] == "ADMIT_FOR_SEPARATE_EXECUTOR"
    assert first["execution_performed"] is False
    assert first["reason_codes"] == ["ADMITTED_BY_EXACT_ACTION_ROLE_TARGET_POLICY"]


@pytest.mark.parametrize("target", [
    "jobs/W64-AQA-JOB-test/inputs/../secret.txt",
    "C:/Comfy_UI_Main/.env",
    "/workspace/.env",
    "jobs/W64-AQA-JOB-other/inputs/input.png",
    "jobs\\W64-AQA-JOB-test\\inputs\\input.png",
])
def test_path_traversal_absolute_cross_job_and_host_paths_are_denied(target: str) -> None:
    module = load_gateway()
    result = module.evaluate_request(request(target=target))
    assert result["admission_disposition"] == "DENY"


@pytest.mark.parametrize("action", [
    "shell", "git", "cloud", "tracker_write", "promotion", "secret_read",
    "arbitrary_network", "package_install", "model_download", "credential_use", "invented_tool",
])
def test_forbidden_and_unknown_actions_are_denied_with_evidence(action: str) -> None:
    module = load_gateway()
    result = module.evaluate_request(request(action=action, target="anything"))
    assert result["admission_disposition"] == "DENY"
    assert "ACTION_NOT_ALLOWLISTED" in result["reason_codes"]


def test_secret_keys_tokens_uris_and_host_paths_in_parameters_are_denied_without_echoing_values() -> None:
    module = load_gateway()
    secret_value = "ghp_" + "A" * 32
    result = module.evaluate_request(request(parameters={
        "api_key": secret_value,
        "callback": "https://example.invalid/collect",
        "local": "C:/Users/example/.aws/credentials",
    }))
    assert result["admission_disposition"] == "DENY"
    assert "SECRET_OR_CREDENTIAL_MATERIAL_DENIED" in result["reason_codes"]
    assert "PARAMETER_URI_OR_HOST_PATH_DENIED" in result["reason_codes"]
    assert secret_value not in str(result)
    assert set(result["secret_scan_categories"]) == {"forbidden_parameter_key", "github_token"}


def test_workflow_engineer_cannot_write_candidate_or_submit_generation() -> None:
    module = load_gateway()
    write = module.evaluate_request(request(
        action="candidate_write",
        target="jobs/W64-AQA-JOB-test/candidates/workflow.json",
    ))
    submit = module.evaluate_request(request(
        action="shadow_generation_submit",
        target="comfyui.prompt",
    ))
    assert "ROLE_NOT_AUTHORIZED_FOR_ACTION" in write["reason_codes"]
    assert "ROLE_NOT_AUTHORIZED_FOR_ACTION" in submit["reason_codes"]


def test_controller_shadow_submit_is_admitted_but_production_submit_is_denied() -> None:
    module = load_gateway()
    shadow = request(
        action="shadow_generation_submit", target="comfyui.prompt",
        role="W64-AQA-ROLE-CONTROLLER",
    )
    assert module.evaluate_request(shadow)["admission_disposition"] == "ADMIT_FOR_SEPARATE_EXECUTOR"
    production = {**shadow, "execution_mode": "production_release"}
    result = module.evaluate_request(production)
    assert result["admission_disposition"] == "DENY"
    assert "ACTION_NOT_ALLOWED_IN_PRODUCTION_MODE" in result["reason_codes"]


def test_empty_authority_binding_and_invalid_schema_fail_closed() -> None:
    module = load_gateway()
    empty = request()
    empty["authority_binding_sha256"] = "0" * 64
    assert "EMPTY_AUTHORITY_BINDING_DENIED" in module.evaluate_request(empty)["reason_codes"]
    invalid = request()
    invalid["parameters"] = "not-an-object"
    with pytest.raises(module.GatewayError, match="schema validation failed"):
        module.evaluate_request(invalid)
