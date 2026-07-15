import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/package_wave64_cv3_emotion_evidence.py"
SPEC = importlib.util.spec_from_file_location("package_wave64_cv3_emotion_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def calibration_fixture():
    return {
        "classification": "W64_EMOTION2VEC_EXECUTION_PASS_TAXONOMY_BLOCKED",
        "calibration": {
            "metrics": {
                "sample_count": 300,
                "accuracy": 0.7233333333333334,
                "macro_f1": 0.7967110893382565,
            }
        },
        "candidate": {
            "predicted_label": "neutral",
            "target_emotion_supported": False,
            "target_intensity_supported": False,
            "emotion_pass": None,
        },
        "gates": {
            "emotion_model_execution_pass": True,
            "production_emotion_authority_pass": False,
            "row_completion_pass": False,
            "final_voice_certification_pass": False,
        },
    }


class CV3EmotionEvidenceTests(unittest.TestCase):
    def test_verify_calibration_accepts_observed_fail_closed_result(self):
        MODULE.verify_calibration(calibration_fixture())

    def test_verify_calibration_rejects_false_emotion_promotion(self):
        payload = calibration_fixture()
        payload["candidate"]["emotion_pass"] = True
        with self.assertRaisesRegex(ValueError, "must remain unresolved"):
            MODULE.verify_calibration(payload)

    def test_write_exact_creates_identical_mirrors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root / "qa.json", root / "tracker.json"]
            digest = MODULE.write_exact({"row_complete": False}, paths)
            self.assertEqual(MODULE.sha256(paths[0]), digest)
            self.assertEqual(MODULE.sha256(paths[1]), digest)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())


if __name__ == "__main__":
    unittest.main()
