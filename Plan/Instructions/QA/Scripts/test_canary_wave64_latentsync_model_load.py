from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_latentsync_model_load.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_model_load_admission.json"
SPEC = importlib.util.spec_from_file_location("canary_latentsync_model_load", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def lease(now: datetime) -> dict:
    return {"valid": True, "lease_id": "lease_test", "project": "comfyui_main", "profile": "comfyui_model_qualification", "lease_mode": "exclusive", "reserved_peak_gib": 12.0, "safety_reserve_gib": 1.0, "expires_at": (now + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")}


def test_exact_sanitized_lease_passes() -> None:
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    assert MODULE.validate_lease(lease(now), admission(), now=now)["lease_id"] == "lease_test"


def test_expired_or_foreign_lease_fails_closed() -> None:
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    expired = lease(now)
    expired["expires_at"] = (now - timedelta(seconds=1)).isoformat()
    with pytest.raises(MODULE.CanaryError, match="expired"):
        MODULE.validate_lease(expired, admission(), now=now)
    foreign = lease(now)
    foreign["project"] = "maskfactory"
    with pytest.raises(MODULE.CanaryError, match="project mismatch"):
        MODULE.validate_lease(foreign, admission(), now=now)


def test_token_bearing_receipt_fails_closed() -> None:
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    tokenized = lease(now)
    tokenized["lease_token"] = "secret"
    with pytest.raises(MODULE.CanaryError, match="must not contain a token"):
        MODULE.validate_lease(tokenized, admission(), now=now)


def test_runtime_capacity_requires_declared_vram_and_host_minima() -> None:
    value = admission()
    required_vram = value["lease"]["required_free_vram_mib"]
    required_host = value["lease"]["minimum_host_available_bytes"]
    accepted = MODULE.validate_runtime_capacity(
        {"free_mib": required_vram}, required_host, value
    )
    assert accepted["required_free_vram_mib"] == required_vram
    with pytest.raises(MODULE.CanaryError, match="free VRAM"):
        MODULE.validate_runtime_capacity(
            {"free_mib": required_vram - 1}, required_host, value
        )
    with pytest.raises(MODULE.CanaryError, match="host memory"):
        MODULE.validate_runtime_capacity(
            {"free_mib": required_vram}, required_host - 1, value
        )


def test_finalize_requires_residency_and_cleanup_without_inference() -> None:
    value = admission()
    before = {"used_mib": 648}
    after = {"used_mib": 648}
    worker = {"error": None, "gpu_loaded": {"used_mib": 3000}, "model": {"parameter_count": 1, "config_resolution": 512, "parameter_devices": ["cuda:0"], "parameter_dtypes": ["torch.float16"]}, "forward_inference_performed": False, "fixture_consumed": False}
    result, code = MODULE.finalize(value, worker, before, after, 0)
    assert code == 0
    assert result["authority"]["model_load"]
    assert not result["authority"]["inference"]
