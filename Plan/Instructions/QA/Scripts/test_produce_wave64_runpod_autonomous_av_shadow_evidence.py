from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_av_shadow_evidence.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_aqa_av_shadow_producer", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    audio = tmp_path / "mix.wav"
    sample_rate = 48000
    duration = 2.0
    times = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    tone = 0.1 * np.sin(2 * np.pi * 440 * times)
    sf.write(audio, np.column_stack([tone, tone]), sample_rate, subtype="PCM_16")
    source_video = tmp_path / "source.mkv"
    mux = tmp_path / "review.mkv"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
            "color=c=blue:s=64x48:r=16:d=2", "-c:v", "ffv1", "-an", str(source_video),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-v", "error", "-i", str(source_video), "-i",
            str(audio), "-c:v", "copy", "-c:a", "pcm_s16le", "-shortest", str(mux),
        ],
        check=True,
        capture_output=True,
    )
    manifest = {
        "outputs": {
            "review_mux": {"sha256": sha256_file(mux), "bytes": mux.stat().st_size},
            "strict_source_video": {"sha256": sha256_file(source_video)},
        },
        "pcm_technical": {"final_mix": {"sample_rate_hz": sample_rate, "channels": 2}},
        "loudness_measurement": {"target_integrated_lufs": -21.5},
        "sync": {"video_frame_rate": 16.0},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    registry = {
        "roles": [
            {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "state": "ACTIVE_REQUIRED"},
            {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "state": "ACTIVE_STRICT_SCOPED"},
            {"role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC", "state": "BLOCKED_UNQUALIFIED"},
            {"role_id": "W64-AQA-ROLE-INDEPENDENT-JUROR", "state": "BLOCKED_UNQUALIFIED"},
        ]
    }
    registry_path = tmp_path / "roles.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return mux, source_video, manifest_path, registry_path


def build(module, mux: Path, video: Path, manifest: Path, registry: Path) -> dict:
    return module.build_evidence(
        mux_path=mux,
        source_video_path=video,
        manifest_path=manifest,
        role_registry_path=registry,
        generated_at="2026-07-21T22:30:00Z",
        mux_relative_path="fixtures/review.mkv",
        source_video_relative_path="fixtures/source.mkv",
        manifest_relative_path="fixtures/manifest.json",
        frame_timestamp_seconds=1.0,
        frame_observations=["A single decoded frame was visible and structurally intact."],
    )


def test_real_av_container_stage_passes_without_semantic_authority(tmp_path: Path) -> None:
    module = load_producer()
    mux, video, manifest, registry = write_fixture(tmp_path)
    first = build(module, mux, video, manifest, registry)
    second = build(module, mux, video, manifest, registry)
    assert first == second
    assert first["measurement"]["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert first["measurement"]["metrics"]["av_stream_start_offset_ms"] <= 50.0
    assert first["measurement"]["metrics"]["av_stream_duration_delta_ms"] <= 50.0
    assert first["technical_contract"]["quality_profile"]["required_approval_roles"] == [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    assert first["decoded_frame_review"]["motion_review_claimed"] is False
    assert len(first["decoded_frame_review"]["frame_sha256"]) == 64
    assert first["product_promotion_eligible"] is False
    assert first["overall_disposition"] == "PASS_DETERMINISTIC_AV_SHADOW_BLOCKED_SEMANTIC_AUTHORITIES"


def test_tampered_mux_and_missing_release_role_fail_closed(tmp_path: Path) -> None:
    module = load_producer()
    mux, video, manifest, registry = write_fixture(tmp_path)
    mux.write_bytes(mux.read_bytes() + b"tamper")
    with pytest.raises(module.EvidenceError, match="hash"):
        build(module, mux, video, manifest, registry)

    mux, video, manifest, registry = write_fixture(tmp_path)
    role_doc = json.loads(registry.read_text(encoding="utf-8"))
    role_doc["roles"] = [
        role for role in role_doc["roles"]
        if role["role_id"] != "W64-AQA-ROLE-INDEPENDENT-JUROR"
    ]
    registry.write_text(json.dumps(role_doc), encoding="utf-8")
    with pytest.raises(module.EvidenceError, match="required role"):
        build(module, mux, video, manifest, registry)
