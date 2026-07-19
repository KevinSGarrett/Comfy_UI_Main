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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_depth_camera_source_position.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/depth_camera_source_position_manifest.schema.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _listener_sample(frame_index: int, pts: int, *, confidence: float = 0.95) -> dict:
    return {
        "frame_index": frame_index,
        "pts": pts,
        "position": [0.0, 0.0, 0.0],
        "forward": [0.0, 1.0, 0.0],
        "up": [0.0, 0.0, 1.0],
        "confidence": confidence,
        "observation_state": "observed",
    }


def _source_sample(
    frame_index: int,
    pts: int,
    *,
    depth_mode: str = "relative",
    relative_depth: float | None = 0.42,
    metric_depth_m: float | None = None,
    confidence: float = 0.91,
    uncertainty: float = 0.08,
    occlusion_state: str = "clear",
    visibility: str = "visible",
    observation_state: str = "observed",
    azimuth: float | None = -12.0,
    elevation: float | None = 4.0,
) -> dict:
    return {
        "frame_index": frame_index,
        "pts": pts,
        "position": [-0.1 + (0.01 * frame_index), 0.9, 0.2],
        "depth_mode": depth_mode,
        "relative_depth": relative_depth,
        "metric_depth_m": metric_depth_m,
        "source_camera_distance": 1.2 if depth_mode != "abstain" else None,
        "source_listener_distance": 1.1 if depth_mode != "abstain" else None,
        "screen_azimuth_deg": azimuth,
        "screen_elevation_deg": elevation,
        "occlusion_state": occlusion_state,
        "visibility": visibility,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "observation_state": observation_state,
    }


def _base_packet() -> dict:
    return {
        "schema_version": "1.0.0",
        "manifest_id": "row088_depth_camera_source_manifest",
        "revision": "r001",
        "run_id": "run_088",
        "scene_id": "scene_088",
        "shot_id": "shot_088",
        "take_id": "take_088",
        "camera_id": "camera_a",
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
        "camera_binding": {
            "camera_id": "camera_a",
            "shot_id": "shot_088",
            "take_id": "take_088",
            "intrinsics_present": False,
            "extrinsics_present": False,
            "calibration_authority": "relative_only",
            "pose_model": "static",
        },
        "coordinate_space": {
            "frame_id": "camera_relative_fixture",
            "handedness": "right",
            "units": "relative",
            "origin": "camera",
            "up_axis": "+y",
        },
        "estimator_stack": {
            "depth_estimator_id": "fixture_relative_depth",
            "camera_pose_estimator_id": "fixture_camera_pose",
            "source_position_estimator_id": "fixture_source_pos",
            "listener_estimator_id": "fixture_listener",
            "revision": "fixture_v1",
            "parameter_digest_sha256": "d" * 64,
        },
        "dependency_authority": {
            "row084_complete": False,
            "row085_complete": False,
        },
        "runtime_authority": {
            "calibrated_trajectory_benchmark_pass": False,
            "runtime_receipt_present": False,
            "combined_frame_contact_audio_review_present": False,
        },
        "depth_authority": {
            "depth_mode": "relative",
            "calibration_source": None,
            "scale_uncertainty": 0.35,
        },
        "listener_trajectory": {
            "listener_id": "listener_main",
            "samples": [
                _listener_sample(0, 0),
                _listener_sample(1, 1),
                _listener_sample(2, 2),
            ],
        },
        "source_trajectories": [
            {
                "source_id": "source_character_1_voice",
                "owner_id": "character_1",
                "track_id": "track_actor_1",
                "samples": [
                    _source_sample(0, 0),
                    _source_sample(1, 1, occlusion_state="partial", visibility="partial"),
                    _source_sample(2, 2),
                ],
            }
        ],
        "thresholds": {
            "min_position_confidence": 0.5,
            "max_scale_uncertainty": 1.0,
            "max_abstention_ratio": 0.5,
            "max_occlusion_ratio": 0.75,
        },
        "provenance": {"fixture": "row088_unit"},
    }


class Row088DepthCameraSourcePositionCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.completedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "spatial_packet.json"
            output_path = tmpdir / "depth_camera_source_position_manifest.json"
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

    def test_compiles_hold_manifest_with_relative_depth_and_trajectories(self) -> None:
        _, compiled = self._run_compile(_base_packet(), expect_ok=True)
        assert compiled is not None
        self.assertFalse(compiled["row_complete"])
        self.assertFalse(compiled["production_completion_allowed"])
        self.assertEqual(compiled["authority_ceiling"], "candidate")
        self.assertFalse(compiled["dependency_authority"]["dependency_ready"])
        self.assertFalse(compiled["runtime_authority"]["runtime_ready"])
        self.assertFalse(compiled["authority_summary"]["spatial_certification_allowed"])
        self.assertTrue(compiled["depth_authority"]["relative_depth_labeled"])
        self.assertFalse(compiled["depth_authority"]["metric_claims_allowed"])
        self.assertIn("dependency_row084_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("dependency_row085_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("relative_depth_only_no_metric_authority", compiled["authority_summary"]["hold_reasons"])
        self.assertEqual(compiled["metrics"]["source_count"], 1)
        self.assertEqual(compiled["metrics"]["relative_only_sample_count"], 3)
        self.assertEqual(compiled["metrics"]["occlusion_sample_count"], 1)
        self.assertEqual(len(compiled["manifest_sha256"]), 64)

    def test_rejects_duplicate_frame_indices(self) -> None:
        packet = _base_packet()
        packet["source_trajectories"][0]["samples"][1]["frame_index"] = 0
        packet["source_trajectories"][0]["samples"][1]["pts"] = 0
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("strictly increasing", result.stderr + result.stdout)

    def test_rejects_camera_take_mismatch(self) -> None:
        packet = _base_packet()
        packet["camera_binding"]["take_id"] = "take_other"
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("camera_binding.take_id must match top-level take_id", result.stderr + result.stdout)

    def test_rejects_metric_without_calibration_authority(self) -> None:
        packet = _base_packet()
        packet["depth_authority"]["depth_mode"] = "metric"
        packet["depth_authority"]["calibration_source"] = "synthetic_scale"
        packet["camera_binding"]["calibration_authority"] = "relative_only"
        packet["coordinate_space"]["units"] = "meters"
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("metric depth claims require", result.stderr + result.stdout)

    def test_rejects_metric_sample_when_authority_is_relative(self) -> None:
        packet = _base_packet()
        packet["source_trajectories"][0]["samples"][0]["depth_mode"] = "metric"
        packet["source_trajectories"][0]["samples"][0]["relative_depth"] = None
        packet["source_trajectories"][0]["samples"][0]["metric_depth_m"] = 1.5
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("blocked without metric depth authority", result.stderr + result.stdout)

    def test_rejects_owner_track_mismatch(self) -> None:
        packet = _base_packet()
        packet["source_trajectories"][0]["owner_id"] = "character_2"
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("owner_id must match owner_track_binding.owner_id", result.stderr + result.stdout)

    def test_abstention_requires_zero_confidence(self) -> None:
        packet = _base_packet()
        packet["source_trajectories"][0]["samples"][1] = _source_sample(
            1,
            1,
            depth_mode="abstain",
            relative_depth=None,
            metric_depth_m=None,
            confidence=0.4,
            observation_state="abstain",
            azimuth=None,
            elevation=None,
        )
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("abstain observation_state requires confidence=0", result.stderr + result.stdout)

    def test_low_confidence_blocks_spatial_certification(self) -> None:
        packet = _base_packet()
        packet["source_trajectories"][0]["samples"][0]["confidence"] = 0.2
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertIn("min_position_confidence", compiled["threshold_violations"])
        self.assertTrue(compiled["authority_summary"]["unsupported_spatial_claims"])
        self.assertFalse(compiled["authority_summary"]["spatial_certification_allowed"])

    def test_schema_requires_spatial_contracts_and_forbids_open_properties(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema.get("additionalProperties", True))
        required = set(schema["required"])
        self.assertIn("camera_binding", required)
        self.assertIn("coordinate_space", required)
        self.assertIn("depth_authority", required)
        self.assertIn("listener_trajectory", required)
        self.assertIn("source_trajectories", required)
        self.assertIn("row_complete", required)


if __name__ == "__main__":
    unittest.main()
