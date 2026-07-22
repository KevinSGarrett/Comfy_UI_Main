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


def test_process_exit_cleanup_can_qualify_framework_context_release() -> None:
    module = load_module()
    evidence = {
        "schema_version": "wave64.aqa.qwen3_asr_runtime_canary.v1",
        "status": "FAIL_RUNTIME_OR_TRANSCRIPT_OR_CLEANUP",
        "runtime": {
            "gpu_after_cleanup": {"used_mib": 4458},
            "cleanup_delta_mib": 3810,
            "cleanup_pass": False,
        },
        "transcription": {"gate": {"expected_phrase_present": True}},
        "error": None,
        "authority": {
            "runtime_capacity": False,
            "exact_fixture_transcription": False,
        },
    }
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 648},
        worker_returncode=1,
        worker_stdout="worker receipt written",
        worker_stderr="framework warning",
    )
    assert exit_code == 0
    assert finalized["status"] == "PASS_RUNTIME_TRANSCRIPT_AND_PROCESS_EXIT_CLEANUP"
    assert finalized["runtime"]["in_process_cleanup_delta_mib"] == 3810
    assert finalized["runtime"]["process_exit_cleanup_delta_mib"] == 0
    assert finalized["authority"]["exact_fixture_transcription"] is True


def test_process_exit_cleanup_fails_on_true_residency_delta() -> None:
    module = load_module()
    evidence = {
        "runtime": {
            "gpu_after_cleanup": {"used_mib": 4458},
            "cleanup_delta_mib": 3810,
            "cleanup_pass": False,
        },
        "transcription": {"gate": {"expected_phrase_present": True}},
        "error": None,
        "authority": {
            "runtime_capacity": False,
            "exact_fixture_transcription": False,
        },
    }
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 2048},
        worker_returncode=1,
        worker_stdout="",
        worker_stderr="",
    )
    assert exit_code == 1
    assert finalized["runtime"]["process_exit_cleanup_pass"] is False
    assert finalized["authority"]["runtime_capacity"] is False
