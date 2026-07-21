from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_strict_model_runtime_canary.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_aqa_strict_model_canary", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_probe(module) -> dict:
    return {
        "observed_at": "2026-07-21T22:00:00Z",
        "queue_running": 0,
        "queue_pending": 0,
        "comfyui_system_stats_healthy": True,
        "gpu": {
            "name": "NVIDIA RTX 6000 Ada Generation",
            "total_mib": 49140,
            "used_mib": 1000,
            "free_mib": 48140,
            "utilization_percent": 0,
        },
        "overlay": {"used_percent": 79.0},
        "workspace": {"used_percent": 74.0},
        "installed_models": [{"name": module.MODEL_ID, "digest": module.EXPECTED_DIGEST}],
        "loaded_models": [],
        "active_foreign_workloads": [],
    }


def remote_fixture(module, *, pre_changes=None, response=None):
    pre = safe_probe(module)
    for key, value in (pre_changes or {}).items():
        pre[key] = value
    post = copy.deepcopy(pre)
    post["observed_at"] = "2026-07-21T22:01:00Z"
    calls = []

    def remote(host, port, request, *, timeout_seconds):
        calls.append(request["action"])
        if request["action"] == "probe":
            return copy.deepcopy(pre if calls.count("probe") == 1 else post)
        if request["action"] == "infer":
            return copy.deepcopy(response or {
                "elapsed_seconds": 2.0,
                "done": True,
                "done_reason": "stop",
                "response": '{"decision":"REFUSE","reason_code":"MISSING_MEDIA"}',
                "total_duration_ns": 2_000_000_000,
                "load_duration_ns": 1_000_000_000,
                "prompt_eval_count": 24,
                "eval_count": 12,
            })
        if request["action"] == "unload":
            return {"done": True, "done_reason": "unload"}
        raise AssertionError(request)

    return remote, calls


def test_safe_canary_loads_refuses_unloads_and_grants_no_product_authority() -> None:
    module = load_producer()
    remote, calls = remote_fixture(module)
    result = module.run_canary(
        host="root@example.invalid",
        port=22,
        pod_id="pod-test",
        network_volume_id="volume-test",
        hourly_compute_usd=0.77,
        remote=remote,
    )
    assert calls == ["probe", "infer", "unload", "probe"]
    assert result["canary_disposition"] == "PASS_MODEL_LOAD_REFUSAL_AND_UNLOAD"
    assert result["inference_receipt"]["parsed_response"] == {
        "decision": "REFUSE",
        "reason_code": "MISSING_MEDIA",
    }
    assert result["final_controller_state"]["state"] == "IDLE"
    assert result["product_approval_granted"] is False
    assert result["runtime"]["remote_endpoint_retained"] is False


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"queue_pending": 1}, "COMFYUI_QUEUE_NOT_IDLE"),
        ({"loaded_models": ["qwen2.5vl:7b"]}, "UNOWNED_OLLAMA_RESIDENCY_PRESENT"),
        (
            {
                "active_foreign_workloads": [
                    {"pid": 123, "workload_class": "maskfactory_strict_visual_burst"}
                ]
            },
            "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT",
        ),
        ({"overlay": {"used_percent": 85.0}}, "OVERLAY_PRESSURE"),
        ({"gpu": {"free_mib": 29000}}, "INSUFFICIENT_FREE_VRAM"),
        ({"installed_models": []}, "STRICT_MODEL_DIGEST_ABSENT_OR_CHANGED"),
    ],
)
def test_unsafe_preflight_fails_before_model_load(changes: dict, match: str) -> None:
    module = load_producer()
    remote, calls = remote_fixture(module, pre_changes=changes)
    with pytest.raises(module.ModelCanaryError, match=match):
        module.run_canary(
            host="root@example.invalid",
            port=22,
            pod_id="pod-test",
            network_volume_id="volume-test",
            hourly_compute_usd=0.77,
            remote=remote,
        )
    assert calls == ["probe"]


def test_admission_snapshot_retains_typed_blockers_without_action() -> None:
    module = load_producer()
    remote, calls = remote_fixture(
        module,
        pre_changes={
            "active_foreign_workloads": [
                {"pid": 123, "workload_class": "maskfactory_strict_visual_burst"}
            ],
            "loaded_models": ["qwen2.5vl:7b"],
            "gpu": {"free_mib": 20000},
        },
    )
    result = module.capture_admission_snapshot(
        host="root@example.invalid",
        port=22,
        pod_id="pod-test",
        network_volume_id="volume-test",
        hourly_compute_usd=0.77,
        remote=remote,
    )
    assert calls == ["probe"]
    assert result["admission_disposition"] == "BLOCKED_NO_ACTION"
    assert result["blocker_codes"] == [
        "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT",
        "INSUFFICIENT_FREE_VRAM",
        "UNOWNED_OLLAMA_RESIDENCY_PRESENT",
    ]
    assert result["resource_mutations"] == []
    assert result["inference_executed"] is False


def test_invalid_refusal_json_still_requests_owned_model_unload() -> None:
    module = load_producer()
    remote, calls = remote_fixture(
        module,
        response={
            "elapsed_seconds": 2.0,
            "done": True,
            "done_reason": "stop",
            "response": '{"decision":"PASS"}',
        },
    )
    with pytest.raises(module.ModelCanaryError, match="exact refusal contract"):
        module.run_canary(
            host="root@example.invalid",
            port=22,
            pod_id="pod-test",
            network_volume_id="volume-test",
            hourly_compute_usd=0.77,
            remote=remote,
        )
    assert calls == ["probe", "infer", "unload"]
