#!/usr/bin/env python3
"""Unit tests for two-character OpenPose control-map preparation helpers."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_base_two_character_openpose_contact_control_map import (
    run_checks,
    summarize_people,
    validate_active_input_name,
    visible_body_keypoints,
)


class PrepareTwoCharacterOpenPoseTests(unittest.TestCase):
    def test_visible_body_keypoints_counts_confident_triplets(self) -> None:
        person = {"pose_keypoints_2d": [10, 20, 0.9, 11, 21, 0.0, 12, 22, 0.1]}
        self.assertEqual(visible_body_keypoints(person), 2)

    def test_summarize_people_produces_counted_records(self) -> None:
        keypoints = {
            "people": [
                {"pose_keypoints_2d": [0, 0, 0.9] * 12},
                {"pose_keypoints_2d": [0, 0, 0.9] * 10},
            ]
        }
        summary = summarize_people(keypoints)
        self.assertEqual([item["visible_body_keypoints"] for item in summary], [12, 10])

    def test_run_checks_fail_closed_without_two_people(self) -> None:
        summary = [
            {"person_index": 0, "visible_body_keypoints": 17, "pose_keypoint_triplets": 18}
        ]
        checks = run_checks(summary, 10, (1024, 1024), (1024, 1024), 100)
        self.assertFalse(checks["exactly_two_people_detected"])
        self.assertFalse(checks["each_person_has_min_visible_body_keypoints"])

    def test_run_checks_require_dimensions_and_nonempty_map(self) -> None:
        summary = [
            {"person_index": 0, "visible_body_keypoints": 10, "pose_keypoint_triplets": 18},
            {"person_index": 1, "visible_body_keypoints": 11, "pose_keypoint_triplets": 18},
        ]
        checks = run_checks(summary, 10, (768, 1024), (1024, 1024), 0)
        self.assertFalse(checks["control_map_nonempty"])
        self.assertFalse(checks["control_map_dimensions_match_source"])

    def test_active_input_name_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            validate_active_input_name("../control.png")
        self.assertEqual(validate_active_input_name("control.png"), "control.png")


if __name__ == "__main__":
    unittest.main()
