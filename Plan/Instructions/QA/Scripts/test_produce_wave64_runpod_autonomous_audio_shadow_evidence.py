from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_audio_shadow_evidence.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_aqa_audio_shadow_producer", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    artifact = tmp_path / "mix.wav"
    sample_rate = 48000
    duration = 2.0
    times = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    left = 0.1 * np.sin(2 * np.pi * 440 * times)
    right = 0.08 * np.sin(2 * np.pi * 660 * times)
    sf.write(artifact, np.column_stack([left, right]), sample_rate, subtype="PCM_16")
    waveform = tmp_path / "waveform.png"
    spectrogram = tmp_path / "spectrogram.png"
    waveform.write_bytes(b"bounded-waveform-fixture")
    spectrogram.write_bytes(b"bounded-spectrogram-fixture")
    manifest = {
        "outputs": {
            "final_mix": {"path": str(artifact), "sha256": sha256_file(artifact), "bytes": artifact.stat().st_size},
            "waveform": {"path": str(waveform), "sha256": sha256_file(waveform)},
            "spectrogram": {"path": str(spectrogram), "sha256": sha256_file(spectrogram)},
        },
        "pcm_technical": {"final_mix": {"sample_rate_hz": sample_rate, "channels": 2, "duration_seconds": duration}},
        "loudness_measurement": {"target_integrated_lufs": -21.0},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    registry = {
        "roles": [
            {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "state": "ACTIVE_REQUIRED"},
            {"role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC", "state": "BLOCKED_UNQUALIFIED"},
        ]
    }
    registry_path = tmp_path / "roles.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return artifact, manifest_path, registry_path


def build(module, artifact: Path, manifest: Path, registry: Path) -> dict:
    return module.build_evidence(
        artifact_path=artifact,
        manifest_path=manifest,
        role_registry_path=registry,
        generated_at="2026-07-21T22:00:00Z",
        artifact_relative_path="fixtures/mix.wav",
        manifest_relative_path="fixtures/manifest.json",
        observations=["Rendered diagnostics contain a bounded non-silent signal."],
    )


def test_real_deterministic_stage_passes_while_semantic_release_stays_blocked(tmp_path: Path) -> None:
    module = load_producer()
    artifact, manifest, registry = write_fixture(tmp_path)
    first = build(module, artifact, manifest, registry)
    second = build(module, artifact, manifest, registry)
    assert first == second
    assert first["measurement"]["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert first["technical_contract"]["preflight_disposition"] == "READY_FOR_LEASE"
    assert first["technical_contract"]["quality_profile"]["required_approval_roles"] == [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    assert first["semantic_release_gate"]["disposition"] == "BLOCKED_UNQUALIFIED"
    assert first["overall_disposition"] == "PASS_DETERMINISTIC_SHADOW_BLOCKED_SEMANTIC_AUDIO_AUTHORITY"
    assert first["product_promotion_eligible"] is False


def test_tampered_artifact_and_diagnostic_hashes_fail_closed(tmp_path: Path) -> None:
    module = load_producer()
    artifact, manifest, registry = write_fixture(tmp_path)
    artifact.write_bytes(artifact.read_bytes() + b"tamper")
    with pytest.raises(module.EvidenceError, match="artifact hash"):
        build(module, artifact, manifest, registry)

    artifact, manifest, registry = write_fixture(tmp_path)
    (tmp_path / "waveform.png").write_bytes(b"tampered-waveform")
    with pytest.raises(module.EvidenceError, match="waveform hash"):
        build(module, artifact, manifest, registry)


def test_missing_role_authority_and_empty_observation_fail_closed(tmp_path: Path) -> None:
    module = load_producer()
    artifact, manifest, registry = write_fixture(tmp_path)
    registry.write_text(json.dumps({"roles": [{"role_id": "W64-AQA-ROLE-DETERMINISTIC", "state": "ACTIVE_REQUIRED"}]}), encoding="utf-8")
    with pytest.raises(module.EvidenceError, match="semantic audio role"):
        build(module, artifact, manifest, registry)
    with pytest.raises(module.EvidenceError, match="observation"):
        module.build_evidence(
            artifact_path=artifact,
            manifest_path=manifest,
            role_registry_path=registry,
            generated_at="2026-07-21T22:00:00Z",
            artifact_relative_path="fixtures/mix.wav",
            manifest_relative_path="fixtures/manifest.json",
            observations=[],
        )
