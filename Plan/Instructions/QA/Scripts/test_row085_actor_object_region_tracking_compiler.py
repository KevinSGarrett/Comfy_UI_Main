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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_actor_object_region_tracking.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/actor_object_region_tracking_manifest.schema.json"
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row085"
SYNTHETIC_LEDGER = FIXTURE_DIR / "synthetic_tracking_benchmark_ledger.json"
FIXTURE_PACKETS = (
    "case_occlusion_gap.json",
    "case_reappearance.json",
    "case_lost_track.json",
)
TRACKING_CASES = ("lost_track", "occlusion_gap", "reappearance")


def _load_compiler_module():
    spec = importlib.util.spec_from_file_location("compile_wave64_actor_object_region_tracking", COMPILER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER_MOD = _load_compiler_module()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sample(frame_index: int, pts: int, *, state: str = "active", visibility: str = "visible", confidence: float = 0.91) -> dict:
    return {
        "frame_index": frame_index,
        "pts": pts,
        "bbox_xywh": [10.0 + frame_index, 20.0, 40.0, 80.0],
        "visibility": visibility,
        "state": state,
        "confidence": confidence,
        "mask_ref": f"mask_{frame_index}",
        "occluder_owner_ids": ["prop_table"] if state == "occluded" else [],
        "depth_order": 1,
    }


def _base_packet() -> dict:
    return {
        "schema_version": "1.0.0",
        "manifest_id": "row085_tracking_manifest",
        "revision": "r001",
        "run_id": "run_085",
        "scene_id": "scene_085",
        "shot_id": "shot_085",
        "take_id": "take_085",
        "is_synthetic": True,
        "video_sha256": "a" * 64,
        "timeline_binding": {
            "timeline_id": "timeline_row084_fixture",
            "timeline_sha256": "b" * 64,
            "frame_count": 48,
            "frame_rate": 24.0,
            "frame_time_origin_seconds": 0.0,
        },
        "detector_stack": {
            "detector_id": "fixture_detector",
            "segmenter_id": "fixture_segmenter",
            "tracker_id": "fixture_tracker",
            "association_id": "fixture_association",
            "revision": "fixture_v1",
            "parameter_digest_sha256": "c" * 64,
        },
        "dependency_authority": {"row084_complete": False},
        "runtime_authority": {
            "annotated_benchmark_pass": False,
            "runtime_receipt_present": False,
            "combined_track_overlay_contact_audio_review_present": False,
        },
        "tracks": [
            {
                "track_id": "track_actor_1",
                "owner_id": "character_1",
                "entity_class": "actor",
                "parent_owner_id": None,
                "samples": [
                    _sample(0, 0),
                    _sample(1, 1),
                    _sample(2, 2, state="occluded", visibility="occluded"),
                    _sample(5, 5, state="reidentified", visibility="visible"),
                ],
                "lifecycle_events": [
                    {
                        "event_type": "spawn",
                        "frame_index": 0,
                        "reason": "actor enters frame",
                        "related_track_id": None,
                    },
                    {
                        "event_type": "occlusion_gap_start",
                        "frame_index": 2,
                        "reason": "crossed behind prop",
                        "related_track_id": "track_prop_table",
                    },
                    {
                        "event_type": "occlusion_gap_end",
                        "frame_index": 4,
                        "reason": "cleared prop",
                        "related_track_id": "track_prop_table",
                    },
                    {
                        "event_type": "reappearance",
                        "frame_index": 5,
                        "reason": "reassociated after occlusion",
                        "related_track_id": None,
                    },
                ],
            },
            {
                "track_id": "track_hand_1",
                "owner_id": "character_1_hand_right",
                "entity_class": "hand",
                "parent_owner_id": "character_1",
                "samples": [_sample(0, 0), _sample(1, 1)],
                "lifecycle_events": [
                    {
                        "event_type": "spawn",
                        "frame_index": 0,
                        "reason": "hand attached to actor",
                        "related_track_id": "track_actor_1",
                    }
                ],
            },
            {
                "track_id": "track_prop_table",
                "owner_id": "prop_table",
                "entity_class": "prop",
                "parent_owner_id": None,
                "samples": [_sample(0, 0), _sample(10, 10)],
                "lifecycle_events": [
                    {
                        "event_type": "spawn",
                        "frame_index": 0,
                        "reason": "static prop",
                        "related_track_id": None,
                    }
                ],
            },
            {
                "track_id": "track_surface_floor",
                "owner_id": "surface_floor",
                "entity_class": "surface",
                "parent_owner_id": None,
                "samples": [_sample(0, 0), _sample(10, 10)],
                "lifecycle_events": [
                    {
                        "event_type": "spawn",
                        "frame_index": 0,
                        "reason": "static surface",
                        "related_track_id": None,
                    }
                ],
            },
        ],
        "metrics": {
            "identity_switch_count": 0,
            "lost_track_count": 0,
            "occlusion_gap_frames": 3,
            "reappearance_count": 1,
            "fragmentation_count": 0,
            "merge_count": 0,
            "split_count": 0,
            "false_positive_count": 0,
            "false_negative_count": 0,
        },
        "thresholds": {
            "max_identity_switch_count": 0,
            "max_lost_track_count": 0,
            "max_occlusion_gap_frames": 12,
            "max_fragmentation_count": 0,
            "max_merge_count": 0,
            "max_split_count": 0,
            "min_track_confidence": 0.5,
        },
        "provenance": {"fixture": "row085_unit"},
    }


class Row085ActorObjectRegionTrackingCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "tracking_packet.json"
            output_path = tmpdir / "actor_object_region_tracking_manifest.json"
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

    def test_compiles_hold_manifest_with_taxonomy_and_metrics(self) -> None:
        _, compiled = self._run_compile(_base_packet(), expect_ok=True)
        assert compiled is not None
        self.assertFalse(compiled["row_complete"])
        self.assertFalse(compiled["production_completion_allowed"])
        self.assertEqual(compiled["authority_ceiling"], "candidate")
        self.assertFalse(compiled["dependency_authority"]["dependency_ready"])
        self.assertFalse(compiled["runtime_authority"]["runtime_ready"])
        self.assertFalse(compiled["authority_summary"]["contact_foley_certification_allowed"])
        self.assertIn("dependency_row084_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertEqual(compiled["metrics"]["occlusion_gap_frames"], 3)
        self.assertEqual(compiled["metrics"]["reappearance_count"], 1)
        self.assertIn("actor", compiled["entity_taxonomy_present"])
        self.assertIn("hand", compiled["entity_taxonomy_present"])
        self.assertEqual(len(compiled["manifest_sha256"]), 64)

    def test_rejects_duplicate_frame_indices(self) -> None:
        packet = _base_packet()
        packet["tracks"][0]["samples"][1]["frame_index"] = 0
        packet["tracks"][0]["samples"][1]["pts"] = 0
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("strictly increasing", result.stderr + result.stdout)

    def test_rejects_decreasing_pts(self) -> None:
        packet = _base_packet()
        packet["tracks"][0]["samples"][1]["pts"] = 0
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("pts must be unique and strictly increasing", result.stderr + result.stdout)

    def test_rejects_missing_required_entity_taxonomy(self) -> None:
        packet = _base_packet()
        packet["tracks"] = [track for track in packet["tracks"] if track["entity_class"] != "surface"]
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("entity taxonomy incomplete", result.stderr + result.stdout)

    def test_rejects_body_region_without_parent_owner(self) -> None:
        packet = _base_packet()
        packet["tracks"][1]["parent_owner_id"] = None
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("requires parent_owner_id", result.stderr + result.stdout)

    def test_rejects_metric_mismatch_against_lifecycle_events(self) -> None:
        packet = _base_packet()
        packet["metrics"]["reappearance_count"] = 99
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("does not match derived lifecycle count", result.stderr + result.stdout)

    def test_identity_switch_blocks_contact_foley_certification(self) -> None:
        packet = _base_packet()
        packet["tracks"][0]["lifecycle_events"].append(
            {
                "event_type": "identity_switch",
                "frame_index": 5,
                "reason": "crossed similar actor",
                "related_track_id": "track_actor_2",
            }
        )
        packet["metrics"]["identity_switch_count"] = 1
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertTrue(compiled["authority_summary"]["ownership_unsupported"])
        self.assertFalse(compiled["authority_summary"]["contact_foley_certification_allowed"])
        self.assertIn(
            "unsupported_ownership_blocks_contact_foley_certification",
            compiled["authority_summary"]["hold_reasons"],
        )
        self.assertFalse(compiled["tracks"][0]["ownership_trusted"])

    def test_schema_requires_metrics_and_forbids_open_properties(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema.get("additionalProperties", True))
        required = set(schema["required"])
        self.assertIn("metrics", required)
        self.assertIn("thresholds", required)
        self.assertIn("tracks", required)
        self.assertIn("row_complete", required)

    def test_fixture_packets_cover_occlusion_reappearance_lost_track(self) -> None:
        for name in FIXTURE_PACKETS:
            self.assertTrue((FIXTURE_DIR / name).is_file(), msg=f"missing fixture {name}")

        _, occlusion = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_occlusion_gap.json"),
            expect_ok=True,
        )
        assert occlusion is not None
        self.assertEqual(occlusion["metrics"]["occlusion_gap_frames"], 6)
        self.assertEqual(occlusion["metrics"]["reappearance_count"], 0)
        self.assertEqual(occlusion["metrics"]["lost_track_count"], 0)
        self.assertFalse(occlusion["row_complete"])
        self.assertFalse(occlusion["production_completion_allowed"])
        self.assertFalse(occlusion["runtime_authority"]["annotated_benchmark_pass"])
        self.assertFalse(occlusion["authority_summary"]["contact_foley_certification_allowed"])
        self.assertIn("dependency_row084_incomplete", occlusion["authority_summary"]["hold_reasons"])

        _, reappearance = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_reappearance.json"),
            expect_ok=True,
        )
        assert reappearance is not None
        self.assertEqual(reappearance["metrics"]["occlusion_gap_frames"], 3)
        self.assertEqual(reappearance["metrics"]["reappearance_count"], 2)
        self.assertEqual(reappearance["metrics"]["lost_track_count"], 0)
        actor = next(track for track in reappearance["tracks"] if track["track_id"] == "track_actor_1")
        self.assertTrue(any(event["event_type"] == "reappearance" for event in actor["lifecycle_events"]))
        self.assertTrue(any(sample["state"] == "reidentified" for sample in actor["samples"]))
        self.assertFalse(reappearance["row_complete"])
        self.assertFalse(reappearance["authority_summary"]["contact_foley_certification_allowed"])

        _, lost = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_lost_track.json"),
            expect_ok=True,
        )
        assert lost is not None
        self.assertEqual(lost["metrics"]["lost_track_count"], 2)
        self.assertEqual(lost["metrics"]["occlusion_gap_frames"], 0)
        self.assertEqual(lost["metrics"]["reappearance_count"], 0)
        self.assertTrue(lost["authority_summary"]["ownership_unsupported"])
        self.assertFalse(lost["authority_summary"]["contact_foley_certification_allowed"])
        self.assertIn(
            "unsupported_ownership_blocks_contact_foley_certification",
            lost["authority_summary"]["hold_reasons"],
        )
        self.assertFalse(lost["tracks"][0]["ownership_trusted"])
        self.assertFalse(lost["row_complete"])
        self.assertFalse(lost["production_completion_allowed"])

    def test_deterministic_replay_and_tamper_hash_check(self) -> None:
        digests: dict[str, str] = {}
        for name in FIXTURE_PACKETS:
            packet = COMPILER_MOD.load_fixture_packet(name)
            first = COMPILER_MOD.compile_manifest(packet)
            second = COMPILER_MOD.compile_manifest(packet)
            # Wall-clock created_at may differ; content-addressed digest must replay.
            self.assertNotEqual(first.get("created_at"), "__sentinel__")
            second["created_at"] = "2000-01-01T00:00:00Z"
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"], msg=f"non-deterministic {name}")
            self.assertEqual(
                COMPILER_MOD.verify_manifest_integrity(first),
                first["manifest_sha256"],
            )
            self.assertEqual(
                COMPILER_MOD.verify_manifest_integrity(second),
                second["manifest_sha256"],
            )
            self.assertFalse(first["row_complete"])
            self.assertFalse(first["production_completion_allowed"])
            digests[name] = first["manifest_sha256"]

        self.assertEqual(len(set(digests.values())), 3)

        tampered = json.loads(json.dumps(COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_occlusion_gap.json")
        )))
        tampered["metrics"]["occlusion_gap_frames"] = 99
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_manifest_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

        hash_tampered = json.loads(json.dumps(COMPILER_MOD.compile_manifest(
            COMPILER_MOD.load_fixture_packet("case_reappearance.json")
        )))
        hash_tampered["manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError) as ctx2:
            COMPILER_MOD.verify_manifest_integrity(hash_tampered)
        self.assertIn("tamper/replay mismatch", str(ctx2.exception))

    def test_synthetic_tracking_benchmark_ledger_binds_fixture_digests(self) -> None:
        self.assertTrue(SYNTHETIC_LEDGER.is_file(), msg="missing synthetic ledger fixture")
        ledger = COMPILER_MOD.build_synthetic_tracking_benchmark_ledger()
        checked_in = json.loads(SYNTHETIC_LEDGER.read_text(encoding="utf-8"))

        self.assertEqual(ledger, checked_in)
        self.assertEqual(
            COMPILER_MOD.verify_synthetic_benchmark_ledger_integrity(ledger),
            ledger["ledger_sha256"],
        )
        self.assertFalse(ledger["row_complete"])
        self.assertFalse(ledger["production_completion_allowed"])
        self.assertFalse(ledger["production_benchmark"])
        self.assertFalse(ledger["annotated_tracking_benchmark_pass"])
        self.assertFalse(ledger["visual_review_claimed"])
        self.assertFalse(ledger["row084_acceptance_claimed"])
        self.assertEqual(ledger["authority_ceiling"], "fixture_synthetic_only")
        self.assertTrue(ledger["is_synthetic"])

        binding_by_name = {item["fixture_name"]: item for item in ledger["fixture_bindings"]}
        self.assertEqual(set(binding_by_name), set(FIXTURE_PACKETS))
        for name in FIXTURE_PACKETS:
            expected_file_digest = COMPILER_MOD.fixture_file_sha256(name)
            compiled = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet(name))
            self.assertEqual(binding_by_name[name]["fixture_file_sha256"], expected_file_digest)
            self.assertEqual(
                binding_by_name[name]["compiled_manifest_sha256"],
                compiled["manifest_sha256"],
            )
            self.assertFalse(binding_by_name[name]["row_complete"])

        by_case = {item["case_id"]: item for item in ledger["tracking_metric_expectations"]}
        self.assertEqual(set(by_case), set(TRACKING_CASES))
        self.assertEqual(by_case["occlusion_gap"]["expected_occlusion_gap_frames"], 6)
        self.assertEqual(by_case["occlusion_gap"]["expected_reappearance_count"], 0)
        self.assertEqual(by_case["occlusion_gap"]["expected_lost_track_count"], 0)
        self.assertEqual(by_case["reappearance"]["expected_occlusion_gap_frames"], 3)
        self.assertEqual(by_case["reappearance"]["expected_reappearance_count"], 2)
        self.assertEqual(by_case["reappearance"]["expected_lost_track_count"], 0)
        self.assertEqual(by_case["lost_track"]["expected_lost_track_count"], 2)
        self.assertEqual(by_case["lost_track"]["expected_occlusion_gap_frames"], 0)
        self.assertEqual(by_case["lost_track"]["expected_reappearance_count"], 0)

        tampered = json.loads(json.dumps(ledger))
        tampered["annotated_tracking_benchmark_pass"] = True
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_synthetic_benchmark_ledger_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

    def test_ledger_vs_compiled_manifest_expectation_verifier_rejects_digest_drift(self) -> None:
        receipt = COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations()
        self.assertEqual(receipt["status"], "ok")
        self.assertTrue(receipt["digest_drift_rejected"])
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_benchmark"])
        self.assertFalse(receipt["annotated_tracking_benchmark_pass"])
        self.assertFalse(receipt["visual_review_claimed"])
        self.assertFalse(receipt["row084_acceptance_claimed"])
        self.assertEqual(receipt["fixture_binding_count"], 3)
        self.assertEqual(receipt["tracking_metric_expectation_count"], 3)
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
        self.assertFalse(cli_receipt["annotated_tracking_benchmark_pass"])

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

        expectation_drifted = json.loads(json.dumps(ledger))
        expectation_drifted["tracking_metric_expectations"][0][
            "expected_occlusion_gap_frames"
        ] = 99
        expectation_body = {
            key: value for key, value in expectation_drifted.items() if key != "ledger_sha256"
        }
        expectation_drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(expectation_body)
        with self.assertRaises(ValueError) as ctx3:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(
                expectation_drifted
            )
        self.assertIn("expected_occlusion_gap_frames mismatch", str(ctx3.exception))

        pass_claimed = json.loads(json.dumps(ledger))
        pass_claimed["annotated_tracking_benchmark_pass"] = True
        pass_body = {key: value for key, value in pass_claimed.items() if key != "ledger_sha256"}
        pass_claimed["ledger_sha256"] = COMPILER_MOD._canonical_sha256(pass_body)
        with self.assertRaises(ValueError) as ctx4:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(pass_claimed)
        self.assertIn("annotated_tracking_benchmark_pass=false", str(ctx4.exception))

        visual_claimed = json.loads(json.dumps(ledger))
        visual_claimed["visual_review_claimed"] = True
        visual_body = {
            key: value for key, value in visual_claimed.items() if key != "ledger_sha256"
        }
        visual_claimed["ledger_sha256"] = COMPILER_MOD._canonical_sha256(visual_body)
        with self.assertRaises(ValueError) as ctx5:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(visual_claimed)
        self.assertIn("visual_review_claimed=false", str(ctx5.exception))

        row084_claimed = json.loads(json.dumps(ledger))
        row084_claimed["row084_acceptance_claimed"] = True
        row084_body = {
            key: value for key, value in row084_claimed.items() if key != "ledger_sha256"
        }
        row084_claimed["ledger_sha256"] = COMPILER_MOD._canonical_sha256(row084_body)
        with self.assertRaises(ValueError) as ctx6:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(row084_claimed)
        self.assertIn("row084_acceptance_claimed=false", str(ctx6.exception))


if __name__ == "__main__":
    unittest.main()
