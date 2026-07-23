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


def lease() -> dict:
    return {
        "valid": True,
        "project": "comfyui_main",
        "profile": "comfyui_model_qualification",
        "lease_mode": "exclusive",
        "reserved_peak_gib": 8,
        "lease_id": "lease-test",
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
    result = module.run_canary(admission, lease(), remote=remote)
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
    with pytest.raises(module.FastTriageCanaryError, match="held-out remains sealed"):
        module.run_canary(admission, lease(), remote=remote)
    assert [item[0] for item in calls].count("infer") == 8
    assert [item[0] for item in calls][-1] == "unload"


def test_unusable_shared_lease_blocks_before_remote_action() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    remote, calls = remote_fixture(admission)
    invalid = lease()
    invalid["reserved_peak_gib"] = 4
    with pytest.raises(module.FastTriageCanaryError, match="lease is not usable"):
        module.run_canary(admission, invalid, remote=remote)
    assert calls == []


def test_lease_receipt_must_match_live_coordinator_validation() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    receipt = lease()
    live = lease()
    live["lease_id"] = "different-live-lease"
    with pytest.raises(
        module.FastTriageCanaryError,
        match="does not match live coordinator field: lease_id",
    ):
        module.bind_live_lease_receipt(
            admission,
            receipt,
            validator=lambda **_: live,
        )


def test_live_lease_binding_rejects_token_bearing_receipt() -> None:
    module = load_module()
    admission = module.load_admission(ADMISSION)
    receipt = lease()
    receipt["lease_token"] = "must-not-be-retained"
    with pytest.raises(module.FastTriageCanaryError, match="must not contain"):
        module.bind_live_lease_receipt(
            admission,
            receipt,
            validator=lambda **_: lease(),
        )


def test_heartbeat_guard_fails_closed_after_sender_error() -> None:
    module = load_module()
    calls = []

    def sender(phase: str) -> None:
        calls.append(phase)
        if len(calls) > 1:
            raise module.FastTriageCanaryError("heartbeat rejected")

    with pytest.raises(
        module.FastTriageCanaryError,
        match="heartbeat guard failed",
    ):
        with module.CoordinatorHeartbeatGuard(
            interval_seconds=0.01,
            sender=sender,
        ):
            import time

            time.sleep(0.05)
    assert calls[0] == "fast_triage_refusal_canary"
