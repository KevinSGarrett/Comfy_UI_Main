from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_overlap_adversarial_promotion_control.py"
SPEC = importlib.util.spec_from_file_location("wave64_overlap_controls", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def tone(path: Path, frequency: float, seconds: float) -> None:
    rate = 24000
    time = np.arange(int(rate * seconds), dtype=np.float64) / rate
    audio = 0.25 * np.sin(2.0 * math.pi * frequency * time)
    sf.write(str(path), audio, rate, subtype="PCM_16")


class Wave64OverlapAdversarialPromotionControlTests(unittest.TestCase):
    def test_overlap_render_preserves_stems_and_spatial_priority_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = root / "left.wav"
            right = root / "right.wav"
            tone(left, 220.0, 3.0)
            tone(right, 330.0, 3.2)
            bindings, report = MODULE.render_overlap(left, right, root / "out")
            gates = report["gates"]
            self.assertTrue(gates["source_ownership_from_isolated_stems_pass"])
            self.assertTrue(gates["overlap_interval_present_pass"])
            self.assertTrue(gates["priority_duck_pass"])
            self.assertTrue(gates["spatial_separation_pass"])
            self.assertTrue(gates["sample_sum_integrity_pass"])
            self.assertTrue(gates["technical_clipping_pass"])
            self.assertFalse(gates["independent_diarization_pass"])
            self.assertFalse(gates["production_authority_pass"])
            self.assertEqual(3, len(bindings))

    def test_defect_matrix_detects_known_fixtures_but_keeps_coverage_blocked(self) -> None:
        records = {
            "kokoro": {"status": "PASS_AUTOMATED_CANDIDATE_ELIGIBLE_HUMAN_PLAYBACK_REQUIRED", "acceptance": {"human_playback_review_pass": False, "production_authority_pass": False}},
            "qwen": {"classification": "PASS_QWEN3_CLONE_CHAIN_SPECIFIC_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED", "gates": {"raw_dialogue_timing_pass": False, "independent_playback_review_pass": False, "production_reference_authority_pass": False}},
            "cosyvoice2": {"classification": "FAIL_COSYVOICE2_DIALOGUE_TIMING", "gates": {"dialogue_timing_pass": False, "target_emotion_taxonomy_supported": False, "target_intensity_taxonomy_status": "unmeasured_no_calibrated_intensity_evaluator", "independent_playback_review_pass": False, "production_proof_authority_pass": False}},
            "chatterbox": {"classification": "FAIL_CHATTERBOX_DIALOGUE_TIMING", "gates": {"dialogue_timing_pass": False, "target_emotion_taxonomy_supported": False, "target_intensity_taxonomy_status": "unmeasured_no_calibrated_intensity_evaluator", "independent_playback_review_pass": False, "production_proof_authority_pass": False}},
            "parler": {"blockers": ["missing emotion_proof", "missing playback_review_proof", "missing production_proof_bundle_binding", "missing speaker_proof"]},
        }
        bindings = {name: {"sha256": character * 64} for name, character in {
            "kokoro_wav": "1", "qwen_wav": "2", "cosyvoice2_wav": "3", "chatterbox_wav": "4", "parler_wav": "5"
        }.items()}
        matrix = MODULE.evaluate_defect_matrix(records, bindings)
        self.assertTrue(matrix["known_fixture_detection_pass"])
        self.assertEqual(1.0, matrix["known_fixture_detection_rate"])
        self.assertFalse(matrix["full_required_category_coverage_pass"])
        self.assertFalse(matrix["coverage"]["multilingual"])
        self.assertFalse(matrix["candidate_media_mutated"])

    def test_blocked_candidate_request_cannot_promote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "candidate.bin"
            artifact.write_bytes(b"candidate\n")
            binding = MODULE.bind(artifact)
            request = MODULE.build_blocked_request("CANDIDATE", binding, "C01-PENDING", {
                "identity_policy": "evaluation_only",
                "reference_id": "REF",
                "reference_sha256": None,
                "model_id": "MODEL",
                "approved_use": "evaluation_only",
                "rights_valid": True,
                "production_authorized": False,
                "evaluation_sha256": "6" * 64,
                "hard_gates_pass": False,
                "ranking_complete": False,
            })
            promotion = MODULE._load_promotion_module(ROOT)
            result = MODULE.exercise_promotion_control(promotion, root / "out", [request])
            self.assertTrue(result["all_current_candidates_refused_pass"])
            self.assertTrue(result["synthetic_non_media_control_probe"]["idempotent_replay_pass"])
            self.assertTrue(result["synthetic_non_media_control_probe"]["revocation_invalidation_pass"])
            self.assertFalse(result["production_promotion_performed"])

    def test_source_declares_no_false_authority(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"independent_diarization_pass": False', text)
        self.assertIn('"human_review_fabricated": False', text)
        self.assertIn('"production_promotion_performed": False', text)
        self.assertIn('"content_based_suppression": False', text)


if __name__ == "__main__":
    unittest.main()
