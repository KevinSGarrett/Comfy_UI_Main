from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "build_wave64_speech_ownership_lipsync_benchmark.py"
SPEC = importlib.util.spec_from_file_location("wave64_speech_ownership_lipsync_benchmark", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechOwnershipLipsyncBenchmarkTests(unittest.TestCase):
    def overlap_fixture(self) -> dict:
        return {
            "classification": MODULE.EXPECTED_OVERLAP_CLASSIFICATION,
            "overlap": {
                "metrics": {
                    "sample_rate_hz": 24000,
                    "samples_per_channel": 103201,
                    "kokoro_start_sample": 0,
                    "qwen_start_sample": 26400,
                    "overlap_start_sample": 26400,
                    "overlap_end_sample": 72000,
                },
                "gates": {
                    "overlap_interval_present_pass": True,
                    "source_ownership_from_isolated_stems_pass": True,
                    "sample_sum_integrity_pass": True,
                    "technical_clipping_pass": True,
                    "spatial_separation_pass": True,
                    "independent_diarization_pass": False,
                    "independent_overlap_intelligibility_pass": False,
                    "human_playback_review_pass": False,
                    "production_authority_pass": False,
                },
            },
        }

    def test_overlap_validation_preserves_missing_authority(self) -> None:
        metrics = MODULE._validate_overlap(self.overlap_fixture())
        self.assertEqual(26400, metrics["overlap_start_sample"])
        value = self.overlap_fixture()
        value["overlap"]["gates"]["independent_diarization_pass"] = True
        with self.assertRaisesRegex(MODULE.ControlBuildError, "was not fail-closed"):
            MODULE._validate_overlap(value)

    def test_overlap_validation_rejects_noncontiguous_topology(self) -> None:
        value = self.overlap_fixture()
        value["overlap"]["metrics"]["qwen_start_sample"] = 25000
        with self.assertRaisesRegex(MODULE.ControlBuildError, "expected topology"):
            MODULE._validate_overlap(value)

    def test_alignment_accepts_only_bounded_word_grapheme_authority(self) -> None:
        alignment = {
            "artifact_sha256": "a" * 64,
            "pass": True,
            "monotonic": True,
            "alignment_authority": {
                "method": "torchaudio_mms_fa_ctc_grapheme_word_alignment",
                "word_timing_runtime_pass": True,
                "grapheme_ctc_runtime_pass": True,
                "phoneme_forced_alignment_pass": False,
                "mfa_style_phoneme_authority": False,
                "whisperx_style_word_authority": False,
            },
            "words": [
                {"label": "one", "start_sample": 2, "end_sample": 8},
                {"label": "two", "start_sample": 9, "end_sample": 15},
            ],
        }
        self.assertEqual(2, len(MODULE._validate_alignment(alignment, "a" * 64)))
        alignment["alignment_authority"]["phoneme_forced_alignment_pass"] = True
        with self.assertRaisesRegex(MODULE.ControlBuildError, "bounded word/grapheme"):
            MODULE._validate_alignment(alignment, "a" * 64)

    def test_atomic_json_write_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            MODULE.write_json_atomic(path, {"classification": "blocked"})
            first = path.read_bytes()
            MODULE.write_json_atomic(path, {"classification": "blocked"})
            self.assertEqual(first, path.read_bytes())
            self.assertEqual("blocked", json.loads(first)["classification"])

    def test_binding_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.bin"
            path.write_bytes(b"fixture")
            with self.assertRaisesRegex(MODULE.ControlBuildError, "SHA-256 mismatch"):
                MODULE.binding(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
