from __future__ import annotations

import importlib.util
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_wav2vec2_phoneme_alignment.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("wav2vec2_phoneme_canary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prospective_thresholds_are_frozen() -> None:
    module = load_module()
    assert module.MIN_SPEECH_GREEDY_SIMILARITY == 0.45
    assert module.MIN_SPEECH_ALIGNMENT_POSTERIOR == 0.10
    assert [spec["expect_speech"] for spec in module.FIXTURES.values()] == [
        True,
        False,
        False,
        True,
    ]


def test_model_provenance_is_exact_and_separate_from_payload() -> None:
    module = load_module()
    assert len(module.MODEL_FILES) == 8
    assert module.MODEL_PROVENANCE_FILES == {
        ".w64_aqa_install_receipt.json": (
            2168,
            "0290956ce208deb5bc928ac154e7f0ec822e0b4a2bffc4e95e4acff60aaef1a9",
        )
    }


def test_exact_file_validator_rejects_unpinned_member(tmp_path: Path) -> None:
    module = load_module()
    payload = b"pinned"
    expected = {"payload.bin": (len(payload), hashlib.sha256(payload).hexdigest())}
    (tmp_path / "payload.bin").write_bytes(payload)
    module.validate_exact_files(tmp_path, expected)
    (tmp_path / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(module.CanaryError, match="file-set mismatch"):
        module.validate_exact_files(tmp_path, expected)


def test_ctc_collapse_and_similarity() -> None:
    module = load_module()
    assert module.ctc_collapse([0, 4, 4, 0, 5, 5, 0, 4], blank_id=0) == [4, 5, 4]
    assert module.normalized_similarity([1, 2, 3], [1, 2, 3]) == 1.0
    assert module.normalized_similarity([1, 2, 3], [1, 9, 3]) == pytest.approx(2 / 3)


@dataclass
class Span:
    start: int
    end: int
    score: float


def test_span_projection_produces_monotonic_words() -> None:
    module = load_module()
    spans = [Span(1, 2, -0.1), Span(3, 5, -0.2), Span(6, 7, -0.3)]
    words = [
        {"word": "one", "phoneme_tokens": ["w", "ʌ"]},
        {"word": "two", "phoneme_tokens": ["t"]},
    ]
    tokens, word_spans, monotonic = module.spans_to_records(
        spans, ["w", "ʌ", "t"], words, 0.02
    )
    assert monotonic is True
    assert len(tokens) == 3
    assert word_spans[0]["start_seconds"] == pytest.approx(0.02)
    assert word_spans[1]["end_seconds"] == pytest.approx(0.14)


def test_lease_requires_exact_profile_and_future_expiry() -> None:
    module = load_module()
    with pytest.raises(module.CanaryError, match="identity/profile"):
        module.validate_lease("lease", "wrong", "2999-01-01T00:00:00Z")
    with pytest.raises(module.CanaryError, match="expired"):
        module.validate_lease("lease", module.EXPECTED_PROFILE, "2000-01-01T00:00:00Z")
