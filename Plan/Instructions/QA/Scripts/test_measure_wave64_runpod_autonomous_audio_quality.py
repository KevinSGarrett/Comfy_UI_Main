from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
MEASURER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_audio_quality.py"


def load_measurer():
    spec = importlib.util.spec_from_file_location("w64_aqa_audio_measure", MEASURER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(
    *, sample_rate: int = 48000, channels: int = 2, duration: float = 2.0,
    lufs_target: float = -21.0, modality: str = "audio",
) -> dict:
    value = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "contract_id": "b" * 64,
        "modality": modality,
        "preflight_disposition": "READY_FOR_LEASE",
        "audio_spec": {
            "sample_rate_hz": sample_rate,
            "channels": channels,
            "duration_seconds": duration,
            "lufs_target": lufs_target,
        },
        "quality_profile": {"hard_gates": [
            {"gate_id": "decode", "metric": "decode_success", "operator": "eq", "threshold": True, "on_failure": "REJECT"},
            {"gate_id": "clipping", "metric": "clipped_sample_fraction", "operator": "lte", "threshold": 0.0, "on_failure": "REPAIR"},
            {"gate_id": "dc", "metric": "max_abs_dc_offset", "operator": "lte", "threshold": 0.01, "on_failure": "REPAIR"},
            {"gate_id": "silence", "metric": "silence_frame_fraction", "operator": "lt", "threshold": 0.9, "on_failure": "REPAIR"},
        ]},
    }
    if modality == "av":
        value["av_spec"] = {"max_sync_error_ms": 50.0, "alignment_required": True}
    return value


def write_tone(
    path: Path, *, sample_rate: int = 48000, duration: float = 2.0,
    amplitude: float = 0.1, dc: float = 0.0, channels: int = 2,
) -> None:
    times = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    mono = amplitude * np.sin(2 * np.pi * 440 * times) + dc
    samples = np.repeat(mono[:, None], channels, axis=1)
    sf.write(path, samples, sample_rate, subtype="FLOAT")


def test_audio_measurement_is_deterministic_and_complete(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "tone.wav"
    write_tone(path)
    first = module.measure_audio(path, contract())
    second = module.measure_audio(path, contract())
    assert first == second
    assert first["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert first["container"]["full_decode_pass"] is True
    assert first["metrics"]["spectral_centroid_hz"] == pytest.approx(440, abs=5)
    assert first["loudness"]["integrated_lufs"] is not None


def test_clipping_and_dc_offset_fail_declared_gates(tmp_path: Path) -> None:
    module = load_measurer()
    clipped = tmp_path / "clipped.wav"
    write_tone(clipped, amplitude=1.2)
    clipped_result = module.measure_audio(clipped, contract())
    assert next(item for item in clipped_result["gate_results"] if item["gate_id"] == "clipping")["status"] == "FAIL"
    offset = tmp_path / "offset.wav"
    write_tone(offset, dc=0.05)
    offset_result = module.measure_audio(offset, contract())
    assert next(item for item in offset_result["gate_results"] if item["gate_id"] == "dc")["status"] == "FAIL"


def test_sample_rate_mismatch_and_silence_fail_closed(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "tone.wav"
    write_tone(path, sample_rate=44100)
    result = module.measure_audio(path, contract())
    assert next(item for item in result["gate_results"] if item["gate_id"] == "contract-sample-rate")["status"] == "FAIL"
    silence = tmp_path / "silence.wav"
    sf.write(silence, np.zeros((96000, 2), dtype=np.float32), 48000, subtype="FLOAT")
    silent_result = module.measure_audio(silence, contract())
    assert next(item for item in silent_result["gate_results"] if item["gate_id"] == "silence")["status"] == "FAIL"
    assert silent_result["disposition"] == "FAIL_DETERMINISTIC_GATES"


def test_unknown_semantic_metric_is_unavailable(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "tone.wav"
    write_tone(path)
    spec = contract()
    spec["quality_profile"]["hard_gates"].append({
        "gate_id": "asr", "metric": "asr_script_word_accuracy", "operator": "gte",
        "threshold": 0.98, "on_failure": "HOLD",
    })
    result = module.measure_audio(path, spec)
    gate = next(item for item in result["gate_results"] if item["gate_id"] == "asr")
    assert gate["status"] == "MEASUREMENT_UNAVAILABLE"
    assert result["disposition"] == "FAIL_DETERMINISTIC_GATES"


def test_av_container_start_offset_is_measured_but_semantic_sync_is_not_invented(tmp_path: Path) -> None:
    module = load_measurer()
    path = tmp_path / "av.mp4"
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x48:r=16:d=2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
        "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    spec = contract(channels=1, modality="av")
    spec["quality_profile"]["hard_gates"].append({
        "gate_id": "lip-sync", "metric": "semantic_lip_sync_error_ms", "operator": "lte",
        "threshold": 50.0, "on_failure": "HOLD",
    })
    result = module.measure_audio(path, spec)
    assert result["av_container"] is not None
    assert result["metrics"]["av_stream_start_offset_ms"] <= 50.0
    assert next(item for item in result["gate_results"] if item["gate_id"] == "lip-sync")["status"] == "MEASUREMENT_UNAVAILABLE"


def test_corrupt_unready_and_oversized_decode_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_measurer()
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio")
    with pytest.raises(module.MeasurementError, match="ffprobe failed"):
        module.measure_audio(bad, contract())
    path = tmp_path / "tone.wav"
    write_tone(path)
    held = contract()
    held["preflight_disposition"] = "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    with pytest.raises(module.MeasurementError, match="not ready"):
        module.measure_audio(path, held)
    monkeypatch.setattr(module, "MAX_DECODED_BYTES", 1)
    with pytest.raises(module.MeasurementError, match="bounded limit"):
        module.measure_audio(path, contract())
