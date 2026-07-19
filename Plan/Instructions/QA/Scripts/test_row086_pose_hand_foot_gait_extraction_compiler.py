#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_pose_hand_foot_gait_extraction.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/pose_hand_foot_gait_extraction_manifest.schema.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _traj_sample(
    frame_index: int,
    pts: int,
    *,
    x: float | None = 10.0,
    y: float | None = 20.0,
    vx: float | None = 0.1,
    vy: float | None = 0.0,
    confidence: float = 0.93,
    observation_state: str = "observed",
) -> dict:
    return {
        "frame_index": frame_index,
        "pts": pts,
        "x": x,
        "y": y,
        "vx": vx,
        "vy": vy,
        "confidence": confidence,
        "observation_state": observation_state,
    }


def _base_packet() -> dict:
    return {
        "schema_version": "1.0.0",
        "manifest_id": "row086_pose_gait_manifest",
        "revision": "r001",
        "run_id": "run_086",
        "scene_id": "scene_086",
        "shot_id": "shot_086",
        "take_id": "take_086",
        "is_synthetic": True,
        "video_sha256": "a" * 64,
        "timeline_binding": {
            "timeline_id": "timeline_row084_fixture",
            "timeline_sha256": "b" * 64,
            "frame_count": 48,
            "frame_rate": 24.0,
            "frame_time_origin_seconds": 0.0,
        },
        "owner_track_binding": {
            "tracking_manifest_id": "row085_tracking_manifest",
            "tracking_manifest_sha256": "c" * 64,
            "owner_id": "character_1",
            "track_id": "track_actor_1",
        },
        "detector_stack": {
            "pose_detector_id": "fixture_pose",
            "hand_detector_id": "fixture_hand",
            "foot_detector_id": "fixture_foot",
            "gait_estimator_id": "fixture_gait",
            "revision": "fixture_v1",
            "parameter_digest_sha256": "d" * 64,
        },
        "dependency_authority": {
            "row084_complete": False,
            "row085_complete": False,
        },
        "runtime_authority": {
            "annotated_benchmark_pass": False,
            "runtime_receipt_present": False,
            "combined_landmark_track_contact_audio_review_present": False,
        },
        "instances": [
            {
                "instance_id": "instance_character_1",
                "owner_id": "character_1",
                "track_id": "track_actor_1",
                "landmarks": [
                    {
                        "landmark_id": "body_pelvis",
                        "landmark_class": "body",
                        "side": "center",
                        "frame_index": 0,
                        "pts": 0,
                        "x": 100.0,
                        "y": 200.0,
                        "confidence": 0.95,
                        "observation_state": "observed",
                    },
                    {
                        "landmark_id": "hand_right_wrist",
                        "landmark_class": "hand",
                        "side": "right",
                        "frame_index": 0,
                        "pts": 0,
                        "x": 140.0,
                        "y": 180.0,
                        "confidence": 0.91,
                        "observation_state": "observed",
                    },
                    {
                        "landmark_id": "foot_left_heel",
                        "landmark_class": "foot",
                        "side": "left",
                        "frame_index": 0,
                        "pts": 0,
                        "x": 90.0,
                        "y": 320.0,
                        "confidence": 0.9,
                        "observation_state": "observed",
                    },
                    {
                        "landmark_id": "foot_right_heel_hidden",
                        "landmark_class": "foot",
                        "side": "right",
                        "frame_index": 2,
                        "pts": 2,
                        "x": None,
                        "y": None,
                        "confidence": 0.0,
                        "observation_state": "outside_frame",
                    },
                ],
                "trajectories": [
                    {
                        "landmark_id": "foot_left_heel",
                        "samples": [
                            _traj_sample(0, 0, x=90.0, y=320.0),
                            _traj_sample(1, 1, x=92.0, y=318.0, vx=2.0, vy=-2.0),
                            _traj_sample(3, 3, x=96.0, y=316.0, vx=2.0, vy=-1.0),
                        ],
                    },
                    {
                        "landmark_id": "hand_right_wrist",
                        "samples": [
                            _traj_sample(0, 0, x=140.0, y=180.0),
                            _traj_sample(1, 1, x=142.0, y=178.0, vx=2.0, vy=-2.0),
                        ],
                    },
                ],
                "gait_phases": [
                    {
                        "side": "left",
                        "phase": "heel_strike",
                        "frame_index": 0,
                        "pts": 0,
                        "confidence": 0.88,
                    },
                    {
                        "side": "left",
                        "phase": "sole_contact",
                        "frame_index": 1,
                        "pts": 1,
                        "confidence": 0.9,
                    },
                    {
                        "side": "left",
                        "phase": "toe_off",
                        "frame_index": 3,
                        "pts": 3,
                        "confidence": 0.86,
                    },
                    {
                        "side": "right",
                        "phase": "swing",
                        "frame_index": 2,
                        "pts": 2,
                        "confidence": 0.8,
                    },
                ],
                "contact_phases": [
                    {
                        "effector": "hand_right",
                        "phase": "approach",
                        "frame_index": 0,
                        "pts": 0,
                        "target_owner_id": "prop_table",
                        "confidence": 0.84,
                    },
                    {
                        "effector": "hand_right",
                        "phase": "contact",
                        "frame_index": 1,
                        "pts": 1,
                        "target_owner_id": "prop_table",
                        "confidence": 0.87,
                    },
                    {
                        "effector": "hand_right",
                        "phase": "release",
                        "frame_index": 3,
                        "pts": 3,
                        "target_owner_id": "prop_table",
                        "confidence": 0.85,
                    },
                ],
            }
        ],
        "thresholds": {
            "min_landmark_confidence": 0.5,
            "max_trajectory_gap_frames": 2,
            "max_fabricated_hidden_joint_count": 0,
            "min_gait_phase_confidence": 0.5,
            "min_contact_phase_confidence": 0.5,
        },
        "provenance": {"fixture": "row086_unit"},
    }


class Row086PoseHandFootGaitExtractionCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.completedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "pose_gait_packet.json"
            output_path = tmpdir / "pose_hand_foot_gait_extraction_manifest.json"
            _write_json(packet_path, packet)
            result = subprocess.run(
                [sys.executable, str(COMPILER), "--input", str(packet_path), "--output", str(output_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if expect_ok and result.returncode != 0:
                self.fail(f"compiler failed unexpectedly\nstdout={result.stdout}\nstderr={result.stderr}")
            if (not expect_ok) and result.returncode == 0:
                self.fail(f"compiler succeeded unexpectedly\nstdout={result.stdout}\nstderr={result.stderr}")
            if expect_ok:
                compiled = json.loads(output_path.read_text(encoding="utf-8"))
                errors = sorted(error.message for error in self.validator.iter_errors(compiled))
                self.assertEqual(errors, [])
                return result, compiled
            return result, None

    def test_compiles_hold_manifest_with_taxonomy_phases_and_partial_view(self) -> None:
        _, compiled = self._run_compile(_base_packet(), expect_ok=True)
        assert compiled is not None
        self.assertFalse(compiled["row_complete"])
        self.assertFalse(compiled["production_completion_allowed"])
        self.assertEqual(compiled["authority_ceiling"], "candidate")
        self.assertFalse(compiled["dependency_authority"]["dependency_ready"])
        self.assertFalse(compiled["runtime_authority"]["runtime_ready"])
        self.assertFalse(compiled["authority_summary"]["contact_phase_certification_allowed"])
        self.assertIn("dependency_row084_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("dependency_row085_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertEqual(compiled["authority_summary"]["fabricated_hidden_joint_count"], 0)
        self.assertEqual(compiled["authority_summary"]["gait_phase_count"], 4)
        self.assertEqual(compiled["authority_summary"]["contact_phase_count"], 3)
        self.assertIn("body", compiled["instances"][0]["landmark_classes_present"])
        self.assertIn("hand", compiled["instances"][0]["landmark_classes_present"])
        self.assertIn("foot", compiled["instances"][0]["landmark_classes_present"])
        self.assertEqual(len(compiled["manifest_sha256"]), 64)

    def test_rejects_fabricated_hidden_joint_coordinates(self) -> None:
        packet = _base_packet()
        packet["instances"][0]["landmarks"][3]["x"] = 12.0
        packet["instances"][0]["landmarks"][3]["y"] = 34.0
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("must not fabricate coordinates", result.stderr + result.stdout)

    def test_rejects_duplicate_trajectory_frames(self) -> None:
        packet = _base_packet()
        packet["instances"][0]["trajectories"][0]["samples"][1]["frame_index"] = 0
        packet["instances"][0]["trajectories"][0]["samples"][1]["pts"] = 0
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("strictly increasing", result.stderr + result.stdout)

    def test_rejects_missing_required_landmark_taxonomy(self) -> None:
        packet = _base_packet()
        packet["instances"][0]["landmarks"] = [
            landmark
            for landmark in packet["instances"][0]["landmarks"]
            if landmark["landmark_class"] != "hand"
        ]
        packet["instances"][0]["trajectories"] = [
            trajectory
            for trajectory in packet["instances"][0]["trajectories"]
            if trajectory["landmark_id"] != "hand_right_wrist"
        ]
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("landmark taxonomy incomplete", result.stderr + result.stdout)

    def test_rejects_owner_binding_mismatch(self) -> None:
        packet = _base_packet()
        packet["instances"][0]["owner_id"] = "character_2"
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("must match owner_track_binding.owner_id", result.stderr + result.stdout)

    def test_rejects_trajectory_gap_above_threshold(self) -> None:
        packet = _base_packet()
        packet["thresholds"]["max_trajectory_gap_frames"] = 0
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertIn("max_trajectory_gap_frames", compiled["threshold_violations"])
        self.assertFalse(compiled["authority_summary"]["contact_phase_certification_allowed"])

    def test_dependencies_and_runtime_gate_certification(self) -> None:
        packet = _base_packet()
        packet["dependency_authority"] = {"row084_complete": True, "row085_complete": True}
        packet["runtime_authority"] = {
            "annotated_benchmark_pass": True,
            "runtime_receipt_present": True,
            "combined_landmark_track_contact_audio_review_present": True,
        }
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        # Even with dependency/runtime flags true, this increment never completes the row.
        self.assertFalse(compiled["row_complete"])
        self.assertFalse(compiled["production_completion_allowed"])
        self.assertTrue(compiled["dependency_authority"]["dependency_ready"])
        self.assertTrue(compiled["runtime_authority"]["runtime_ready"])
        self.assertTrue(compiled["authority_summary"]["contact_phase_certification_allowed"])
        self.assertEqual(compiled["authority_ceiling"], "technical")

    def test_schema_requires_instances_and_forbids_open_properties(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema.get("additionalProperties", True))
        required = set(schema["required"])
        self.assertIn("instances", required)
        self.assertIn("thresholds", required)
        self.assertIn("owner_track_binding", required)
        self.assertIn("row_complete", required)


if __name__ == "__main__":
    unittest.main()
