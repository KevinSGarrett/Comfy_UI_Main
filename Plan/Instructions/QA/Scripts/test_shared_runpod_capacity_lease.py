from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/shared_runpod_capacity_lease.py"


def load_module():
    spec = importlib.util.spec_from_file_location("shared_runpod_capacity_lease", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_process_local_lease_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    for name in (
        "SHARED_RUNPOD_LEASE_ID",
        "SHARED_RUNPOD_LEASE_TOKEN",
        "SHARED_RUNPOD_LEASE_PROFILE",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(module.SharedRunPodLeaseError, match="GPU action requires"):
        module.validate_shared_runpod_lease()


def test_profile_mismatch_fails_before_coordinator_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    monkeypatch.setenv("SHARED_RUNPOD_LEASE_ID", "lease-test")
    monkeypatch.setenv("SHARED_RUNPOD_LEASE_TOKEN", "secret-test-token")
    monkeypatch.setenv("SHARED_RUNPOD_LEASE_PROFILE", "comfyui_qa_shadow")
    with pytest.raises(module.SharedRunPodLeaseError, match="profile mismatch"):
        module.validate_shared_runpod_lease(expected_profile="comfyui_model_qualification")


def test_valid_receipt_retains_no_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_module()
    coordinator = tmp_path / "coordinator.py"
    coordinator.write_text("# fixture\n", encoding="utf-8")
    monkeypatch.setattr(module, "COORDINATOR", coordinator)
    monkeypatch.setenv("SHARED_RUNPOD_LEASE_ID", "lease-test")
    monkeypatch.setenv("SHARED_RUNPOD_LEASE_TOKEN", "secret-test-token")
    monkeypatch.setenv("SHARED_RUNPOD_LEASE_PROFILE", "comfyui_model_qualification")

    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["env"] = kwargs["env"]
        return SimpleNamespace(
            returncode=0,
            stderr="",
            stdout=json.dumps(
                {
                    "valid": True,
                    "lease_id": "lease-test",
                    "project": "comfyui_main",
                    "profile": "comfyui_model_qualification",
                    "lease_mode": "exclusive",
                    "reserved_peak_gb": 30.0,
                    "expires_at": "2026-07-22T04:00:00Z",
                }
            ),
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    receipt = module.validate_shared_runpod_lease(
        expected_profile="comfyui_model_qualification"
    )
    assert receipt["token_retained"] is False
    assert "secret-test-token" not in json.dumps(receipt)
    assert "--project" in observed["command"]
    assert observed["env"]["SHARED_RUNPOD_LEASE_TOKEN"] == "secret-test-token"
