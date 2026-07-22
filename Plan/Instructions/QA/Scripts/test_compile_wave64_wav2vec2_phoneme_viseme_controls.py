from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema.validators import validator_for


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_wav2vec2_phoneme_viseme_controls.py"
REGISTRY = ROOT / "Plan/10_REGISTRIES/wave64_ipa_viseme_mapping_registry.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_phoneme_viseme_compilation.schema.json"


def load_module():
    spec = importlib.util.spec_from_file_location("wave64_phoneme_viseme", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def synthetic_receipt() -> dict:
    spans = [
        {"token": "p", "start_seconds": 0.10, "end_seconds": 0.14, "posterior": 0.91},
        {"token": "t", "start_seconds": 0.20, "end_seconds": 0.24, "posterior": 0.92},
        {"token": "f", "start_seconds": 0.30, "end_seconds": 0.34, "posterior": 0.93},
        {"token": "iː", "start_seconds": 0.40, "end_seconds": 0.44, "posterior": 0.94},
    ]
    return {
        "status": "PASS_EXACT_MATRIX_AND_PROCESS_EXIT_CLEANUP",
        "transcript": "prospective synthetic control",
        "authority": {"exact_matrix_alignment": True},
        "fixtures": [
            {
                "fixture_id": "clean_speech",
                "expect_speech": True,
                "speech_gate": True,
                "passed": True,
                "input_sample_rate_hz": 1000,
                "duration_seconds": 0.8,
                "sha256": "a" * 64,
                "phoneme_spans": spans,
            }
        ],
    }


def test_pinned_control_identities_are_exact() -> None:
    module = load_module()
    assert module.sha256_file(REGISTRY) == module.EXPECTED_MAPPING_SHA256
    assert module.sha256_file(SCHEMA) == module.EXPECTED_SCHEMA_SHA256
    assert module.EXPECTED_CANARY_SHA256 == (
        "404dbd97bbef08b966f6a39434b7256b97e42dc0c1a7c9cd56949f4f48878a93"
    )


def test_synthetic_compilation_has_complete_nonoverlap_and_required_coverage() -> None:
    module = load_module()
    result = module.compile_fixture(synthetic_receipt(), registry(), "clean_speech", 25)
    assert result["status"] == "PASS_EXACT_ACCEPTED_ALIGNMENT_TO_VISEME_CONTROLS"
    assert all(result["gates"].values())
    assert all(result["coverage"].values())
    assert result["events"][0]["start_sample"] == 0
    assert result["events"][-1]["end_sample"] == 800
    assert all(
        left["end_sample"] == right["start_sample"]
        for left, right in zip(result["events"], result["events"][1:], strict=False)
    )
    assert [frame["frame_index"] for frame in result["frame_controls"]] == list(range(20))
    assert all(sum(frame["viseme_weights"].values()) == pytest.approx(1.0) for frame in result["frame_controls"])


def test_synthetic_compilation_is_deterministic_and_schema_valid() -> None:
    module = load_module()
    first = module.compile_fixture(synthetic_receipt(), registry(), "clean_speech", 24)
    second = module.compile_fixture(synthetic_receipt(), registry(), "clean_speech", 24)
    assert module.canonical_sha256(first) == module.canonical_sha256(second)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(first)


def test_unmapped_or_overlapping_phonemes_fail_closed() -> None:
    module = load_module()
    unmapped = synthetic_receipt()
    unmapped["fixtures"][0]["phoneme_spans"][0]["token"] = "not-ipa"
    with pytest.raises(module.VisemeCompilationError, match="unmapped IPA"):
        module.compile_fixture(unmapped, registry(), "clean_speech", 24)
    overlapping = synthetic_receipt()
    overlapping["fixtures"][0]["phoneme_spans"][1]["start_seconds"] = 0.13
    with pytest.raises(module.VisemeCompilationError, match="monotonic"):
        module.compile_fixture(overlapping, registry(), "clean_speech", 24)


def test_nonaccepted_source_or_nonspeech_fixture_fails_closed() -> None:
    module = load_module()
    failed = synthetic_receipt()
    failed["status"] = "FAIL_MATRIX_RUNTIME_OR_PROCESS_EXIT_CLEANUP"
    with pytest.raises(module.VisemeCompilationError, match="did not pass"):
        module.compile_fixture(failed, registry(), "clean_speech", 24)
    nonspeech = copy.deepcopy(synthetic_receipt())
    nonspeech["fixtures"][0]["speech_gate"] = False
    with pytest.raises(module.VisemeCompilationError, match="speech authority"):
        module.compile_fixture(nonspeech, registry(), "clean_speech", 24)


def test_authority_remains_bounded() -> None:
    module = load_module()
    authority = module.compile_fixture(synthetic_receipt(), registry(), "clean_speech", 24)["authority"]
    assert authority["exact_accepted_alignment_input"] is True
    assert authority["sample_accurate_viseme_compilation"] is True
    assert authority["rendered_lip_sync"] is False
    assert authority["identity_preservation"] is False
    assert authority["audio_visual_sync"] is False
    assert authority["operational_activation"] is False
    assert authority["product_promotion"] is False
