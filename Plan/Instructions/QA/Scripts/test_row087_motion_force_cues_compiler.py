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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_motion_force_cues.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/motion_force_cues_manifest.schema.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sample(
    sample_id: str,
    owner_id: str,
    frame_index: int,
    pts: int,
    *,
    local_xy: list[float] | None = None,
    actor_xy: list[float] | None = None,
    residual_xy: list[float] | None = None,
    accel_xy: list[float] | None = None,
    camera_motion_dominant: bool = False,
    confidence: float = 0.9,
    region_class: str = "actor",
) -> dict:
    return {
        "sample_id": sample_id,
        "owner_id": owner_id,
        "region_class": region_class,
        "frame_index": frame_index,
        "pts": pts,
        "local_velocity_xy": local_xy if local_xy is not None else [2.0, 0.0],
        "actor_relative_velocity_xy": actor_xy if actor_xy is not None else [2.0, 0.0],
        "residual_after_camera_xy": residual_xy if residual_xy is not None else [2.0, 0.0],
        "acceleration_xy": accel_xy if accel_xy is not None else [0.1, 0.0],
        "velocity_units": "pixels_per_frame",
        "acceleration_units": "pixels_per_frame_squared",
        "camera_motion_dominant": camera_motion_dominant,
        "confidence": confidence,
    }


def _cue(
    cue_id: str,
    owner_id: str,
    cue_class: str,
    frame_index: int,
    *,
    force_proxy: float = 0.4,
    uncertainty: float = 0.1,
    confidence: float = 0.8,
    force_is_estimate: bool = True,
) -> dict:
    return {
        "cue_id": cue_id,
        "owner_id": owner_id,
        "cue_class": cue_class,
        "frame_index": frame_index,
        "force_proxy": force_proxy,
        "force_is_estimate": force_is_estimate,
        "force_units": "nonphysical_proxy",
        "uncertainty": uncertainty,
        "confidence": confidence,
    }


def _base_packet() -> dict:
    return {
        "schema_version": "1.0.0",
        "manifest_id": "row087_motion_force_manifest",
        "revision": "r001",
        "run_id": "run_087",
        "scene_id": "scene_087",
        "shot_id": "shot_087",
        "take_id": "take_087",
        "is_synthetic": True,
        "video_sha256": "a" * 64,
        "timeline_binding": {
            "timeline_id": "timeline_row084_fixture",
            "timeline_sha256": "b" * 64,
            "frame_count": 24,
            "frame_rate": 24.0,
            "frame_time_origin_seconds": 0.0,
        },
        "flow_binding": {
            "optical_flow_algorithm": "opencv_farneback_fixture_v1",
            "field_sha256": "c" * 64,
            "frame_pair_count": 23,
            "units": "pixels_per_frame",
        },
        "camera_model": {
            "model_id": "static_translation_fixture",
            "compensation_mode": "static_translation",
            "transform_sha256": "d" * 64,
            "planned_motion_supported": False,
        },
        "coordinate_spaces": [
            "local_image",
            "actor_relative",
            "camera_compensated",
            "surface_relative",
        ],
        "dependency_authority": {
            "row084_complete": False,
            "row085_complete": False,
            "row086_complete": False,
        },
        "runtime_authority": {
            "calibrated_trajectory_benchmark_pass": False,
            "runtime_receipt_present": False,
            "combined_flow_track_contact_audio_review_present": False,
        },
        "motion_samples": [
            _sample("s0", "character_1", 0, 0),
            _sample("s1", "character_1", 1, 1, local_xy=[1.5, 0.2], actor_xy=[1.5, 0.2], residual_xy=[1.5, 0.2]),
            _sample(
                "s2",
                "character_1_hand",
                0,
                0,
                region_class="hand",
                local_xy=[0.5, 0.0],
                actor_xy=[0.5, 0.0],
                residual_xy=[0.5, 0.0],
            ),
            _sample(
                "s3",
                "character_1_hand",
                2,
                2,
                region_class="hand",
                local_xy=[3.0, 0.0],
                actor_xy=[3.0, 0.0],
                residual_xy=[3.0, 0.0],
                accel_xy=[1.25, 0.0],
            ),
        ],
        "force_cues": [
            _cue("cue_approach", "character_1_hand", "approach", 1, force_proxy=0.2),
            _cue("cue_impact", "character_1_hand", "impact", 2, force_proxy=0.7, uncertainty=0.15),
            _cue("cue_slide", "character_1", "sliding", 2, force_proxy=0.3),
            _cue("cue_scuff", "character_1", "scuffing", 2, force_proxy=0.25),
            _cue("cue_fabric", "character_1", "fabric", 1, force_proxy=0.1),
        ],
        "metrics": {
            "motion_sample_count": 4,
            "owner_count": 2,
            "sliding_cue_count": 1,
            "scuffing_cue_count": 1,
            "fabric_cue_count": 1,
            "impact_cue_count": 1,
            "approach_cue_count": 1,
            "force_estimate_count": 5,
            "camera_dominant_sample_count": 0,
        },
        "thresholds": {
            "max_false_actor_motion_from_camera": 0.25,
            "min_sample_confidence": 0.5,
            "max_force_uncertainty": 0.5,
        },
        "provenance": {"fixture": "row087_unit"},
    }


