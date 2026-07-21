from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py"
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_request(*, action: str = "artifact_read", target: str | None = None, parameters=None) -> dict:
    job_id = "W64-AQA-JOB-executor-test"
    return {
        "schema_version": "wave64.aqa.tool_gateway_request.v1",
        "request_id": "W64-AQA-TOOL-executor-test-001",
        "job_id": job_id,
        "actor_role_id": "W64-AQA-ROLE-DETERMINISTIC",
        "authority_binding_sha256": "a" * 64,
        "execution_mode": "shadow_qualification",
        "action_type": action,
        "target": target or f"jobs/{job_id}/evidence/artifact.json",
        "parameters": {} if parameters is None else parameters,
    }


def admitted(request: dict) -> dict:
    return load(GATEWAY_PATH, "w64_gateway_for_executor_test").evaluate_request(request)


def write_target(root: Path, request: dict, content: bytes = b'{"safe":true}\n') -> Path:
    path = root.joinpath(*request["target"].split("/"))
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    return path


def test_admitted_artifact_read_returns_digest_without_content_or_writes(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_success")
    request = make_request()
    target = write_target(tmp_path, request)
    before = target.read_bytes()
    receipt = module.execute_artifact_read(request, admitted(request), tmp_path)
    assert receipt["disposition"] == "PASS_READ_ONLY_ARTIFACT_DIGEST"
    assert receipt["artifact_sha256"] == "7eeccb134911ebae5c9ab93e29604540babeda8e0f5a634d92fc0a1d3dc45c52"
    assert receipt["byte_count"] == len(before)
    assert receipt["content_exposed"] is False
    assert receipt["target_write_performed"] is False
    assert receipt["network_used"] is False
    assert target.read_bytes() == before
    assert "safe" not in json.dumps(receipt)


def test_tampered_decision_is_rejected(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_tamper")
    request = make_request()
    write_target(tmp_path, request)
    decision = admitted(request)
    decision["normalized_target"] = decision["normalized_target"].replace("artifact", "other")
    with pytest.raises(module.ExecutorError, match="DECISION_RECOMPUTE_MISMATCH"):
        module.execute_artifact_read(request, decision, tmp_path)


def test_denied_decision_and_unqualified_write_action_are_rejected(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_denied")
    request = make_request(action="proposal_write")
    decision = admitted(request)
    with pytest.raises(module.ExecutorError, match="DECISION_NOT_ADMITTED|ACTION_NOT_QUALIFIED"):
        module.execute_artifact_read(request, decision, tmp_path)


def test_nonempty_parameters_are_rejected_even_when_gateway_admits(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_parameters")
    request = make_request(parameters={"label": "safe"})
    write_target(tmp_path, request)
    assert admitted(request)["admission_disposition"] == "ADMIT_FOR_SEPARATE_EXECUTOR"
    with pytest.raises(module.ExecutorError, match="PARAMETERS_MUST_BE_EMPTY"):
        module.execute_artifact_read(request, admitted(request), tmp_path)


@pytest.mark.parametrize("name", [".env", ".env.local", "api_token.json", "credentials.json", "private-key.pem", "client.p12"])
def test_sensitive_names_and_suffixes_are_denied_before_read(tmp_path: Path, name: str) -> None:
    module = load(EXECUTOR_PATH, f"w64_executor_sensitive_{name.replace('.', '_')}")
    request = make_request(target=f"jobs/W64-AQA-JOB-executor-test/evidence/{name}")
    write_target(tmp_path, request)
    with pytest.raises(module.ExecutorError, match="SENSITIVE_PATH"):
        module.execute_artifact_read(request, admitted(request), tmp_path)


@pytest.mark.parametrize("content", [
    b"AKIA" + b"A" * 16,
    b"ghp_" + b"A" * 32,
    b"-----BEGIN " + b"PRIVATE KEY-----\nnot-real\n",
    b"Bearer " + b"a" * 24,
])
def test_secret_like_content_is_denied_without_echoing_value(tmp_path: Path, content: bytes) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_secret_content")
    request = make_request()
    write_target(tmp_path, request, content)
    with pytest.raises(module.ExecutorError) as captured:
        module.execute_artifact_read(request, admitted(request), tmp_path)
    assert "SECRET_LIKE_CONTENT_DENIED" in str(captured.value)
    assert content.decode(errors="ignore") not in str(captured.value)


def test_size_limit_is_enforced_before_content_is_returned(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_size")
    request = make_request()
    write_target(tmp_path, request, b"12345")
    policy = json.loads(module.EXECUTOR_POLICY_PATH.read_text(encoding="utf-8"))
    policy["artifact_read"]["max_bytes"] = 4
    with pytest.raises(module.ExecutorError, match="SIZE_LIMIT"):
        module.execute_artifact_read(request, admitted(request), tmp_path, executor_policy=policy)


def test_elapsed_time_limit_fails_closed(tmp_path: Path, monkeypatch) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_time")
    request = make_request()
    write_target(tmp_path, request)
    ticks = iter([0.0, 6.0])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    with pytest.raises(module.ExecutorError, match="TIME_LIMIT"):
        module.execute_artifact_read(request, admitted(request), tmp_path)


def test_toctou_content_change_during_open_is_rejected(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_toctou")
    request = make_request()
    target = write_target(tmp_path, request, b'{"safe":true}\n')

    def mutate(_: Path) -> None:
        target.write_bytes(b'{"safe":false}\n')

    with pytest.raises(module.ExecutorError, match="FILE_IDENTITY_CHANGED_DURING_READ"):
        module.execute_artifact_read(request, admitted(request), tmp_path, after_open_hook=mutate)


def test_symlink_target_is_rejected_when_supported(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_symlink")
    request = make_request()
    target = tmp_path.joinpath(*request["target"].split("/"))
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    with pytest.raises(module.ExecutorError, match="SYMLINK_OR_REPARSE_POINT_DENIED"):
        module.execute_artifact_read(request, admitted(request), tmp_path)


def test_windows_reparse_attribute_is_classified_without_platform_dependency() -> None:
    module = load(EXECUTOR_PATH, "w64_executor_reparse")
    fake = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
    assert module._is_reparse(fake)


@pytest.mark.parametrize("target", [
    "https://example.invalid/artifact.json",
    "C:/Comfy_UI_Main/.env",
    "jobs/W64-AQA-JOB-executor-test/evidence/../../secret.json",
    "jobs/W64-AQA-JOB-other/evidence/artifact.json",
])
def test_network_absolute_traversal_and_cross_job_targets_never_reach_executor(tmp_path: Path, target: str) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_boundary")
    request = make_request(target=target)
    decision = admitted(request)
    assert decision["admission_disposition"] == "DENY"
    with pytest.raises(module.ExecutorError, match="DECISION_NOT_ADMITTED"):
        module.execute_artifact_read(request, decision, tmp_path)


def test_atomic_receipt_publish_never_overwrites_and_cleans_temporary(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_publish")
    output = tmp_path / "receipt.json"
    module._publish_immutable(output, "one\n")
    assert output.read_text(encoding="utf-8") == "one\n"
    with pytest.raises(module.ExecutorError, match="already exists"):
        module._publish_immutable(output, "two\n")
    assert output.read_text(encoding="utf-8") == "one\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_publish_crash_before_atomic_link_leaves_no_final_receipt(tmp_path: Path, monkeypatch) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_crash")
    output = tmp_path / "receipt.json"

    def crash(_source, _destination):
        raise OSError("injected crash")

    monkeypatch.setattr(module.os, "link", crash)
    with pytest.raises(OSError, match="injected crash"):
        module._publish_immutable(output, "receipt\n")
    assert not output.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_executor_policy_cannot_expand_actions_or_weaken_controls(tmp_path: Path) -> None:
    module = load(EXECUTOR_PATH, "w64_executor_policy")
    request = make_request()
    write_target(tmp_path, request)
    base = json.loads(module.EXECUTOR_POLICY_PATH.read_text(encoding="utf-8"))
    expanded = json.loads(json.dumps(base))
    expanded["qualified_actions"].append("proposal_write")
    with pytest.raises(module.ExecutorError, match="artifact_read only"):
        module.execute_artifact_read(request, admitted(request), tmp_path, executor_policy=expanded)
    weakened = json.loads(json.dumps(base))
    weakened["artifact_read"]["network_allowed"] = True
    with pytest.raises(module.ExecutorError, match="weakens"):
        module.execute_artifact_read(request, admitted(request), tmp_path, executor_policy=weakened)
