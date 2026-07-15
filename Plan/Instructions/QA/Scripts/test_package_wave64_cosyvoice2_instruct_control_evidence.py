import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/package_wave64_cosyvoice2_instruct_control_evidence.py"
SPEC = importlib.util.spec_from_file_location("package_wave64_cosyvoice2_instruct", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PackageWave64CosyVoice2InstructControlEvidenceTests(unittest.TestCase):
    def _runtime(self):
        return {
            "engine": "CosyVoice2",
            "runtime": {
                "inference_mode": "instruct2",
                "speed": 1.2,
                "model_native_speed_control": True,
                "post_generation_truncation_applied": False,
                "post_generation_time_stretch_applied": False,
            },
            "dialogue": {
                "instruct_text": MODULE.INSTRUCT_TEXT,
                "instruct_text_sha256": MODULE.INSTRUCT_SHA256,
            },
            "boundaries": {
                "authorized_candidate_ordinal": 1,
                "maximum_candidates_for_control_path": 1,
            },
            "output": {
                "sha256": MODULE.CANDIDATE_SHA256,
                "bytes": 351404,
                "pcm": {"duration_seconds": 7.32},
            },
            "gates": {
                "dialogue_timing_pass": False,
                "production_proof_authority_pass": False,
            },
        }

    def _evaluation(self):
        return {
            "status": "FAIL_COSYVOICE2_DIALOGUE_TIMING",
            "candidate": {
                "asr_transcript": "I'm not sure if I can get it.",
                "normalized_wer": 1.0,
                "speaker_similarity": 0.34052106738090515,
                "validated_speaker_threshold": 0.33445611596107483,
                "dnsmos_reference_percentile": 0.5,
                "inference_mode": "instruct2",
                "duration_seconds": 7.32,
                "expected_duration_seconds": 3.0,
                "dnsmos": {"OVRL": 2.8629396650581356},
                "predicted_emotion": {"predicted_label": "happy"},
            },
            "gates": {
                "candidate_asr_pass": False,
                "candidate_reference_speaker_identity_pass": True,
                "candidate_dnsmos_worst_reference_floor_pass": True,
                "dialogue_timing_pass": False,
                "target_emotion_taxonomy_supported": False,
                "independent_playback_review_pass": False,
                "production_proof_authority_pass": False,
                "row_complete": False,
                "final_voice_certification_pass": False,
            },
        }

    def test_runtime_verifier_accepts_exact_control_contract(self):
        MODULE.verify_runtime(self._runtime())

    def test_runtime_verifier_rejects_post_generation_stretch(self):
        payload = self._runtime()
        payload["runtime"]["post_generation_time_stretch_applied"] = True
        with self.assertRaisesRegex(ValueError, "time stretch"):
            MODULE.verify_runtime(payload)

    def test_evaluation_verifier_accepts_exact_rejection(self):
        MODULE.verify_evaluation(self._evaluation())

    def test_evaluation_verifier_rejects_false_asr_promotion(self):
        payload = self._evaluation()
        payload["gates"]["candidate_asr_pass"] = True
        with self.assertRaisesRegex(ValueError, "ASR failure"):
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
