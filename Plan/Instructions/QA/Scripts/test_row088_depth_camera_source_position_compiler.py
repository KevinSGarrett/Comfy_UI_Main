#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row088"
SYNTHETIC_LEDGER = FIXTURE_DIR / "synthetic_camera_listener_source_trajectory_ledger.json"
FIXTURE_PACKETS = (
    "case_static_camera_listener_source.json",
    "case_moving_camera_listener_source.json",
)
TRAJECTORY_CASES = ("static", "moving")


def _load_compiler_module():
    spec = importlib.util.spec_from_file_location(
        "compile_wave64_depth_camera_source_position", COMPILER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER_MOD = _load_compiler_module()


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

    def test_fixture_packets_cover_static_and_moving_camera_listener_source(self) -> None:
        for name in FIXTURE_PACKETS:
            self.assertTrue((FIXTURE_DIR / name).is_file(), msg=f"missing fixture {name}")

        static = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_static_camera_listener_source.json")
        )
        self.assertEqual(static["camera_binding"]["pose_model"], "static")
        self.assertEqual(static["metrics"]["listener_sample_count"], 3)
        self.assertEqual(static["metrics"]["source_sample_count"], 3)
        self.assertEqual(static["metrics"]["relative_only_sample_count"], 3)
        self.assertEqual(static["metrics"]["occlusion_sample_count"], 0)
        self.assertEqual(static["metrics"]["metric_claim_count"], 0)
        self.assertFalse(static["row_complete"])
        self.assertFalse(static["depth_authority"]["metric_claims_allowed"])

        moving = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_moving_camera_listener_source.json")
        )
        self.assertEqual(moving["camera_binding"]["pose_model"], "moving")
        self.assertEqual(moving["metrics"]["listener_sample_count"], 4)
        self.assertEqual(moving["metrics"]["source_sample_count"], 4)
        self.assertEqual(moving["metrics"]["relative_only_sample_count"], 4)
        self.assertEqual(moving["metrics"]["occlusion_sample_count"], 1)
        self.assertEqual(moving["metrics"]["metric_claim_count"], 0)
        self.assertFalse(moving["row_complete"])

    def test_deterministic_replay_and_tamper_hash_check(self) -> None:
        digests: dict[str, str] = {}
        for name in FIXTURE_PACKETS:
            packet = COMPILER_MOD.load_fixture_packet(name)
            first = COMPILER_MOD.compile_manifest(packet)
            second = COMPILER_MOD.compile_manifest(packet)
            # Wall-clock created_at may differ; content-addressed digest must replay.
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
            self.assertEqual(
                COMPILER_MOD.verify_manifest_integrity(first),
                first["manifest_sha256"],
            )
            self.assertEqual(
                COMPILER_MOD.verify_manifest_integrity(second),
                second["manifest_sha256"],
            )
            digests[name] = first["manifest_sha256"]

        self.assertEqual(len(set(digests.values())), 2)

        tampered = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_static_camera_listener_source.json")
        )
        tampered["metrics"]["source_sample_count"] = 999
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_manifest_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

        hash_tampered = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_moving_camera_listener_source.json")
        )
        hash_tampered["manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError) as ctx2:
            COMPILER_MOD.verify_manifest_integrity(hash_tampered)
        self.assertIn("tamper/replay mismatch", str(ctx2.exception))

    def test_synthetic_camera_listener_source_ledger_binds_fixture_digests(self) -> None:
        self.assertTrue(SYNTHETIC_LEDGER.is_file(), msg="missing synthetic ledger fixture")
        ledger = COMPILER_MOD.build_synthetic_camera_listener_source_trajectory_ledger()
        checked_in = json.loads(SYNTHETIC_LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(ledger, checked_in)
        self.assertEqual(
            COMPILER_MOD.verify_synthetic_benchmark_ledger_integrity(ledger),
            ledger["ledger_sha256"],
        )
        self.assertFalse(ledger["row_complete"])
        self.assertFalse(ledger["production_completion_allowed"])
        self.assertFalse(ledger["production_benchmark"])
        self.assertFalse(ledger["calibrated_trajectory_benchmark_pass"])
        self.assertFalse(ledger["visual_review_claimed"])
        self.assertFalse(ledger["rows084_085_acceptance_claimed"])
        self.assertEqual(ledger["authority_ceiling"], "fixture_synthetic_only")
        self.assertTrue(ledger["is_synthetic"])

        binding_by_name = {item["fixture_name"]: item for item in ledger["fixture_bindings"]}
        for name in FIXTURE_PACKETS:
            expected_file_digest = COMPILER_MOD.fixture_file_sha256(name)
            compiled = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet(name))
            self.assertEqual(binding_by_name[name]["fixture_file_sha256"], expected_file_digest)
            self.assertEqual(
                binding_by_name[name]["compiled_manifest_sha256"],
                compiled["manifest_sha256"],
            )

        by_case = {item["case_id"]: item for item in ledger["trajectory_metric_expectations"]}
        self.assertEqual(set(by_case), set(TRAJECTORY_CASES))
        self.assertEqual(by_case["static"]["expected_listener_sample_count"], 3)
        self.assertEqual(by_case["moving"]["expected_listener_sample_count"], 4)
        self.assertEqual(by_case["moving"]["expected_occlusion_sample_count"], 1)
        self.assertEqual(by_case["static"]["expected_metric_claim_count"], 0)

        tampered = json.loads(json.dumps(ledger))
        tampered["authority_ceiling"] = "tampered"
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_synthetic_benchmark_ledger_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

    def test_ledger_vs_compiled_manifest_expectation_verifier_rejects_digest_drift(self) -> None:
        receipt = COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations()
        self.assertEqual(receipt["status"], "ok")
        self.assertTrue(receipt["digest_drift_rejected"])
        self.assertFalse(receipt["calibrated_trajectory_benchmark_pass"])
        self.assertFalse(receipt["visual_review_claimed"])
        self.assertFalse(receipt["rows084_085_acceptance_claimed"])
        self.assertFalse(receipt["row_complete"])
        self.assertEqual(receipt["fixture_binding_count"], 2)
        self.assertEqual(receipt["authority_ceiling"], "fixture_synthetic_only")

        cli = subprocess.run(
            [sys.executable, str(COMPILER), "--verify-synthetic-benchmark-ledger"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0, msg=cli.stderr + cli.stdout)
        cli_receipt = json.loads(cli.stdout)
        self.assertEqual(cli_receipt["ledger_sha256"], receipt["ledger_sha256"])

        ledger = COMPILER_MOD.load_synthetic_benchmark_ledger()
        drifted = json.loads(json.dumps(ledger))
        drifted["fixture_bindings"][0]["compiled_manifest_sha256"] = "0" * 64
        drifted_body = {key: value for key, value in drifted.items() if key != "ledger_sha256"}
        drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(drifted_body)
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(drifted)
        self.assertIn("compiled manifest digest drift", str(ctx.exception))

        file_drifted = json.loads(json.dumps(ledger))
        file_drifted["fixture_bindings"][0]["fixture_file_sha256"] = "1" * 64
        file_body = {key: value for key, value in file_drifted.items() if key != "ledger_sha256"}
        file_drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(file_body)
        with self.assertRaises(ValueError) as ctx2:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(file_drifted)
        self.assertIn("fixture file digest drift", str(ctx2.exception))

        pass_claimed = json.loads(json.dumps(ledger))
        pass_claimed["calibrated_trajectory_benchmark_pass"] = True
        pass_body = {key: value for key, value in pass_claimed.items() if key != "ledger_sha256"}
        pass_claimed["ledger_sha256"] = COMPILER_MOD._canonical_sha256(pass_body)
        with self.assertRaises(ValueError) as ctx3:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(pass_claimed)
        self.assertIn("calibrated_trajectory_benchmark_pass=false", str(ctx3.exception))

    def test_ci_fixture_ledger_gate_rejects_checked_in_divergence(self) -> None:
        receipt = COMPILER_MOD.run_ci_fixture_ledger_gate()
        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(receipt["gate"], "row088_ci_fixture_ledger_gate")
        self.assertTrue(receipt["checked_in_matches_rebuild"])
        self.assertTrue(receipt["digest_drift_rejected"])
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["calibrated_trajectory_benchmark_pass"])
        self.assertFalse(receipt["visual_review_claimed"])
        self.assertFalse(receipt["rows084_085_acceptance_claimed"])
        self.assertFalse(receipt["production_benchmark"])
        self.assertEqual(receipt["authority_ceiling"], "fixture_synthetic_only")

        cli = subprocess.run(
            [sys.executable, str(COMPILER), "--ci-gate"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0, msg=cli.stderr + cli.stdout)
        cli_receipt = json.loads(cli.stdout)
        self.assertEqual(cli_receipt["ledger_sha256"], receipt["ledger_sha256"])
        self.assertFalse(cli_receipt["rows084_085_acceptance_claimed"])

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            for name in FIXTURE_PACKETS:
                (tmpdir / name).write_bytes((FIXTURE_DIR / name).read_bytes())
            drifted = json.loads(SYNTHETIC_LEDGER.read_text(encoding="utf-8"))
            drifted["fixture_bindings"][0]["compiled_manifest_sha256"] = "0" * 64
            body = {key: value for key, value in drifted.items() if key != "ledger_sha256"}
            drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(body)
            _write_json(
                tmpdir / "synthetic_camera_listener_source_trajectory_ledger.json", drifted
            )
            with self.assertRaises(ValueError) as ctx:
                COMPILER_MOD.run_ci_fixture_ledger_gate(fixture_dir=tmpdir)
            self.assertIn("diverge from rebuild", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