class Row087MotionForceCuesCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "motion_force_packet.json"
            output_path = tmpdir / "motion_force_cues_manifest.json"
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

    def test_compiles_hold_manifest_with_estimate_force_contract(self) -> None:
        _, compiled = self._run_compile(_base_packet(), expect_ok=True)
        assert compiled is not None
        self.assertFalse(compiled["row_complete"])
        self.assertFalse(compiled["production_completion_allowed"])
        self.assertEqual(compiled["authority_ceiling"], "candidate")
        self.assertFalse(compiled["dependency_authority"]["dependency_ready"])
        self.assertFalse(compiled["runtime_authority"]["runtime_ready"])
        self.assertFalse(compiled["authority_summary"]["contact_force_certification_allowed"])
        self.assertTrue(compiled["authority_summary"]["force_proxies_are_estimates"])
        self.assertTrue(compiled["authority_summary"]["camera_false_actor_motion_blocked"])
        self.assertIn("dependency_row084_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("dependency_row085_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("dependency_row086_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertEqual(compiled["metrics"]["sliding_cue_count"], 1)
        self.assertEqual(compiled["metrics"]["impact_cue_count"], 1)
        self.assertEqual(len(compiled["manifest_sha256"]), 64)
        for cue in compiled["force_cues"]:
            self.assertTrue(cue["force_is_estimate"])
            self.assertEqual(cue["force_units"], "nonphysical_proxy")

    def test_rejects_non_estimate_force_proxy(self) -> None:
        packet = _base_packet()
        packet["force_cues"][1]["force_is_estimate"] = False
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("force_is_estimate must be true", result.stderr + result.stdout)

    def test_rejects_camera_motion_as_false_actor_motion(self) -> None:
        packet = _base_packet()
        packet["motion_samples"][0]["camera_motion_dominant"] = True
        packet["motion_samples"][0]["actor_relative_velocity_xy"] = [1.0, 0.0]
        packet["metrics"]["camera_dominant_sample_count"] = 1
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("camera motion cannot become false actor motion", result.stderr + result.stdout)

    def test_rejects_non_monotonic_owner_frames(self) -> None:
        packet = _base_packet()
        packet["motion_samples"][1]["frame_index"] = 0
        packet["motion_samples"][1]["pts"] = 0
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("strictly increasing per owner", result.stderr + result.stdout)

    def test_rejects_missing_required_coordinate_space(self) -> None:
        packet = _base_packet()
        packet["coordinate_spaces"] = ["local_image", "actor_relative", "camera_compensated"]
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("coordinate_spaces missing required spaces", result.stderr + result.stdout)

    def test_rejects_metric_mismatch_against_derived_cues(self) -> None:
        packet = _base_packet()
        packet["metrics"]["fabric_cue_count"] = 99
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("does not match derived count", result.stderr + result.stdout)

    def test_rejects_unsupported_camera_actor_relative_claim(self) -> None:
        packet = _base_packet()
        packet["camera_model"] = {
            "model_id": "unsupported_fixture",
            "compensation_mode": "unsupported",
            "transform_sha256": None,
            "planned_motion_supported": False,
        }
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("unsupported camera compensation cannot certify", result.stderr + result.stdout)

    def test_schema_requires_force_estimate_contract_and_forbids_open_properties(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema.get("additionalProperties", True))
        required = set(schema["required"])
        self.assertIn("motion_samples", required)
        self.assertIn("force_cues", required)
        self.assertIn("row_complete", required)
        force_cue = schema["$defs"]["force_cue"]["properties"]
        self.assertEqual(force_cue["force_is_estimate"]["const"], True)
        self.assertEqual(force_cue["force_units"]["const"], "nonphysical_proxy")


if __name__ == "__main__":
    unittest.main()
