#!/usr/bin/env python3
"""Focused regression tests for the Wave64 Rows135, 136, and 138 runner."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_alignment_viseme_spatial.py"
SPEC = importlib.util.spec_from_file_location("wave64_alignment_viseme_spatial", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Wave64AlignmentVisemeSpatialTests(unittest.TestCase):
    def test_normalized_words_are_exact(self) -> None:
        self.assertEqual(
            MODULE.normalized_words(MODULE.TRANSCRIPT),
            ["we", "hold", "the", "frame", "steady", "and", "move", "on", "the", "beat"],
        )

    def test_intervals_reject_overlap_and_bad_confidence(self) -> None:
        with self.assertRaises(MODULE.RuntimePacketError):
            MODULE.validate_intervals([
                {"start_sample": 0, "end_sample": 20, "confidence": 1.0},
                {"start_sample": 19, "end_sample": 30, "confidence": 1.0},
            ], 40, "fixture")
        with self.assertRaises(MODULE.RuntimePacketError):
            MODULE.validate_intervals([
                {"start_sample": 0, "end_sample": 20, "confidence": 1.1},
            ], 40, "fixture")

    def test_viseme_fixture_covers_required_categories_without_overlaps(self) -> None:
        fixture = MODULE.compile_viseme_fixture(24000)
        self.assertTrue(fixture["fixture_runtime_pass"])
        self.assertTrue(all(fixture["fixture_coverage"].values()))
        self.assertFalse(fixture["production_phoneme_input_used"])
        self.assertFalse(fixture["row_complete"])
        previous_end = 0
        for interval in fixture["intervals"]:
            self.assertGreaterEqual(interval["start_sample"], previous_end)
            self.assertGreater(interval["end_sample"], interval["start_sample"])
            self.assertFalse(interval["coarticulation"]["cross_interval_overlap"])
            previous_end = interval["end_sample"]

    def test_spatial_renderer_is_deterministic_stereo_and_finite(self) -> None:
        rate = 24000
        time = np.arange(rate, dtype=np.float32) / rate
        source = (0.2 * np.sin(2 * np.pi * 220.0 * time)).astype(np.float32)
        first, first_metadata = MODULE.render_spatial(source, rate)
        second, second_metadata = MODULE.render_spatial(source, rate)
        self.assertEqual(first.shape, (rate, 2))
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(first_metadata, second_metadata)
        self.assertTrue(np.isfinite(first).all())
        self.assertFalse(np.array_equal(first[:, 0], first[:, 1]))
        self.assertLessEqual(float(np.max(np.abs(first))), 0.960001)

    def test_spatial_renderer_rejects_invalid_input(self) -> None:
        with self.assertRaises(MODULE.RuntimePacketError):
            MODULE.render_spatial(np.zeros(10, dtype=np.float32), 24000)
        invalid = np.zeros(24000, dtype=np.float32)
        invalid[100] = np.nan
        with self.assertRaises(MODULE.RuntimePacketError):
            MODULE.render_spatial(invalid, 24000)

    def test_bind_fails_closed_on_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            path.write_bytes(b"fixture")
            binding = MODULE.bind(path)
            self.assertEqual(binding["sha256"], MODULE.sha256_file(path))
            with self.assertRaises(MODULE.RuntimePacketError):
                MODULE.bind(path, "0" * 64)

    def test_authority_constants_do_not_overclaim(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"mms_grapheme_is_phoneme_authority": False', source)
        self.assertIn('"fixture_is_production_alignment": False', source)
        self.assertIn('"automated_metrics_are_human_playback": False', source)
        self.assertIn('"row_complete": False', source)
        self.assertIn("CC-BY-NC-4.0", source)


if __name__ == "__main__":
    unittest.main()
