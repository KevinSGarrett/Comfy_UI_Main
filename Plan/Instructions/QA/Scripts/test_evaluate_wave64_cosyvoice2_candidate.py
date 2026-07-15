import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_cosyvoice2_candidate.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_cosyvoice2_candidate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class EvaluateWave64CosyVoice2CandidateTests(unittest.TestCase):
    def _fixture(self, base: Path):
        candidate = base / "candidate.wav"
        reference = base / "reference.wav"
        candidate.write_bytes(b"candidate")
        reference.write_bytes(b"reference")
        manifest = {
            "engine": "CosyVoice2",
            "output": {"path": str(candidate), "sha256": MODULE.sha256(candidate)},
            "reference_speaker": {"path": str(reference), "sha256": MODULE.sha256(reference)},
            "dialogue": {
                "text": "A real line.",
                "style_emotion_required": "focused",
                "style_intensity_required": "controlled",
            },
            "gates": {"independent_reference_speaker_bound": True},
            "boundaries": {"final_voice_certification_claimed": False},
        }
        return candidate, reference, manifest

    def test_candidate_lineage_accepts_exact_source_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, reference, manifest = self._fixture(Path(temporary))
            result = MODULE.verify_candidate_lineage(manifest, candidate, MODULE.sha256(candidate))
            self.assertEqual(result, (reference, "A real line.", "focused", "controlled"))

    def test_candidate_lineage_rejects_candidate_hash_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, manifest = self._fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, "candidate SHA-256"):
                MODULE.verify_candidate_lineage(manifest, candidate, "0" * 64)

    def test_candidate_lineage_rejects_reference_hash_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, reference, manifest = self._fixture(Path(temporary))
            reference.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "reference-speaker"):
                MODULE.verify_candidate_lineage(manifest, candidate, MODULE.sha256(candidate))

    def test_candidate_lineage_rejects_certification_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, manifest = self._fixture(Path(temporary))
            manifest["boundaries"]["final_voice_certification_claimed"] = True
            with self.assertRaisesRegex(ValueError, "improperly claims"):
                MODULE.verify_candidate_lineage(manifest, candidate, MODULE.sha256(candidate))

    def test_classification_prioritizes_timing_failure(self):
        gates = {
            "dialogue_timing_pass": False,
            "candidate_asr_pass": True,
            "candidate_reference_speaker_identity_pass": True,
        }
        self.assertEqual(MODULE.classify(gates), "FAIL_COSYVOICE2_DIALOGUE_TIMING")

    def test_classification_allows_narrow_content_speaker_pass_only(self):
        gates = {
            "dialogue_timing_pass": True,
            "candidate_asr_pass": True,
            "candidate_reference_speaker_identity_pass": True,
        }
        self.assertEqual(
            MODULE.classify(gates),
            "PASS_COSYVOICE2_CONTENT_SPEAKER_TECHNICAL_STYLE_AUTHORITY_BLOCKED",
        )

    def test_load_json_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                MODULE.load_json(path, "0" * 64, "record")

    def test_metric_gates_compute_narrow_results_and_leave_intensity_unmeasured(self):
        gates = MODULE.build_metric_gates(
            wer=4.8,
            max_wer=0.2,
            similarity=0.3992827236652374,
            threshold=0.33445611596107483,
            dnsmos_ovrl=2.884593350272355,
            reference_mos=[2.5, 3.0, 3.5],
            timing_pass=False,
            target_emotion="focused",
            emotion_labels=["neutral", "sad"],
        )
        self.assertFalse(gates["candidate_asr_pass"])
        self.assertTrue(gates["candidate_reference_speaker_identity_pass"])
        self.assertTrue(gates["candidate_dnsmos_worst_reference_floor_pass"])
        self.assertIsNone(gates["candidate_dnsmos_quality_certification_pass"])
        self.assertFalse(gates["dialogue_timing_pass"])
        self.assertFalse(gates["target_emotion_taxonomy_supported"])
        self.assertIsNone(gates["target_intensity_taxonomy_supported"])
        self.assertEqual(
            gates["target_intensity_taxonomy_status"],
            "unmeasured_no_calibrated_intensity_evaluator",
        )
        self.assertFalse(gates["production_proof_authority_pass"])

    def test_metric_gates_reject_empty_dnsmos_reference(self):
        with self.assertRaisesRegex(ValueError, "calibration is empty"):
            MODULE.build_metric_gates(
                wer=0.0,
                max_wer=0.2,
                similarity=1.0,
                threshold=0.3,
                dnsmos_ovrl=4.0,
                reference_mos=[],
                timing_pass=True,
                target_emotion="neutral",
                emotion_labels=["neutral"],
            )

    def test_deployable_speaker_threshold_requires_held_out_pass(self):
        evidence = {
            "threshold_validation": {"threshold": 0.33445611596107483},
            "acceptance": {"speaker_disjoint_threshold_generalization_pass": True},
        }
        self.assertEqual(
            MODULE.require_deployable_speaker_threshold(evidence), 0.33445611596107483
        )
        evidence["acceptance"]["speaker_disjoint_threshold_generalization_pass"] = False
        with self.assertRaisesRegex(ValueError, "not deployable"):
            MODULE.require_deployable_speaker_threshold(evidence)


if __name__ == "__main__":
    unittest.main()
