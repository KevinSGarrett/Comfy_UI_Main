from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_qwen3_asr_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location("qwen3_asr_runtime_canary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_transcript_gate_normalizes_case_and_punctuation() -> None:
    module = load_module()
    result = module.evaluate_transcript(
        "Once upon a midnight, dreary!", "once upon a midnight"
    )
    assert result["expected_phrase_present"] is True
    assert result["disposition"] == "PASS_EXPECTED_TRANSCRIPT_PRESENT"


def test_transcript_gate_rejects_missing_expected_phrase() -> None:
    module = load_module()
    result = module.evaluate_transcript("unrelated hallucination", "once upon a midnight")
    assert result["expected_phrase_present"] is False


def test_input_validation_binds_receipt_revision_manifest_and_audio(
    tmp_path: Path,
) -> None:
    module = load_module()
    model_root = tmp_path / "model"
    model_root.mkdir()
    (model_root / ".w64_aqa_install_receipt.json").write_text(
        json.dumps(
            {
                "manifest_sha256": module.MODEL_MANIFEST_SHA256,
                "source_revision": module.MODEL_REVISION,
            }
        ),
        encoding="utf-8",
    )
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"fixture-audio")
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    result = module.validate_inputs(model_root, audio, digest)
    assert result["audio_sha256"] == digest
    assert result["model_revision"] == module.MODEL_REVISION


@pytest.mark.parametrize("field", ["manifest_sha256", "source_revision"])
def test_input_validation_fails_closed_on_model_identity_mismatch(
    tmp_path: Path, field: str
) -> None:
    module = load_module()
    model_root = tmp_path / "model"
    model_root.mkdir()
    receipt = {
        "manifest_sha256": module.MODEL_MANIFEST_SHA256,
        "source_revision": module.MODEL_REVISION,
    }
    receipt[field] = "0" * 64
    (model_root / ".w64_aqa_install_receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"fixture-audio")
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    with pytest.raises(module.CanaryError, match="mismatch"):
        module.validate_inputs(model_root, audio, digest)
