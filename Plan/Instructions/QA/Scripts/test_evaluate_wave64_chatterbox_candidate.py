import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_chatterbox_candidate.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_chatterbox_candidate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class EvaluateWave64ChatterboxCandidateTests(unittest.TestCase):
    def fixture(self, base: Path):
        candidate = base / "candidate.wav"
        reference = base / "reference.wav"
        runner = base / "runner.py"
        candidate.write_bytes(b"candidate")
        reference.write_bytes(b"reference")
        runner.write_text("MODEL_ID='ResembleAI/chatterbox'\nMODEL_REVISION='rev'\nEXPECTED_MODEL_HASHES={'a':'b'}\n", encoding="utf-8")
        contract = {
            "text": "A real line.",
            "style_emotion": "focused",
            "style_intensity": "controlled",
        }
        contract_hash = MODULE.hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        manifest = {
            "engine": "ChatterboxTTS",
            "output": {
                "path": str(candidate),
                "sha256": MODULE.sha256(candidate),
                "perth_watermark_detected": True,
                "perth_watermark_score": 1.0,
            },
            "reference_speaker": {"path": str(reference), "sha256": MODULE.sha256(reference)},
            "dialogue": {
                "text": "A real line.",
                "style_emotion_required": "focused",
                "style_intensity_required": "controlled",
            },
            "runtime": {
                "post_generation_truncation_applied": False,
                "post_generation_time_stretch_applied": False,
            },
            "native_controls": {
                "controls_predeclared_before_generation": True,
                "controls_tuned_against_candidate_result": False,
                "style_contract_verified": False,
            },
            "implementation": {
                "runner_path": str(runner),
                "runner_sha256": MODULE.sha256(runner),
                "control_contract": contract,
                "control_contract_sha256": contract_hash,
            },
            "model": {
                "model_id": "ResembleAI/chatterbox",
                "revision": "rev",
                "payloads": [{"path": "a", "sha256": "b"}],
            },
            "gates": {"independent_reference_speaker_bound": True},
            "boundaries": {
                "watermark_removed": False,
                "authorized_candidate_ordinal": 1,
                "maximum_candidates_for_control_path": 1,
                "same_control_path_retry_allowed": False,
                "final_voice_certification_claimed": False,
            },
        }
        return candidate, reference, runner, manifest

    def test_lineage_accepts_exact_chatterbox_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, reference, runner, manifest = self.fixture(Path(temporary))
            result = MODULE.verify_candidate_lineage(
                manifest, candidate, MODULE.sha256(candidate), runner, MODULE.sha256(runner)
            )
            self.assertEqual(result, (reference, "A real line.", "focused", "controlled"))

    def test_lineage_rejects_candidate_hash_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, runner, manifest = self.fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, "candidate SHA-256"):
                MODULE.verify_candidate_lineage(manifest, candidate, "0" * 64, runner, MODULE.sha256(runner))

    def test_lineage_rejects_runner_hash_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, runner, manifest = self.fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, "runner SHA-256"):
                MODULE.verify_candidate_lineage(manifest, candidate, MODULE.sha256(candidate), runner, "0" * 64)

    def test_lineage_rejects_control_contract_hash_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, runner, manifest = self.fixture(Path(temporary))
            manifest["implementation"]["control_contract"]["style_emotion"] = "happy"
            with self.assertRaisesRegex(ValueError, "control-contract SHA-256"):
                MODULE.verify_candidate_lineage(
                    manifest, candidate, MODULE.sha256(candidate), runner, MODULE.sha256(runner)
                )

    def test_lineage_rejects_missing_watermark(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, runner, manifest = self.fixture(Path(temporary))
            manifest["output"]["perth_watermark_detected"] = False
            with self.assertRaisesRegex(ValueError, "watermark"):
                MODULE.verify_candidate_lineage(
                    manifest, candidate, MODULE.sha256(candidate), runner, MODULE.sha256(runner)
                )

    def test_lineage_rejects_postprocessing(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, runner, manifest = self.fixture(Path(temporary))
            manifest["runtime"]["post_generation_time_stretch_applied"] = True
            with self.assertRaisesRegex(ValueError, "time stretching"):
                MODULE.verify_candidate_lineage(
                    manifest, candidate, MODULE.sha256(candidate), runner, MODULE.sha256(runner)
                )

    def test_lineage_rejects_retry_permission(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _, runner, manifest = self.fixture(Path(temporary))
            manifest["boundaries"]["same_control_path_retry_allowed"] = True
            with self.assertRaisesRegex(ValueError, "same-path retry"):
                MODULE.verify_candidate_lineage(
                    manifest, candidate, MODULE.sha256(candidate), runner, MODULE.sha256(runner)
                )

    def test_classification_prioritizes_timing_failure(self):
        self.assertEqual(
            MODULE.classify({"dialogue_timing_pass": False}),
            "FAIL_CHATTERBOX_DIALOGUE_TIMING",
        )

    def test_classification_allows_narrow_pass_only(self):
        gates = {
            "dialogue_timing_pass": True,
            "candidate_asr_pass": True,
            "candidate_reference_speaker_identity_pass": True,
            "candidate_dnsmos_worst_reference_floor_pass": True,
        }
        self.assertEqual(
            MODULE.classify(gates),
            "PASS_CHATTERBOX_CONTENT_SPEAKER_TECHNICAL_STYLE_AUTHORITY_BLOCKED",
        )

    def test_metric_gates_leave_style_and_authority_fail_closed(self):
        gates = MODULE.build_metric_gates(
            wer=0.0,
            max_wer=0.2,
            similarity=0.5,
            threshold=0.3,
            dnsmos_ovrl=3.0,
            reference_mos=[2.5, 3.5],
            timing_pass=False,
            target_emotion="focused",
            emotion_labels=["neutral", "happy"],
        )
        self.assertTrue(gates["candidate_asr_pass"])
        self.assertFalse(gates["dialogue_timing_pass"])
        self.assertFalse(gates["target_emotion_taxonomy_supported"])
        self.assertIsNone(gates["candidate_style_intensity_pass"])
        self.assertFalse(gates["production_proof_authority_pass"])

    def test_speaker_threshold_requires_disjoint_validation(self):
        evidence = {
            "threshold_validation": {"threshold": 0.33445611596107483},
            "acceptance": {"speaker_disjoint_threshold_generalization_pass": True},
        }
        self.assertEqual(MODULE.require_deployable_speaker_threshold(evidence), 0.33445611596107483)
        evidence["acceptance"]["speaker_disjoint_threshold_generalization_pass"] = False
        with self.assertRaisesRegex(ValueError, "not deployable"):
            MODULE.require_deployable_speaker_threshold(evidence)

    def test_timing_blocker_names_current_candidate(self):
        self.assertEqual(
            MODULE.timing_blocker(3.92, 3.0),
            "the 3.92-second Chatterbox candidate exceeds the 3.0-second dialogue contract",
        )


if __name__ == "__main__":
    unittest.main()
