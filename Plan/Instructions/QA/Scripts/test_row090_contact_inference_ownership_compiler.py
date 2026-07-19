#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_contact_inference_ownership.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/contact_inference_ownership_manifest.schema.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _absent_binding(blocker: str) -> dict:
    return {
        "present": False,
        "path": None,
        "sha256": None,
        "bytes": None,
        "blocker": blocker,
    }


def _base_packet() -> dict:
    return {
        "schema_version": "1.0",
        "manifest_id": "row090_contact_inference_manifest",
        "run_id": "run_090",
        "scene_id": "scene_090",
        "shot_id": "shot_090",
        "take_id": "take_090",
        "is_synthetic": True,
        "video_sha256": "a" * 64,
        "timeline": {
            "frame_rate": 24.0,
            "frame_count": 72,
            "frame_time_origin_seconds": 0.0,
            "target_sample_rate_hz": 48000,
        },
        "input_bindings": {
            "tracked_masks": _absent_binding("row085_incomplete"),
            "landmarks": _absent_binding("row086_incomplete"),
            "depth": _absent_binding("row088_incomplete"),
            "motion": _absent_binding("row087_incomplete"),
            "materials": _absent_binding("row089_incomplete"),
        },
        "dependency_authority": {
            "row085_complete": False,
            "row086_complete": False,
            "row087_complete": False,
            "row088_complete": False,
            "row089_complete": False,
        },
        "runtime_authority": {
            "runtime_proof_present": False,
            "combined_frame_contact_audio_review_present": False,
        },
        "visual_take_artifact": {
            "path": "fixtures/visual_take.bin",
            "sha256": "b" * 64,
            "bytes": 128,
            "media_type": "application/octet-stream",
        },
        "contact_evidence_artifact": {
            "path": "fixtures/contact_evidence.bin",
            "sha256": "c" * 64,
            "bytes": 256,
            "media_type": "application/octet-stream",
        },
        "contact_candidates": [
            {
                "contact_id": "contact_001",
                "source_owner": "character_1",
                "target_owner": "character_2",
                "source_body_region": "hand_right",
                "target_body_region_or_surface": "forearm_left",
                "object_or_surface": None,
                "source_entity_id": "character_1:hand_right",
                "target_entity_id": "character_2:forearm_left",
                "source_material": "skin",
                "target_material": "fabric",
                "approach_frame": 10,
                "onset_frame": 12,
                "peak_frame": 13,
                "release_frame": 14,
                "end_frame": 15,
                "force_band": "light",
                "visibility": "visible",
                "ownership_trusted": False,
                "confidence": 0.41,
                "authority_ceiling": "candidate",
                "decision": "candidate",
                "decision_reason": "dependency and input authority unsatisfied",
                "blockers": ["awaiting_row085_089"],
                "evidence": [{"kind": "declared_candidate", "ref": "fixture_packet"}],
                "audio_expected": True,
                "min_expected_force_events": 1,
                "max_expected_force_events": 1,
            },
            {
                "contact_id": "contact_002",
                "source_owner": None,
                "target_owner": "table_1",
                "source_body_region": None,
                "target_body_region_or_surface": "surface",
                "object_or_surface": "table_1",
                "source_entity_id": None,
                "target_entity_id": "table_1:surface",
                "source_material": "unknown",
                "target_material": "wood",
                "approach_frame": None,
                "onset_frame": 30,
                "peak_frame": 30,
                "release_frame": 31,
                "end_frame": 31,
                "force_band": "none",
                "visibility": "unknown",
                "ownership_trusted": False,
                "confidence": 0.1,
                "authority_ceiling": "candidate",
                "decision": "blocked",
                "decision_reason": "source ownership unknown",
                "blockers": ["unowned_source"],
                "evidence": [{"kind": "ownership_gap", "ref": "source_track_missing"}],
                "audio_expected": False,
                "min_expected_force_events": 0,
                "max_expected_force_events": 0,
            },
        ],
    }


class Row090ContactInferenceOwnershipCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "contact_packet.json"
            output_path = tmpdir / "contact_inference_ownership_manifest.json"
            _write_json(packet_path, packet)
            result = subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    "--input",
                    str(packet_path),
                    "--output",
                    str(output_path),
                ],
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

    def test_compiles_dependency_hold_candidate_and_blocked_contacts(self) -> None:
        result, compiled = self._run_compile(_base_packet(), expect_ok=True)
        self.assertEqual(result.returncode, 0)
        assert compiled is not None
        self.assertEqual(compiled["authority_summary"]["contact_count"], 2)
        self.assertEqual(compiled["authority_summary"]["candidate_count"], 1)
        self.assertEqual(compiled["authority_summary"]["blocked_count"], 1)
        self.assertEqual(compiled["authority_summary"]["certified_count"], 0)
        self.assertFalse(compiled["authority_summary"]["production_trust_allowed"])
        self.assertFalse(compiled["dependency_authority"]["all_dependencies_complete"])
        self.assertFalse(compiled["runtime_authority"]["runtime_ready"])
        self.assertEqual(compiled["contacts"][0]["phases"]["onset_sample"], 24000)
        self.assertFalse(compiled["visual_contact_manifest"]["contact_authority"]["production_trust_claim"])
        self.assertEqual(
            compiled["visual_contact_manifest"]["contact_authority"]["gold_mask_dependency_status"],
            "missing",
        )
        # Blocked unowned contact is excluded from consumer projection edges.
        self.assertEqual(len(compiled["visual_contact_manifest"]["contact_edges"]), 1)
        self.assertEqual(compiled["visual_contact_manifest"]["contact_edges"][0]["contact_edge_id"], "contact_001")

    def test_rejects_certified_decision_when_dependencies_unsatisfied(self) -> None:
        packet = _base_packet()
        packet["contact_candidates"][0]["decision"] = "certified"
        packet["contact_candidates"][0]["authority_ceiling"] = "certification"
        packet["contact_candidates"][0]["ownership_trusted"] = True
        self._run_compile(packet, expect_ok=False)

    def test_rejects_non_candidate_ceiling_under_dependency_hold(self) -> None:
        packet = _base_packet()
        packet["contact_candidates"][0]["authority_ceiling"] = "technical"
        self._run_compile(packet, expect_ok=False)

    def test_rejects_string_boolean_dependency_lookalike(self) -> None:
        packet = _base_packet()
        packet["dependency_authority"]["row085_complete"] = "false"  # type: ignore[assignment]
        self._run_compile(packet, expect_ok=False)

    def test_rejects_unordered_phase_frames(self) -> None:
        packet = _base_packet()
        packet["contact_candidates"][0]["peak_frame"] = 11
        self._run_compile(packet, expect_ok=False)

    def test_rejects_duplicate_contact_ids(self) -> None:
        packet = _base_packet()
        dup = copy.deepcopy(packet["contact_candidates"][1])
        dup["contact_id"] = packet["contact_candidates"][0]["contact_id"]
        packet["contact_candidates"].append(dup)
        self._run_compile(packet, expect_ok=False)

    def test_rejects_certification_ceiling_without_runtime_authority(self) -> None:
        packet = _base_packet()
        for key in packet["dependency_authority"]:
            packet["dependency_authority"][key] = True
        packet["input_bindings"] = {
            key: {
                "present": True,
                "path": f"fixtures/{key}.bin",
                "sha256": "d" * 64,
                "bytes": 16,
                "blocker": None,
            }
            for key in ("tracked_masks", "landmarks", "depth", "motion", "materials")
        }
        packet["contact_candidates"][0]["ownership_trusted"] = True
        packet["contact_candidates"][0]["decision"] = "candidate"
        packet["contact_candidates"][0]["authority_ceiling"] = "certification"
        packet["contact_candidates"][0]["blockers"] = []
        self._run_compile(packet, expect_ok=False)

    def test_schema_rejects_string_boolean_is_synthetic(self) -> None:
        _, compiled = self._run_compile(_base_packet(), expect_ok=True)
        assert compiled is not None
        compiled["is_synthetic"] = "false"
        errors = list(self.validator.iter_errors(compiled))
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
