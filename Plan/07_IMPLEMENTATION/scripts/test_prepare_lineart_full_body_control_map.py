#!/usr/bin/env python3
"""Unit tests for Lineart full-body control-map preparation helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_lineart_full_body_control_map import (  # noqa: E402
    EXPECTED_SOURCE_SHA256,
    ROOT,
    run_fail_closed_checks,
    source_selection_checks,
    validate_active_input_name,
)


class PrepareLineartFullBodyTests(unittest.TestCase):
    def test_validate_active_input_name_rejects_path_traversal(self) -> None:
        with self.assertRaises(ValueError):
            validate_active_input_name("../control.png")
        with self.assertRaises(ValueError):
            validate_active_input_name("control.jpg")
        self.assertEqual(
            validate_active_input_name("controlnet_lineart_full_body_standing_w70_v1.png"),
            "controlnet_lineart_full_body_standing_w70_v1.png",
        )

    def test_source_selection_checks_require_full_folder_and_expected_hash(self) -> None:
        source_ok = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
        checks_ok = source_selection_checks(source_ok, EXPECTED_SOURCE_SHA256)
        self.assertTrue(all(checks_ok.values()))

        source_bad = ROOT / "Ref_Image_1/Full/New folder/example.jpg"
        checks_bad = source_selection_checks(source_bad, "1234")
        self.assertFalse(checks_bad["source_outside_excluded_new_folder"])
        self.assertFalse(checks_bad["source_sha256_matches_expected"])

    def test_run_fail_closed_checks_require_nonblank_and_models(self) -> None:
        checks = run_fail_closed_checks(
            source_size=(704, 1056),
            control_size=(704, 1056),
            control_bytes=100,
            source_checks={
                "source_is_ref_image_1_full": True,
                "source_outside_excluded_new_folder": True,
                "source_sha256_matches_expected": True,
            },
            model_records=[
                {
                    "filename": "sk_model.pth",
                    "exists": True,
                    "sha256_matches_expected": True,
                },
                {
                    "filename": "sk_model2.pth",
                    "exists": False,
                    "sha256_matches_expected": False,
                },
            ],
            stats={
                "std": 8.0,
                "bright_contour_pixel_ratio": 0.04,
                "high_confidence_contour_pixel_ratio": 0.003,
                "dark_background_pixel_ratio": 0.95,
            },
        )
        self.assertFalse(checks["required_lineart_models_hash_trusted"])
        self.assertTrue(checks["line_map_not_blank_by_std"])
        self.assertTrue(checks["bright_contour_ratio_gte_0_01"])

    def test_run_fail_closed_checks_accepts_detector_resolution_with_same_aspect(self) -> None:
        checks = run_fail_closed_checks(
            source_size=(3000, 4000),
            control_size=(1024, 1365),
            control_bytes=100,
            source_checks={
                "source_is_ref_image_1_full": True,
                "source_outside_excluded_new_folder": True,
                "source_sha256_matches_expected": True,
            },
            model_records=[
                {
                    "filename": "sk_model.pth",
                    "exists": True,
                    "sha256_matches_expected": True,
                },
                {
                    "filename": "sk_model2.pth",
                    "exists": True,
                    "sha256_matches_expected": True,
                },
            ],
            stats={
                "std": 18.0,
                "bright_contour_pixel_ratio": 0.028,
                "high_confidence_contour_pixel_ratio": 0.012,
                "dark_background_pixel_ratio": 0.96,
            },
        )
        self.assertTrue(all(checks.values()))


if __name__ == "__main__":
    unittest.main()
