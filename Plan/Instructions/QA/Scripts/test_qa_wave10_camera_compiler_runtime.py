#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = PROJECT_ROOT / "Plan" / "07_IMPLEMENTATION" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from qa_wave10_camera_compiler_runtime import (  # noqa: E402
    REQUIRED_VISUAL_CHECKS,
    body_points,
    final_result,
    framing_keypoints_in_frame,
    nonblank_metrics,
    validate_visual_disposition,
)


def keypoint_payload() -> dict:
    raw = []
    for index in range(18):
        raw.extend([100 + index, 200 + index, 1.0])
    return {
        "canvas_width": 768,
        "canvas_height": 1024,
        "people": [{"pose_keypoints_2d": raw}],
    }


class Wave10CameraRuntimeQaTests(unittest.TestCase):
    def test_body_points_normalize_all_18_landmarks(self) -> None:
        points = body_points(keypoint_payload())
        self.assertEqual(len(points), 18)
        self.assertAlmostEqual(points[0][0], 100 / 768)
        self.assertAlmostEqual(points[13][1], 213 / 1024)

    def test_framing_points_require_head_wrists_and_ankles(self) -> None:
        points = body_points(keypoint_payload())
        self.assertTrue(framing_keypoints_in_frame(points))
        points.pop(13)
        self.assertFalse(framing_keypoints_in_frame(points))

    def test_nonblank_metrics_pass_varied_image(self) -> None:
        pixels = np.full((64, 64, 3), 10, dtype=np.uint8)
        pixels[:, 32:, :] = 220
        self.assertTrue(nonblank_metrics(Image.fromarray(pixels))["pass"])

    def test_visual_disposition_fail_is_valid_contract(self) -> None:
        checks = {name: True for name in REQUIRED_VISUAL_CHECKS}
        checks["both_hands_fully_visible_and_inspectable"] = False
        checks["no_required_region_hidden"] = False
        payload = {
            "image_sha256": "a" * 64,
            "original_resolution_review": True,
            "checks": checks,
            "result": "fail",
        }
        contract_valid, visual_pass, issues = validate_visual_disposition(payload, "a" * 64)
        self.assertTrue(contract_valid)
        self.assertFalse(visual_pass)
        self.assertEqual(issues, [])

    def test_final_result_blocks_visual_failure_without_retry(self) -> None:
        self.assertEqual(
            final_result(True, True, False),
            ("fail_visual_runtime_composition_mismatch", "Blocked_Visual_Runtime_Composition_Mismatch"),
        )

    def test_visual_failure_cannot_be_reclassified_as_overall_pass(self) -> None:
        result, status = final_result(True, True, False)
        self.assertNotEqual(result, "pass_wave10_camera_compiler_runtime_qa")
        self.assertEqual(status, "Blocked_Visual_Runtime_Composition_Mismatch")


if __name__ == "__main__":
    unittest.main()
