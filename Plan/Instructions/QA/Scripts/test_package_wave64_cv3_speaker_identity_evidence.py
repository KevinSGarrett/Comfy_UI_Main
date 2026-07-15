import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/package_wave64_cv3_speaker_identity_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("package_wave64_cv3_speaker_identity_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def calibration_fixture():
    return {
        "status": "BLOCKED_SPEAKER_CALIBRATION_OR_CHAIN_IDENTITY_THRESHOLD",
        "dataset": {"pair_count": 46},
        "calibration": {
            "cross_validation_pass": False,
            "folds": [
                {
                    "held_out_category": category,
                    "fold_pass": category != "emotion",
                    "held_out": {
                        "false_positive_rate": (
                            0.15416666666666667 if category == "emotion" else 0.01
                        )
                    },
                }
                for category in ("emotion", "rhyme", "speed", "volume")
            ],
            "full_fit": {"deployment_threshold_allowed": False},
        },
        "chain_specific_evaluation": {
            "speaker_similarity": 0.9932656288146973,
            "chain_specific_identity_preservation_pass": False,
        },
        "acceptance": {
            "universal_biometric_identity_claim_allowed": False,
            "parler_candidate_reference_identity_claim_allowed": False,
            "emotion_or_style_claim_allowed": False,
            "independent_perceptual_playback_review_pass": False,
            "production_review_authority_allowed": False,
            "authority_registry_mutation_allowed": False,
            "row_completion_allowed": False,
        },
        "row_complete": False,
    }


class PackageCV3SpeakerIdentityEvidenceTests(unittest.TestCase):
    def test_verify_calibration_accepts_exact_blocker(self):
        MODULE.verify_calibration(calibration_fixture())

    def test_verify_calibration_rejects_threshold_promotion(self):
        payload = calibration_fixture()
        payload["calibration"]["full_fit"]["deployment_threshold_allowed"] = True
        with self.assertRaisesRegex(ValueError, "threshold must remain unauthorized"):
            MODULE.verify_calibration(payload)

    def test_verify_calibration_rejects_identity_promotion(self):
        payload = calibration_fixture()
        payload["chain_specific_evaluation"]["chain_specific_identity_preservation_pass"] = True
        with self.assertRaisesRegex(ValueError, "identity preservation must remain unresolved"):
            MODULE.verify_calibration(payload)

    def test_write_exact_produces_identical_mirrors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root / "qa.json", root / "tracker.json"]
            digest = MODULE.write_exact({"status": "BLOCKED"}, paths)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(MODULE.sha256(paths[0]), digest)

    def test_load_bound_json_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            path.write_text(json.dumps({"status": "BLOCKED"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                MODULE.load_bound_json(path, "0" * 64, "fixture")


if __name__ == "__main__":
    unittest.main()
