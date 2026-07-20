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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_pose_hand_foot_gait_extraction.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/pose_hand_foot_gait_extraction_manifest.schema.json"
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row086"
SYNTHETIC_LEDGER = FIXTURE_DIR / "synthetic_landmark_phase_ledger.json"
FIXTURE_PACKETS = (
    "case_visible_landmark_trajectory.json",
    "case_gait_contact_phases.json",
    "case_partial_view_hidden_joint.json",
)


def _load_compiler_module():
    spec = importlib.util.spec_from_file_location(
        "compile_wave64_pose_hand_foot_gait_extraction", COMPILER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER_MOD = _load_compiler_module()


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

    def test_fixture_packets_cover_landmark_gait_and_partial_view(self) -> None:
        for name in FIXTURE_PACKETS:
            self.assertTrue((FIXTURE_DIR / name).is_file(), msg=f"missing fixture {name}")

        _, visible = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_visible_landmark_trajectory.json"),
            expect_ok=True,
        )
        assert visible is not None
        self.assertEqual(visible["authority_summary"]["trajectory_count"], 3)
        self.assertEqual(visible["authority_summary"]["landmark_count"], 3)
        self.assertFalse(visible["row_complete"])
        self.assertFalse(visible["dependency_authority"]["row084_complete"])
        self.assertFalse(visible["dependency_authority"]["row085_complete"])
        self.assertFalse(visible["runtime_authority"]["annotated_benchmark_pass"])

        _, gait = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_gait_contact_phases.json"),
            expect_ok=True,
        )
        assert gait is not None
        self.assertGreaterEqual(gait["authority_summary"]["gait_phase_count"], 4)
        self.assertGreaterEqual(gait["authority_summary"]["contact_phase_count"], 4)
        phases = {item["phase"] for item in gait["instances"][0]["gait_phases"]}
        self.assertTrue({"heel_strike", "sole_contact", "toe_off"}.issubset(phases))

        _, partial = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_partial_view_hidden_joint.json"),
            expect_ok=True,
        )
        assert partial is not None
        hidden = [
            item
            for item in partial["instances"][0]["landmarks"]
            if item["observation_state"] in {"outside_frame", "occluded"}
        ]
        self.assertGreaterEqual(len(hidden), 2)
        for landmark in hidden:
            self.assertIsNone(landmark["x"])
            self.assertIsNone(landmark["y"])
        self.assertEqual(partial["authority_summary"]["fabricated_hidden_joint_count"], 0)

    def test_deterministic_replay_and_tamper_proof_for_fixtures(self) -> None:
        for name in FIXTURE_PACKETS:
            first = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet(name))
            second = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet(name))
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
            self.assertEqual(
                COMPILER_MOD.verify_manifest_integrity(first),
                first["manifest_sha256"],
            )
            tampered = json.loads(json.dumps(first))
            tampered["authority_summary"]["landmark_count"] = 99
            with self.assertRaises(ValueError) as ctx:
                COMPILER_MOD.verify_manifest_integrity(tampered)
            self.assertIn("tamper/replay mismatch", str(ctx.exception))

            hash_tampered = json.loads(json.dumps(first))
            hash_tampered["manifest_sha256"] = "0" * 64
            with self.assertRaises(ValueError) as ctx2:
                COMPILER_MOD.verify_manifest_integrity(hash_tampered)
            self.assertIn("tamper/replay mismatch", str(ctx2.exception))

        cli = subprocess.run(
            [sys.executable, str(COMPILER), "--verify-fixture-replay"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0, msg=cli.stderr + cli.stdout)
        receipt = json.loads(cli.stdout)
        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(receipt["fixture_count"], 3)
        self.assertFalse(receipt["annotated_benchmark_pass"])
        self.assertFalse(receipt["row084_acceptance_claimed"])
        self.assertFalse(receipt["row085_acceptance_claimed"])
        self.assertFalse(receipt["row_complete"])
        self.assertEqual(receipt["authority_ceiling"], "fixture_synthetic_only")

    def test_synthetic_landmark_phase_ledger_binds_fixture_digests(self) -> None:
        self.assertTrue(SYNTHETIC_LEDGER.is_file(), msg="missing synthetic ledger fixture")
        ledger = COMPILER_MOD.build_synthetic_landmark_phase_ledger()
        checked_in = COMPILER_MOD.load_synthetic_landmark_phase_ledger()
        self.assertEqual(ledger, checked_in)
        self.assertEqual(
            COMPILER_MOD.verify_synthetic_landmark_phase_ledger_integrity(ledger),
            ledger["ledger_sha256"],
        )
        self.assertFalse(ledger["row_complete"])
        self.assertFalse(ledger["production_completion_allowed"])
        self.assertFalse(ledger["production_benchmark"])
        self.assertFalse(ledger["annotated_benchmark_pass"])
        self.assertFalse(ledger["annotated_clip_harness_production_pass"])
        self.assertFalse(ledger["visual_review_claimed"])
        self.assertFalse(ledger["rows084_085_acceptance_claimed"])
        self.assertEqual(ledger["authority_ceiling"], "fixture_synthetic_only")
        self.assertTrue(ledger["is_synthetic"])

        binding_by_name = {item["fixture_name"]: item for item in ledger["fixture_bindings"]}
        for name in FIXTURE_PACKETS:
            self.assertIn(name, binding_by_name)
            self.assertEqual(
                binding_by_name[name]["fixture_file_sha256"],
                COMPILER_MOD.fixture_file_sha256(name),
            )
            self.assertFalse(binding_by_name[name]["row_complete"])

        by_case = {item["case_id"]: item for item in ledger["landmark_phase_expectations"]}
        self.assertEqual(
            set(by_case),
            {
                "visible_landmark_trajectory",
                "gait_contact_phases",
                "partial_view_hidden_joint",
            },
        )
        self.assertEqual(by_case["partial_view_hidden_joint"]["expected_fabricated_hidden_joint_count"], 0)
        self.assertGreaterEqual(
            by_case["partial_view_hidden_joint"]["expected_hidden_or_unknown_landmark_count"],
            2,
        )

        tampered = json.loads(json.dumps(ledger))
        tampered["landmark_phase_expectations"][0]["expected_landmark_count"] = 999
        with self.assertRaises(ValueError):
            COMPILER_MOD.verify_synthetic_landmark_phase_ledger_integrity(tampered)

    def test_ledger_vs_compiled_manifest_expectation_verifier_rejects_digest_drift(self) -> None:
        receipt = COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations()
        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(receipt["fixture_binding_count"], 3)
        self.assertEqual(receipt["landmark_phase_expectation_count"], 3)
        self.assertFalse(receipt["annotated_benchmark_pass"])
        self.assertFalse(receipt["annotated_clip_harness_production_pass"])
        self.assertFalse(receipt["rows084_085_acceptance_claimed"])
        self.assertFalse(receipt["row_complete"])
        self.assertEqual(receipt["authority_ceiling"], "fixture_synthetic_only")

        cli = subprocess.run(
            [sys.executable, str(COMPILER), "--verify-synthetic-landmark-phase-ledger"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0, msg=cli.stderr + cli.stdout)
        cli_receipt = json.loads(cli.stdout)
        self.assertEqual(cli_receipt["ledger_sha256"], receipt["ledger_sha256"])

        ledger = COMPILER_MOD.load_synthetic_landmark_phase_ledger()
        drifted = json.loads(json.dumps(ledger))
        drifted["fixture_bindings"][0]["compiled_manifest_sha256"] = "a" * 64
        drifted_body = {key: value for key, value in drifted.items() if key != "ledger_sha256"}
        drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(drifted_body)
        with self.assertRaises(ValueError):
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(drifted)

        file_drifted = json.loads(json.dumps(ledger))
        file_drifted["fixture_bindings"][0]["fixture_file_sha256"] = "b" * 64
        file_body = {key: value for key, value in file_drifted.items() if key != "ledger_sha256"}
        file_drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(file_body)
        with self.assertRaises(ValueError):
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(file_drifted)

        pass_claimed = json.loads(json.dumps(ledger))
        pass_claimed["annotated_benchmark_pass"] = True
        pass_body = {key: value for key, value in pass_claimed.items() if key != "ledger_sha256"}
        pass_claimed["ledger_sha256"] = COMPILER_MOD._canonical_sha256(pass_body)
        with self.assertRaises(ValueError):
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(pass_claimed)

    def test_annotated_clip_harness_and_ci_gate_reject_false_completion(self) -> None:
        harness = COMPILER_MOD.run_annotated_clip_harness()
        self.assertEqual(harness["status"], "ok")
        self.assertEqual(harness["harness"], "row086_annotated_clip_harness")
        self.assertFalse(harness["annotated_benchmark_pass"])
        self.assertFalse(harness["annotated_clip_harness_production_pass"])
        self.assertFalse(harness["rows084_085_acceptance_claimed"])
        self.assertFalse(harness["row_complete"])
        self.assertEqual(harness["authority_ceiling"], "fixture_synthetic_only")

        harness_cli = subprocess.run(
            [sys.executable, str(COMPILER), "--run-annotated-clip-harness"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(harness_cli.returncode, 0, msg=harness_cli.stderr + harness_cli.stdout)
        harness_cli_receipt = json.loads(harness_cli.stdout)
        self.assertEqual(harness_cli_receipt["ledger_sha256"], harness["ledger_sha256"])

        receipt = COMPILER_MOD.run_ci_fixture_ledger_gate()
        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(receipt["gate"], "row086_ci_fixture_ledger_gate")
        self.assertTrue(receipt["checked_in_matches_rebuild"])
        self.assertFalse(receipt["annotated_benchmark_pass"])
        self.assertFalse(receipt["annotated_clip_harness_production_pass"])
        self.assertFalse(receipt["rows084_085_acceptance_claimed"])
        self.assertFalse(receipt["row_complete"])
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

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            for name in FIXTURE_PACKETS:
                (tmpdir / name).write_bytes((FIXTURE_DIR / name).read_bytes())
            drifted = json.loads(json.dumps(COMPILER_MOD.load_synthetic_landmark_phase_ledger()))
            drifted["hold_reasons"] = list(drifted["hold_reasons"]) + ["injected_divergence"]
            body = {key: value for key, value in drifted.items() if key != "ledger_sha256"}
            drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(body)
            _write_json(tmpdir / "synthetic_landmark_phase_ledger.json", drifted)
            with self.assertRaises(ValueError):
                COMPILER_MOD.run_ci_fixture_ledger_gate(fixture_dir=tmpdir)


if __name__ == "__main__":
    unittest.main()
