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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_motion_force_cues.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/motion_force_cues_manifest.schema.json"
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row087"
SYNTHETIC_LEDGER = FIXTURE_DIR / "synthetic_calibrated_trajectory_benchmark_ledger.json"
FIXTURE_PACKETS = (
    "case_static_camera.json",
    "case_pan_camera.json",
    "case_actor_relative_residual.json",
    "case_sliding_scuffing_fabric.json",
)
TRAJECTORY_CASES = ("static", "pan", "actor_relative_residual", "sliding_scuffing_fabric")


def _load_compiler_module():
    spec = importlib.util.spec_from_file_location("compile_wave64_motion_force_cues", COMPILER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER_MOD = _load_compiler_module()


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

    def test_fixture_packets_cover_static_pan_residual_and_cues(self) -> None:
        for name in FIXTURE_PACKETS:
            self.assertTrue((FIXTURE_DIR / name).is_file(), msg=f"missing fixture {name}")

        static = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet("case_static_camera.json"))
        self.assertEqual(static["camera_model"]["compensation_mode"], "static_translation")
        self.assertEqual(static["metrics"]["camera_dominant_sample_count"], 0)
        self.assertFalse(static["row_complete"])

        pan = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet("case_pan_camera.json"))
        self.assertEqual(pan["camera_model"]["compensation_mode"], "planned_transform")
        self.assertTrue(pan["camera_model"]["planned_motion_supported"])
        self.assertEqual(pan["metrics"]["camera_dominant_sample_count"], 3)
        for sample in pan["motion_samples"]:
            self.assertTrue(sample["camera_motion_dominant"])
            mag = (sample["actor_relative_velocity_xy"][0] ** 2 + sample["actor_relative_velocity_xy"][1] ** 2) ** 0.5
            self.assertLessEqual(mag, pan["thresholds"]["max_false_actor_motion_from_camera"])

        residual = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_actor_relative_residual.json")
        )
        self.assertEqual(residual["metrics"]["motion_sample_count"], 4)
        self.assertEqual(residual["metrics"]["approach_cue_count"], 1)
        self.assertEqual(residual["metrics"]["impact_cue_count"], 1)

        cues = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_sliding_scuffing_fabric.json")
        )
        self.assertEqual(cues["metrics"]["sliding_cue_count"], 1)
        self.assertEqual(cues["metrics"]["scuffing_cue_count"], 1)
        self.assertEqual(cues["metrics"]["fabric_cue_count"], 1)

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

        self.assertEqual(len(set(digests.values())), 4)

        tampered = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_static_camera.json")
        )
        tampered["metrics"]["motion_sample_count"] = 999
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_manifest_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

        hash_tampered = COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_pan_camera.json")
        )
        hash_tampered["manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError) as ctx2:
            COMPILER_MOD.verify_manifest_integrity(hash_tampered)
        self.assertIn("tamper/replay mismatch", str(ctx2.exception))

    def test_synthetic_calibrated_trajectory_ledger_binds_fixture_digests(self) -> None:
        self.assertTrue(SYNTHETIC_LEDGER.is_file(), msg="missing synthetic ledger fixture")
        ledger = COMPILER_MOD.build_synthetic_calibrated_trajectory_benchmark_ledger()
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
        self.assertFalse(ledger["rows084_085_086_acceptance_claimed"])
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
        self.assertEqual(by_case["pan"]["expected_camera_dominant_sample_count"], 3)
        self.assertEqual(by_case["sliding_scuffing_fabric"]["expected_sliding_cue_count"], 1)
        self.assertEqual(by_case["sliding_scuffing_fabric"]["expected_scuffing_cue_count"], 1)
        self.assertEqual(by_case["sliding_scuffing_fabric"]["expected_fabric_cue_count"], 1)

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
        self.assertFalse(receipt["rows084_085_086_acceptance_claimed"])
        self.assertFalse(receipt["row_complete"])
        self.assertEqual(receipt["fixture_binding_count"], 4)
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


if __name__ == "__main__":
    unittest.main()
