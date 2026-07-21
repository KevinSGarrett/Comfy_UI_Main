from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_phase_lease_runtime_canary.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_aqa_runtime_canary", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parameters() -> dict:
    return {
        "observed_at": "2026-07-21T22:00:00Z", "pod_id": "pod-test",
        "network_volume_id": "volume-test", "gpu_profile": "1x RTX 6000 Ada 48GB",
        "hourly_compute_usd": 0.77, "overlay_used_percent": 79,
        "workspace_used_percent": 74, "vram_total_mib": 49140,
        "vram_free_mib": 47993, "queue_running": 0, "queue_pending": 0,
        "strict_model_digest": "a" * 64, "strict_model_runtime": "ollama-0.32.1",
    }


def test_no_generation_canary_acquires_releases_and_verifies_hash_chain() -> None:
    module = load_producer()
    result = module.produce_canary(**parameters())
    assert result["canary_disposition"] == "PASS_ADMISSION_AND_RELEASE_NO_GENERATION"
    assert result["shadow_contract"]["promotion_disposition"] == "EVIDENCE_ONLY"
    assert result["final_controller_state"]["state"] == "IDLE"
    assert result["final_controller_state"]["lease"] is None
    assert [entry["event"] for entry in result["final_controller_state"]["journal"]][-3:] == ["LEASE_ACQUIRED", "LEASE_DRAINING", "LEASE_RELEASED"]
    assert result["strict_model_inventory"]["inference_executed"] is False
    assert result["resource_mutations"] == []


@pytest.mark.parametrize("changes,match", [
    ({"overlay_used_percent": 85}, "OVERLAY_PRESSURE"),
    ({"queue_running": 1}, "QUEUE_NOT_IDLE"),
    ({"vram_free_mib": 100}, "INSUFFICIENT_FREE_VRAM"),
    ({"strict_model_digest": "short"}, "full lowercase sha256"),
])
def test_invalid_or_unsafe_runtime_snapshot_fails_closed(changes: dict, match: str) -> None:
    module = load_producer()
    values = parameters()
    values.update(changes)
    with pytest.raises((module.CanaryError, RuntimeError), match=match):
        module.produce_canary(**values)
