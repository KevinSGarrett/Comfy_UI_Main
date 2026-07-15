#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/package_wave64_cosyvoice2_corrected_reference_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("package_corrected_cosyvoice2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PackageCorrectedCosyVoice2EvidenceTests(unittest.TestCase):
    def test_evaluation_accepts_narrow_passes_and_timing_rejection(self):
        payload = {
            "status": "FAIL_COSYVOICE2_DIALOGUE_TIMING",
            "candidate": {
                "normalized_wer": 0.0,
                "speaker_similarity": 0.6607623100280762,
                "validated_speaker_threshold": 0.33445611596107483,
                "dnsmos_reference_percentile": 0.75,
                "duration_seconds": 4.84,
                "expected_duration_seconds": 3.0,
                "dnsmos": {"OVRL": 3.174097435695213},
            },
            "gates": {
                "candidate_asr_pass": True,
                "candidate_reference_speaker_identity_pass": True,
                "candidate_dnsmos_worst_reference_floor_pass": True,
                "candidate_dnsmos_quality_certification_pass": None,
                "dialogue_timing_pass": False,
                "target_emotion_taxonomy_supported": False,
                "target_intensity_taxonomy_supported": None,
                "independent_playback_review_pass": False,
                "production_proof_authority_pass": False,
                "row_complete": False,
                "final_voice_certification_pass": False,
            },
        }
        MODULE.verify_evaluation(payload)

    def test_evaluation_rejects_false_timing_promotion(self):
        payload = {
            "status": "FAIL_COSYVOICE2_DIALOGUE_TIMING",
            "candidate": {
                "normalized_wer": 0.0,
                "speaker_similarity": 0.6607623100280762,
                "validated_speaker_threshold": 0.33445611596107483,
                "dnsmos_reference_percentile": 0.75,
                "duration_seconds": 4.84,
                "expected_duration_seconds": 3.0,
                "dnsmos": {"OVRL": 3.174097435695213},
            },
            "gates": {
                "candidate_asr_pass": True,
                "candidate_reference_speaker_identity_pass": True,
                "candidate_dnsmos_worst_reference_floor_pass": True,
                "candidate_dnsmos_quality_certification_pass": None,
                "dialogue_timing_pass": True,
                "target_emotion_taxonomy_supported": False,
                "target_intensity_taxonomy_supported": None,
                "independent_playback_review_pass": False,
                "production_proof_authority_pass": False,
                "row_complete": False,
                "final_voice_certification_pass": False,
            },
        }
        with self.assertRaisesRegex(ValueError, "fail-closed"):
            MODULE.verify_evaluation(payload)

    def test_write_exact_keeps_mirrors_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / "qa.json", Path(temporary) / "tracker.json"]
            digest = MODULE.write_exact({"row_complete": False}, paths)
            self.assertTrue(all(MODULE.sha256(path) == digest for path in paths))


if __name__ == "__main__":
    unittest.main()
