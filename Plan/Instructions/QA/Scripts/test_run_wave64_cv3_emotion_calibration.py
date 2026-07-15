import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/run_wave64_cv3_emotion_calibration.py"
SPEC = importlib.util.spec_from_file_location("run_wave64_cv3_emotion_calibration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CV3EmotionCalibrationTests(unittest.TestCase):
    def test_cv3_emotion_maps_are_exactly_pinned(self):
        self.assertEqual(set(MODULE.CV3_EMOTION_MAP_HASHES), {"en", "zh"})
        self.assertTrue(all(len(value) == 64 for value in MODULE.CV3_EMOTION_MAP_HASHES.values()))

    def test_model_token_normalization(self):
        self.assertEqual(MODULE.normalize_model_token("happy/happy"), "happy")
        self.assertEqual(MODULE.normalize_model_token("<unk>"), "unknown")
        self.assertEqual(MODULE.normalize_model_token("<surprised>"), "surprised")

    def test_read_model_labels_accepts_authoritative_taxonomy(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tokens.txt"
            path.write_text(
                "\n".join(
                    [
                        "angry/angry",
                        "disgusted/disgusted",
                        "fearful/fearful",
                        "happy/happy",
                        "neutral/neutral",
                        "other/other",
                        "sad/sad",
                        "surprised/surprised",
                        "<unk>",
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(MODULE.read_model_labels(path), MODULE.EXPECTED_MODEL_LABELS)

    def test_read_model_labels_rejects_stale_unused_classes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tokens.txt"
            path.write_text("angry\nunuse_0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "taxonomy mismatch"):
                MODULE.read_model_labels(path)

    def test_parse_inference_result_selects_highest_score(self):
        scores = [0.01] * 9
        scores[3] = 0.91
        parsed = MODULE.parse_inference_result([{"scores": scores}], MODULE.EXPECTED_MODEL_LABELS)
        self.assertEqual(parsed["predicted_label"], "happy")
        self.assertEqual(parsed["predicted_score"], 0.91)

    def test_parse_inference_result_rejects_non_finite_score(self):
        scores = [0.01] * 9
        scores[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            MODULE.parse_inference_result([{"scores": scores}], MODULE.EXPECTED_MODEL_LABELS)

    def test_parse_inference_result_rejects_wrong_score_count(self):
        with self.assertRaisesRegex(ValueError, "invalid score vector"):
            MODULE.parse_inference_result([{"scores": [0.5, 0.5]}], MODULE.EXPECTED_MODEL_LABELS)

    def test_score_metrics_computes_accuracy_and_macro_f1(self):
        records = [
            {"language": "en", "reference_label": "angry", "intensity": "high", "predicted_label": "angry"},
            {"language": "en", "reference_label": "happy", "intensity": "high", "predicted_label": "sad"},
            {"language": "en", "reference_label": "sad", "intensity": "high", "predicted_label": "sad"},
        ]
        metrics = MODULE.score_metrics(records)
        self.assertAlmostEqual(metrics["accuracy"], 2 / 3)
        self.assertEqual(metrics["confusion"]["happy"]["sad"], 1)
        self.assertAlmostEqual(metrics["macro_f1"], (1.0 + 0.0 + (2 / 3)) / 3)

    def test_select_records_preserves_every_stratum(self):
        records = []
        for language in MODULE.CV3_LANGUAGES:
            for label in MODULE.CV3_REFERENCE_LABELS:
                for intensity in MODULE.CV3_INTENSITIES:
                    for index in range(25):
                        records.append(
                            {
                                "language": language,
                                "reference_label": label,
                                "intensity": intensity,
                                "utterance_index": index + 1,
                            }
                        )
        selected = MODULE.select_records(records, 2)
        self.assertEqual(len(selected), 24)
        self.assertEqual({record["utterance_index"] for record in selected}, {1, 2})

    def test_select_records_rejects_out_of_range_limit(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 25"):
            MODULE.select_records([], 26)

    def test_candidate_lineage_preserves_unsupported_contract_terms(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = (root / "line.wav").resolve()
            candidate.write_bytes(b"candidate")
            candidate_hash = MODULE.sha256(candidate)
            packet = root / "packet.json"
            packet.write_text(
                json.dumps(
                    {
                        "result": "pass",
                        "execution_passed": True,
                        "verified_media": {"media_path": str(candidate), "sha256": candidate_hash},
                        "timeline_conformance": {"speech_truncated": False},
                    }
                ),
                encoding="utf-8",
            )
            contract = root / "contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "lines": [
                            {
                                "line_id": "L001",
                                "output_file": str(candidate),
                                "emotion": "focused",
                                "intensity": "controlled",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            lineage = MODULE.bind_candidate_lineage(
                candidate,
                candidate_hash,
                packet,
                MODULE.sha256(packet),
                contract,
                MODULE.sha256(contract),
            )
            self.assertEqual(lineage["target_emotion"], "focused")
            self.assertEqual(lineage["target_intensity"], "controlled")
            self.assertNotIn(lineage["target_emotion"], MODULE.EXPECTED_MODEL_LABELS)

    def test_require_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.bin"
            path.write_bytes(b"exact")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                MODULE.require_hash(path, "0" * 64, "fixture")


if __name__ == "__main__":
    unittest.main()
