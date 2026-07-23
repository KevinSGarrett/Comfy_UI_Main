from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_mit_ast_audioset_events.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_mit_ast_audioset_event_canary_admission.json"
PLAN = ROOT / "Plan/10_REGISTRIES/wave64_forced_alignment_audio_event_expansion_plan.json"
SPEC = importlib.util.spec_from_file_location("canary_mit_ast", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def lease(now: datetime) -> dict:
    return {"valid": True, "lease_id": "lease_test", "project": "comfyui_main", "profile": "comfyui_model_qualification", "lease_mode": "exclusive", "reserved_peak_gib": 4.0, "safety_reserve_gib": 1.0, "expires_at": (now + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")}


def plan() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def test_exact_sanitized_lease_passes_and_token_fails() -> None:
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    assert MODULE.validate_lease(lease(now), admission(), now=now)["lease_id"] == "lease_test"
    tokenized = lease(now)
    tokenized["lease_token"] = "secret"
    with pytest.raises(MODULE.CanaryError, match="must not contain a token"):
        MODULE.validate_lease(tokenized, admission(), now=now)


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


def test_partition_order_requires_matching_calibration_receipt() -> None:
    value = admission()
    with pytest.raises(MODULE.CanaryError, match="passing calibration"):
        MODULE.validate_partition(plan(), "held_out", None, value)
    receipt = {"status": "PASS_EXACT_EVENT_CALIBRATION_PARTITION", "plan_sha256": value["plan"]["sha256"], "model_revision": value["model"]["revision"]}
    cases = MODULE.validate_partition(plan(), "held_out", receipt, value)
    assert [case["case_id"] for case in cases] == ["event_speech_foley_ambience_mix", "event_two_speaker_overlap"]
    receipt["model_revision"] = "wrong"
    with pytest.raises(MODULE.CanaryError, match="identity mismatch"):
        MODULE.validate_partition(plan(), "held_out", receipt, value)


def test_label_family_matching_is_bounded() -> None:
    assert MODULE.family_match("speech", "Male speech, man speaking")
    assert MODULE.family_match("cloth movement", "Rustling")
    assert MODULE.family_match("room ambience", "Inside, small room")
    assert not MODULE.family_match("speech", "Engine")


def test_audio_is_resampled_to_exact_ast_rate() -> None:
    audio = np.linspace(-1.0, 1.0, 48000, dtype=np.float32)
    resampled = MODULE.resample_audio(audio, 48000, 16000)
    assert resampled.dtype == np.float32
    assert resampled.shape == (16000,)
    assert MODULE.resample_audio(audio, 48000, 48000) is audio


def test_invalid_resampling_input_fails_closed() -> None:
    with pytest.raises(MODULE.CanaryError, match="invalid audio resampling input"):
        MODULE.resample_audio(np.array([], dtype=np.float32), 48000, 16000)


def test_git_blob_identity_matches_git_hash_object(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_bytes(b"bounded\n")
    assert MODULE.git_blob_sha1(path) == "9906b2ec88da353ebc55f548563ebf11ea7ef95c"


def test_finalize_requires_cleanup_and_worker_success() -> None:
    worker = {"status": "PASS_EXACT_EVENT_CALIBRATION_PARTITION", "error": None, "runtime": {}, "authority": {"exact_partition_measurement": True}}
    result, code = MODULE.finalize(worker, {"used_mib": 600}, {"used_mib": 650}, 0, 1024)
    assert code == 0 and result["runtime"]["process_exit_cleanup_pass"]
    failed = {"status": "PASS_EXACT_EVENT_CALIBRATION_PARTITION", "error": None, "runtime": {}, "authority": {"exact_partition_measurement": True}}
    result, code = MODULE.finalize(failed, {"used_mib": 600}, {"used_mib": 2000}, 0, 1024)
    assert code == 1 and not result["authority"]["exact_partition_measurement"]
