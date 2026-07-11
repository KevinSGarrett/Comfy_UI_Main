#!/usr/bin/env python3
"""Unit tests for Canny full-body control-map preparation helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_canny_full_body_control_map import (  # noqa: E402
    EXPECTED_SOURCE_SHA256,
    ROOT,
    run_fail_closed_checks,
    source_selection_checks,
    validate_canny_parameters,
)


class PrepareCannyFullBodyTests(unittest.TestCase):
    def test_source_selection_checks_require_full_folder_and_expected_hash(self) -> None:
        source_ok = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
        checks_ok = source_selection_checks(source_ok, EXPECTED_SOURCE_SHA256)
        self.assertTrue(all(checks_ok.values()))

        source_bad = ROOT / "Ref_Image_1/Full/New folder/example.jpg"
        checks_bad = source_selection_checks(source_bad, "1234")
        self.assertFalse(checks_bad["source_outside_excluded_new_folder"])
        self.assertFalse(checks_bad["source_sha256_matches_expected"])

    def test_validate_canny_parameters_rejects_non_authoritative_values(self) -> None:
        validate_canny_parameters(kernel=(5, 5), sigma=1.4, low=100, high=200)
        with self.assertRaises(ValueError):
            validate_canny_parameters(kernel=(3, 3), sigma=1.4, low=100, high=200)
        with self.assertRaises(ValueError):
            validate_canny_parameters(kernel=(5, 5), sigma=0.9, low=100, high=200)
        with self.assertRaises(ValueError):
            validate_canny_parameters(kernel=(5, 5), sigma=1.4, low=50, high=150)

    def test_run_fail_closed_checks_require_edge_density_and_nonblank(self) -> None:
        checks = run_fail_closed_checks(
            source_size=(1536, 2048),
            control_size=(768, 1024),
            control_bytes=100,
            source_checks={
                "source_is_ref_image_1_full": True,
                "source_outside_excluded_new_folder": True,
                "source_sha256_matches_expected": True,
            },
            stats={
                "min": 0.0,
                "max": 255.0,
                "std": 12.0,
                "edge_density": 0.08,
                "black_pixel_ratio": 0.92,
                "unique_values": [0, 255],
            },
            source_sha256="abc",
            source_copy_sha256="abc",
        )
        self.assertTrue(all(checks.values()))

        failing = run_fail_closed_checks(
            source_size=(1536, 2048),
            control_size=(768, 1024),
            control_bytes=100,
            source_checks={
                "source_is_ref_image_1_full": True,
                "source_outside_excluded_new_folder": True,
                "source_sha256_matches_expected": True,
            },
            stats={
                "min": 0.0,
                "max": 255.0,
                "std": 1.0,
                "edge_density": 0.001,
                "black_pixel_ratio": 0.99,
                "unique_values": [0, 255],
            },
            source_sha256="abc",
            source_copy_sha256="abc",
        )
        self.assertFalse(failing["edge_map_not_blank_by_std"])
        self.assertFalse(failing["edge_density_gte_0_005"])

    def test_run_fail_closed_checks_reject_nonbinary_pixels_and_copy_drift(self) -> None:
        checks = run_fail_closed_checks(
            source_size=(1536, 2048),
            control_size=(768, 1024),
            control_bytes=100,
            source_checks={
                "source_is_ref_image_1_full": True,
                "source_outside_excluded_new_folder": True,
                "source_sha256_matches_expected": True,
            },
            stats={
                "min": 0.0,
                "max": 255.0,
                "std": 12.0,
                "edge_density": 0.08,
                "black_pixel_ratio": 0.92,
                "unique_values": [0, 127, 255],
            },
            source_sha256="abc",
            source_copy_sha256="def",
        )
        self.assertFalse(checks["control_map_binary_uint8_0_255_only"])
        self.assertFalse(checks["control_map_contains_black_and_white"])
        self.assertFalse(checks["source_copy_hash_matches_source"])


if __name__ == "__main__":
    unittest.main()
