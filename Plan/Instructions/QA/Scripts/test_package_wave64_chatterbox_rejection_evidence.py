import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/package_wave64_chatterbox_rejection_evidence.py"
SPEC = importlib.util.spec_from_file_location("package_wave64_chatterbox", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PackageWave64ChatterboxRejectionEvidenceTests(unittest.TestCase):
    def _runtime(self):
        return {
            "engine": "ChatterboxTTS",
            "implementation": {
                "control_contract_sha256": MODULE.CONTROL_CONTRACT_SHA256,
                "control_contract": {
                    "text": MODULE.EXPECTED_TEXT,
                    "expected_duration_seconds": 3.0,
                    "max_duration_delta_seconds": 0.35,
                    "style_emotion": "focused",
                    "style_intensity": "controlled",
                    "seed": 64032,
                    "candidate_ordinal": 1,
                    "exaggeration": 0.6,
                    "cfg_weight": 0.3,
                    "temperature": 0.8,
                    "repetition_penalty": 1.2,
                    "min_p": 0.05,
                    "top_p": 1.0,
                    "post_generation_truncation_allowed": False,
                    "post_generation_time_stretch_allowed": False,
                    "same_control_path_retry_allowed": False,
                },
            },
            "runtime": {
                "runtime_executed": True,
                "decode_succeeded": True,
                "post_generation_truncation_applied": False,
                "post_generation_time_stretch_applied": False,
            },
            "output": {
                "sha256": MODULE.CANDIDATE_SHA256,
                "bytes": 188204,
                "pcm": {"duration_seconds": 3.92},
                "perth_watermark_detected": True,
            },
            "gates": {
                "dialogue_timing_pass": False,
                "production_proof_authority_pass": False,
            },
            "boundaries": {
                "maximum_candidates_for_control_path": 1,
                "same_control_path_retry_allowed": False,
            },
        }

    def _evaluation(self):
        return {
            "status": "FAIL_CHATTERBOX_DIALOGUE_TIMING",
            "candidate": {
                "expected_text": MODULE.EXPECTED_TEXT,
                "asr_transcript": MODULE.EXPECTED_TEXT,
                "normalized_wer": 0.0,
                "speaker_similarity": 0.6610352993011475,
                "validated_speaker_threshold": 0.33445611596107483,
                "dnsmos_reference_percentile": 0.875,
                "target_emotion": "focused",
                "target_intensity": "controlled",
                "duration_seconds": 3.92,
                "expected_duration_seconds": 3.0,
                "perth_watermark_score": 1.0,
                "dnsmos": {"OVRL": 3.200727064729366},
                "predicted_emotion": {"predicted_label": "neutral"},
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

    def test_runtime_verifier_accepts_exact_failed_timing_contract(self):
        MODULE.verify_runtime(self._runtime())

    def test_runtime_verifier_rejects_post_generation_stretch(self):
        payload = self._runtime()
        payload["runtime"]["post_generation_time_stretch_applied"] = True
        with self.assertRaisesRegex(ValueError, "time stretch"):
            MODULE.verify_runtime(payload)

    def test_runtime_verifier_rejects_same_path_retry(self):
        payload = self._runtime()
        payload["boundaries"]["same_control_path_retry_allowed"] = True
        with self.assertRaisesRegex(ValueError, "retry"):
            MODULE.verify_runtime(payload)

    def test_evaluation_verifier_accepts_exact_rejection(self):
        MODULE.verify_evaluation(self._evaluation())

    def test_evaluation_verifier_rejects_false_timing_promotion(self):
        payload = self._evaluation()
        payload["gates"]["dialogue_timing_pass"] = True
        with self.assertRaisesRegex(ValueError, "fail-closed"):
            MODULE.verify_evaluation(payload)

    def test_evaluation_verifier_rejects_dnsmos_self_certification(self):
        payload = self._evaluation()
        payload["gates"]["candidate_dnsmos_quality_certification_pass"] = True
        with self.assertRaisesRegex(ValueError, "self-certify"):
            MODULE.verify_evaluation(payload)

    def test_write_exact_produces_identical_mirrors(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / "qa.json", Path(temporary) / "tracker.json"]
            digest = MODULE.write_exact({"ok": True}, paths)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertTrue(all(MODULE.sha256(path) == digest for path in paths))

    def test_git_normalized_text_hash_accepts_crlf_and_lf(self):
        with tempfile.TemporaryDirectory() as temporary:
            lf = Path(temporary) / "lf.py"
            crlf = Path(temporary) / "crlf.py"
            lf.write_bytes(b"one\ntwo\n")
            crlf.write_bytes(b"one\r\ntwo\r\n")
            expected = MODULE.hashlib.sha256(lf.read_bytes()).hexdigest()
            lf_binding = MODULE.require_git_normalized_text_hash(lf, expected, "lf")
            crlf_binding = MODULE.require_git_normalized_text_hash(crlf, expected, "crlf")
            self.assertEqual(lf_binding["sha256"], crlf_binding["sha256"])
            self.assertEqual(crlf_binding["hash_basis"], "git_normalized_lf")


if __name__ == "__main__":
    unittest.main()
