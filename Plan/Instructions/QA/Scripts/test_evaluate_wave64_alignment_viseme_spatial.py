#!/usr/bin/env python3
"""Focused regression tests for the Rows135, 136, and 138 evaluator."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_alignment_viseme_spatial.py"
SPEC = importlib.util.spec_from_file_location("wave64_alignment_viseme_spatial_evaluator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Wave64AlignmentVisemeSpatialEvaluatorTests(unittest.TestCase):
    def test_spatial_inspection_detects_expected_motion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spatial.wav"
            rate = 24000
            left = np.column_stack((np.ones(rate // 2) * 0.2, np.ones(rate // 2) * 0.05))
            right = np.column_stack((np.ones(rate // 2) * 0.05, np.ones(rate // 2) * 0.2))
            sf.write(str(path), np.vstack((left, right)).astype(np.float32), rate, subtype="PCM_24")
            metrics, _, observed_rate = MODULE.inspect_spatial(path)
            self.assertEqual(observed_rate, rate)
            self.assertTrue(metrics["trajectory_channel_motion_pass"])
            self.assertEqual(metrics["channels"], 2)
            self.assertEqual(metrics["clipping_ratio"], 0.0)

    def test_spatial_inspection_rejects_mono(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mono.wav"
            sf.write(str(path), np.zeros(24000, dtype=np.float32), 24000)
            with self.assertRaises(MODULE.EvaluationError):
                MODULE.inspect_spatial(path)

    def test_manifest_authority_claims_fail_closed(self) -> None:
        base = {
            "classification": MODULE.EXPECTED_MANIFEST_CLASSIFICATION,
            "source": {"sha256": MODULE.EXPECTED_SOURCE_SHA256, "transcript": MODULE.EXPECTED_TEXT, "source_unchanged_after_runtime": True},
            "row135": {"word_alignment_pass": True, "phoneme_alignment_pass": False, "row_complete": False, "alignment": {}},
            "row136": {"fixture_runtime_pass": True, "production_input_pass": False, "row_complete": False, "fixture": {}},
            "row138": {"row_complete": False, "output": {}},
            "boundaries": {
                "mms_grapheme_is_phoneme_authority": False,
                "fixture_is_production_alignment": False,
                "automated_metrics_are_human_playback": False,
                "production_ready": False,
            },
        }
        for key in base["boundaries"]:
            invalid = copy.deepcopy(base)
            invalid["boundaries"][key] = True
            with self.assertRaises(MODULE.EvaluationError):
                MODULE.verify_runtime_manifest(invalid)

    def test_source_contains_required_blocked_gates(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"phoneme_authority_pass": False', source)
        self.assertIn('"independent_playback_review_pass": False', source)
        self.assertIn('"production_scene_authority_pass": False', source)
        self.assertIn('"row_complete": False', source)


if __name__ == "__main__":
    unittest.main()
