from __future__ import annotations

import importlib.util
import json
import argparse
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/package_wave64_kokoro_audition_evidence.py"
SPEC = importlib.util.spec_from_file_location("wave64_kokoro_packager", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_expected_hashes_are_immutable_sha256_values() -> None:
    for value in (
        MODULE.EXPECTED_SELECTED_SHA256,
        MODULE.EXPECTED_MANIFEST_SHA256,
        MODULE.EXPECTED_EVALUATION_SHA256,
        MODULE.EXPECTED_REQUEST_SHA256,
    ):
        assert len(value) == 64
        int(value, 16)


def test_bind_rejects_tamper(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"tamper")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        MODULE.bind(path, "0" * 64, "artifact")


def test_request_must_bind_selected_and_evaluation() -> None:
    request_path = (
        MODULE.PROJECT_ROOT
        / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
        / "w64_kokoro_audition_20260715T131034-0500/human_playback_review_request.json"
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    selected = {"sha256": "a" * 64}
    evaluation = request["automated_evidence_bindings"][-1]
    with pytest.raises(ValueError, match="selected candidate"):
        MODULE.verify_request(request, selected, evaluation)


def test_request_cannot_claim_blinding_when_paths_disclose_engine() -> None:
    request_path = (
        MODULE.PROJECT_ROOT
        / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
        / "w64_kokoro_audition_20260715T131034-0500/human_playback_review_request.json"
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["blinding"]["engine_identity_hidden_initial_pass"] = True
    selected = request["artifact_binding"]
    evaluation = request["automated_evidence_bindings"][-1]
    with pytest.raises(ValueError, match="claims engine blinding"):
        MODULE.verify_request(request, selected, evaluation)


def test_package_derives_selected_metrics_from_bound_evaluation() -> None:
    artifact_dir = (
        MODULE.PROJECT_ROOT
        / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
        / "w64_kokoro_audition_20260715T131034-0500"
    )
    arguments = argparse.Namespace(
        artifact_dir=str(artifact_dir),
        selected_candidate=str(artifact_dir / "L001_C01_kokoro_speed_1.00_pcm3s.wav"),
        audition_manifest=str(artifact_dir / "kokoro_audition_manifest.json"),
        evaluation=str(artifact_dir / "kokoro_audition_evaluation.json"),
        human_request=str(artifact_dir / "human_playback_review_request.json"),
    )
    payload = MODULE.package(arguments)
    evaluation = json.loads((artifact_dir / "kokoro_audition_evaluation.json").read_text(encoding="utf-8"))
    row = next(item for item in evaluation["candidates"] if item["candidate_id"] == payload["selected_candidate"]["candidate_id"])
    assert payload["selected_candidate"]["normalized_wer"] == row["metrics"]["normalized_wer"]
    assert payload["selected_candidate"]["dnsmos_ovrl"] == row["metrics"]["dnsmos"]["OVRL"]
    assert payload["selected_candidate"]["engine"] == "kokoro"


def test_evidence_mirrors_are_byte_identical(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    digest = MODULE.write_mirrors({"status": "PASS"}, [left, right])
    assert left.read_bytes() == right.read_bytes()
    assert MODULE.sha256(left) == digest
