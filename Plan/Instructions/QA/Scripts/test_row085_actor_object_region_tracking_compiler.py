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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_actor_object_region_tracking.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/actor_object_region_tracking_manifest.schema.json"


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


if __name__ == "__main__":
    unittest.main()
