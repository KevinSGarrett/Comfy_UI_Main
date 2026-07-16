from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "run_wave64_speech_acoustics.py"
SPEC = importlib.util.spec_from_file_location("speech_acoustics_runner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechAcousticsRunnerTests(unittest.TestCase):
    def test_renderers_are_finite_and_preserve_speech_length(self) -> None:
        rate = 24000
        time = np.arange(rate, dtype=np.float64) / rate
        signal = 0.12 * np.sin(2.0 * np.pi * 180.0 * time)
        nonverbal, _ = MODULE.render_nonverbal(signal, rate)
        microphone, recipe = MODULE.render_virtual_microphone(signal, rate)
        restored, restoration = MODULE.restore_speech(microphone, rate)
        self.assertEqual(signal.size, nonverbal.size)
        self.assertEqual(signal.size, microphone.size)
        self.assertEqual(signal.size, restored.size)
        self.assertTrue(np.isfinite(nonverbal).all())
        self.assertTrue(np.isfinite(microphone).all())
        self.assertTrue(np.isfinite(restored).all())
        self.assertTrue(recipe["nondestructive_source_retained"])
        self.assertTrue(restoration["source_and_intermediate_retained"])
        self.assertLessEqual(restoration["declick_repair_sample_ratio"], 0.001)

    def test_declick_repairs_an_isolated_impulse_only(self) -> None:
        rate = 24000
        source = np.zeros(rate, dtype=np.float64)
        source[rate // 2] = 0.9
        restored, recipe = MODULE.restore_speech(source, rate)
        self.assertEqual(1, recipe["declick_samples_repaired"])
        self.assertLess(abs(float(restored[rate // 2])), 0.01)

    def test_index_record_must_be_unique_and_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "index.jsonl"
            record = {
                "sha256": "a" * 64,
                "absolute_path": "x.wav",
                "relative_path": "x.wav",
                "bytes": 10,
                "duration_seconds": 1.0,
                "format": "wav",
                "sample_rate_hz": 24000,
                "channels": 1,
                "event_type": "breath",
                "role": "voice",
                "intensity_band": "low",
                "sync_class": "windowed",
                "license_classification": "CC0-1.0",
                "attribution": "test",
                "quality_defects": [],
                "content_based_suppression": False,
            }
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            self.assertEqual("breath", MODULE.find_index_record(path, "a" * 64)["event_type"])
            path.write_text(json.dumps({**record, "content_based_suppression": True}) + "\n", encoding="utf-8")
            with self.assertRaises(MODULE.AcousticsError):
                MODULE.find_index_record(path, "a" * 64)

    def test_peak_limit_never_amplifies(self) -> None:
        source = np.array([-2.0, 0.0, 2.0], dtype=np.float64)
        output, gain = MODULE.peak_limit(source, 0.95)
        self.assertLess(gain, 1.0)
        self.assertLessEqual(float(np.max(np.abs(output))), 0.95)


if __name__ == "__main__":
    unittest.main()
