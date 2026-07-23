from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_qwen3vl4_fast_triage_refusal_canary.py"
)
ADMISSION = (
    ROOT / "Plan/10_REGISTRIES/wave64_qwen3vl4_fast_triage_refusal_admission.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("w64_fast_triage_refusal", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_probe(admission: dict) -> dict:
    return {
        "queue_running": 0,
        "queue_pending": 0,
        "ollama_version": admission["execution"]["ollama_version"],
        "installed_models": [
            {
                "name": admission["selected_package"]["model_id"],
                "digest": admission["selected_package"]["digest"],
            }
        ],
        "loaded_models": [],
        "gpu": {
            "name": "NVIDIA RTX 6000 Ada Generation",
            "used_mib": 648,
            "free_mib": 47993,
            "utilization_percent": 0,
        },
        "ollama_rss_mib": 100,
        "overlay_used_percent": 55,
    }


def direct_execution() -> dict:
    return {
        "valid": True,
        "project": "comfyui_main",
        "profile": "comfyui_model_qualification",
        "lease_mode": "direct",
        "governance_disabled": True,
    }


def remote_fixture(admission: dict, *, bad_case: str | None = None):
    pre = safe_probe(admission)
    post = copy.deepcopy(pre)
    calls = []

    def remote(action: str, timeout_seconds: int, **kwargs):
        calls.append((action, kwargs.get("reason_code")))
        if action == "probe":
            return copy.deepcopy(
                pre if sum(item[0] == "probe" for item in calls) == 1 else post
            )
        if action == "infer":
            response = {"decision": "REFUSE", "reason_code": kwargs["reason_code"]}
            if bad_case and bad_case in kwargs["prompt"]:
                response = {"decision": "PASS", "reason_code": kwargs["reason_code"]}
            return {
                "elapsed_seconds": 1.0,
                "response": json.dumps(response),
                "done": True,
                "done_reason": "stop",
                "gpu_after": {"used_mib": 3500},
                "ollama_rss_mib": 500,
            }
        if action == "unload":
            return {"done": True, "done_reason": "unload"}
        raise AssertionError(action)

    return remote, calls


def test_admission_is_hash_bound_and_excludes_unlicensed_llava() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    assert admission["selected_package"]["package_id"] == "W64-AQA-PKG-QWEN3VL4"
    assert admission["excluded_packages"] == [
        {
            "package_id": "W64-AQA-PKG-LLAVA13",
            "reason": "LLAMA2_COMMUNITY_LICENSE_REVIEW_REQUIRED_NOT_ACCEPTED",
        }
    ]
    assert admission["authority"]["triage_crop_capability"] is False


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"queue_pending": 1}, "COMFYUI_QUEUE_NOT_IDLE"),
        ({"loaded_models": ["foreign:model"]}, "UNOWNED_OLLAMA_RESIDENCY_PRESENT"),
        ({"ollama_version": "drifted"}, "OLLAMA_RUNTIME_VERSION_DRIFT"),
        ({"overlay_used_percent": 85}, "OVERLAY_PRESSURE"),
        ({"gpu": {"free_mib": 4096}}, "INSUFFICIENT_FREE_VRAM"),
        ({"installed_models": []}, "SELECTED_MODEL_DIGEST_ABSENT_OR_CHANGED"),
    ],
)
def test_preflight_fails_closed(change: dict, reason: str) -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    snapshot = safe_probe(admission)
    snapshot.update(change)
    assert reason in module.preflight_reasons(admission, snapshot)


def test_calibration_twice_then_held_out_once_and_no_operational_authority() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    remote, calls = remote_fixture(admission)
    result = module.run_canary(admission, direct_execution(), remote=remote)
    assert [item[0] for item in calls].count("infer") == 13
    assert (
        len(
            [
                item
                for item in result["qualification_report"]["fixtures"]
                if item["partition"] == "calibration"
            ]
        )
        == 4
    )
    assert all(
        len(item["runs"]) == 2
        for item in result["qualification_report"]["fixtures"][:4]
    )
    assert all(
        len(item["runs"]) == 1
        for item in result["qualification_report"]["fixtures"][4:]
    )
    assert (
        result["qualification_report"]["authority_scope"]
        == "REFUSAL_DISCIPLINE_SCOPE_ONLY"
    )
    assert result["authority"]["triage_crop_capability"] is False


def test_failed_calibration_keeps_held_out_sealed_and_unloads() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    remote, calls = remote_fixture(
        admission, bad_case="known_good_deterministic_image_decode"
    )
    result = module.run_canary(admission, direct_execution(), remote=remote)
    assert result["disposition"] == "FAIL_CALIBRATION_HELD_OUT_SEALED"
    assert [item[0] for item in calls].count("infer") == 8
    assert [item[0] for item in calls][-2:] == ["unload", "probe"]
    assert all(
        fixture["partition"] == "calibration"
        for fixture in result["qualification_report"]["fixtures"]
    )


def test_direct_execution_requires_project_and_profile_before_remote_action() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    remote, calls = remote_fixture(admission)
    invalid = direct_execution()
    invalid["profile"] = "wrong-profile"
    with pytest.raises(module.FastTriageCanaryError, match="not usable"):
        module.run_canary(admission, invalid, remote=remote)
    assert calls == []


def test_direct_execution_ignores_stale_coordinator_receipt_profile() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    receipt = direct_execution()
    live = direct_execution()
    live["profile"] = "wrong-profile"
    bound = module.bind_live_lease_receipt(
        admission,
        receipt,
        validator=lambda **_: live,
    )
    assert bound["governance_disabled"] is True


def test_direct_execution_does_not_require_or_inspect_tokens() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    receipt = direct_execution()
    receipt["lease_token"] = "ignored-by-direct-execution"
    assert module.bind_live_lease_receipt(
        admission,
        receipt,
        validator=lambda **_: direct_execution(),
    )["valid"] is True


def test_remote_request_binds_timeout_into_ssh_payload() -> None:
    module = load_module()
    request = module.remote_request(
        "infer",
        300,
        model="qwen3-vl:4b-instruct-q4_K_M",
        reason_code="OUT_OF_SCOPE_REFUSAL",
    )
    assert request == {
        "action": "infer",
        "timeout_seconds": 300,
        "model": "qwen3-vl:4b-instruct-q4_K_M",
        "reason_code": "OUT_OF_SCOPE_REFUSAL",
    }
    with pytest.raises(module.FastTriageCanaryError, match="timeout must be positive"):
        module.remote_request("probe", 0)


def test_runner_has_no_windows_coordinator_heartbeat_dependency() -> None:
    assert "shared_runpod_coordinator" not in SCRIPT.read_text(encoding="utf-8")
