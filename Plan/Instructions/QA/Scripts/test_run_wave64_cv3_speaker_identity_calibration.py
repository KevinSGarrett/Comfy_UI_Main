import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/run_wave64_cv3_speaker_identity_calibration.py"
)
SPEC = importlib.util.spec_from_file_location("run_wave64_cv3_speaker_identity_calibration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CV3SpeakerIdentityCalibrationTests(unittest.TestCase):
    def test_parse_kaldi_map_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map.scp"
            path.write_text("same first\nsame second\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate Kaldi key"):
                MODULE.parse_kaldi_map(path)

    def test_resolve_cv3_waveform_repairs_only_published_legacy_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            waveform = root / "data/subjective_continue/emotion/en/waveform/prompt_audio_1.wav"
            waveform.parent.mkdir(parents=True)
            waveform.write_bytes(b"wave")
            resolved = MODULE.resolve_cv3_waveform(
                root,
                "data/subjective_zeroshot_continue/emotion/en/waveform/prompt_audio_1.wav",
            )
            self.assertEqual(resolved, waveform)
            with self.assertRaisesRegex(ValueError, "unsupported CV3 waveform map prefix"):
                MODULE.resolve_cv3_waveform(root, "other/prompt_audio_1.wav")

    def test_rates_computes_balanced_metrics(self):
        result = MODULE.rates([True, True, False, False], [0.9, 0.4, 0.6, 0.1], 0.5)
        self.assertEqual(result["true_positive_rate"], 0.5)
        self.assertEqual(result["false_positive_rate"], 0.5)
        self.assertEqual(result["balanced_accuracy"], 0.5)

    def test_select_threshold_requires_high_tpr_and_low_fpr(self):
        threshold, result = MODULE.select_threshold(
            [True] * 10 + [False] * 10,
            [0.9] * 10 + [0.1] * 10,
        )
        self.assertTrue(result["training_constraints_pass"])
        self.assertGreater(threshold, 0.1)
        self.assertLess(threshold, 0.9)

    def test_select_threshold_reports_failed_constraints_for_overlap(self):
        _, result = MODULE.select_threshold(
            [True] * 10 + [False] * 10,
            [0.4] * 10 + [0.6] * 10,
        )
        self.assertFalse(result["training_constraints_pass"])

    def test_extract_segments_rejects_same_source_and_stem(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            audio = root / "same.wav"
            audio.write_bytes(b"same")
            digest = MODULE.sha256(audio)
            manifest = {
                "source_bindings": {
                    "voice_source": {
                        "path": str(audio),
                        "sha256": digest,
                        "excerpt_start_seconds": 0,
                        "excerpt_end_seconds": 1,
                    }
                },
                "outputs": {"voice_stem": {"path": str(audio), "sha256": digest}},
                "sync": {"voice_start_seconds": 0},
            }
            with self.assertRaisesRegex(ValueError, "distinct artifacts"):
                MODULE.extract_segments(manifest, root)

    def test_delivery_evidence_binding_requires_exact_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "evidence.json"
            payload = {"status": "PASS", "delivery": {"manifest_path": "wrong.json"}}
            path.write_text(json.dumps(payload), encoding="utf-8")
            binding, observed = MODULE.load_json_binding(
                path, MODULE.sha256(path), "evidence"
            )
            self.assertEqual(binding["sha256"], MODULE.sha256(path))
            self.assertEqual(observed["delivery"]["manifest_path"], "wrong.json")

    def test_published_binding_records_final_path_and_source_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "temporary.wav"
            source.write_bytes(b"voice")
            published = root / "final" / "voice.wav"
            binding = MODULE.published_binding(source, published)
            self.assertEqual(binding["path"], str(published))
            self.assertEqual(binding["sha256"], MODULE.sha256(source))
            self.assertEqual(binding["bytes"], 5)


if __name__ == "__main__":
    unittest.main()
