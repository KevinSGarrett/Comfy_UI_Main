#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_visual_audio_event_manifest.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/visual_audio_event_manifest.schema.json"
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row091"
BLOCKED_HOLD_FIXTURE = FIXTURE_DIR / "decision_phase_blocked_dependency_hold.json"
SILENCE_HOLD_FIXTURE = FIXTURE_DIR / "decision_phase_intentional_silence_hold.json"
MIXED_HOLD_FIXTURE = FIXTURE_DIR / "decision_phase_mixed_coverage_hold.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_packet() -> dict:
    return {
        "schema_version": "1.0",
        "manifest_id": "row091_traceability_manifest",
        "video_sha256": "a" * 64,
        "scene_state_sha256": "b" * 64,
        "timeline": {
            "time_base": "24/1",
            "frame_count": 72,
            "duration_seconds": 3.0,
            "target_sample_rate_hz": 48000,
        },
        "detectors": [{"name": "contact_detector", "revision": "r1"}],
        "dependency_authority": {
            "row084_complete": False,
            "row090_complete": False,
        },
        "runtime_authority": {
            "runtime_proof_present": False,
            "audio_review_present": False,
            "combined_frame_contact_audio_review_present": False,
        },
        "rights_decision_sha256": "c" * 64,
        "traceability_events": [
            {
                "traceability_id": "trace_evt_001",
                "event_id": "evt_001",
                "event_type": "footstep",
                "source_owner": "character_1",
                "target_owner": "floor_1",
                "source_body_part": "foot_left",
                "target_body_part": None,
                "start_frame": 12,
                "anchor_frame": 13,
                "end_frame": 14,
                "material": "wood",
                "footwear": "boot",
                "force_band": "medium",
                "expected_layers": ["foley_step"],
                "confidence": 0.35,
                "authority_ceiling": "candidate",
                "evidence": [{"kind": "detector", "ref": "contact_detector"}],
                "decision": "blocked",
                "decision_reason": "dependency authority unsatisfied",
            },
            {
                "traceability_id": "trace_evt_002",
                "event_id": "evt_002",
                "event_type": "breath",
                "source_owner": "character_1",
                "target_owner": None,
                "source_body_part": None,
                "target_body_part": None,
                "start_frame": 20,
                "anchor_frame": 22,
                "end_frame": 25,
                "material": "air",
                "footwear": None,
                "force_band": "low",
                "expected_layers": ["breath_roomtone"],
                "confidence": 0.4,
                "authority_ceiling": "candidate",
                "evidence": [{"kind": "timeline", "ref": "shot_cut_001"}],
                "decision": "silent",
                "decision_reason": "intentional silence accepted under hold",
            },
        ],
    }


class Row091VisualAudioEventManifestCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "traceability_packet.json"
            output_path = tmpdir / "visual_audio_event_manifest.json"
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
                self.assertEqual(sorted(error.message for error in self.validator.iter_errors(compiled)), [])
                return result, compiled
            return result, None

    def test_compiles_dependency_hold_traceability_manifest_with_coverage(self) -> None:
        result, compiled = self._run_compile(_base_packet(), expect_ok=True)
        self.assertEqual(result.returncode, 0)
        assert compiled is not None
        self.assertEqual(compiled["coverage"]["required_events"], 2)
        self.assertEqual(compiled["coverage"]["covered_events"], 0)
        self.assertEqual(compiled["coverage"]["silent_events"], 1)
        self.assertEqual(compiled["coverage"]["blocked_events"], 1)
        self.assertTrue(
            all(
                any(evidence.get("kind") == "traceability_decision" for evidence in event["evidence"])
                for event in compiled["events"]
            )
        )

    def test_rejects_covered_decision_when_dependencies_unsatisfied(self) -> None:
        packet = _base_packet()
        packet["traceability_events"][0]["decision"] = "cover"
        self._run_compile(packet, expect_ok=False)

    def test_rejects_certification_ceiling_without_runtime_authority(self) -> None:
        packet = _base_packet()
        packet["dependency_authority"]["row084_complete"] = True
        packet["dependency_authority"]["row090_complete"] = True
        packet["traceability_events"][0]["decision"] = "cover"
        packet["traceability_events"][0]["authority_ceiling"] = "certification"
        self._run_compile(packet, expect_ok=False)

    def test_rejects_duplicate_traceability_ids(self) -> None:
        packet = _base_packet()
        dup = copy.deepcopy(packet["traceability_events"][1])
        dup["event_id"] = "evt_003"
        dup["traceability_id"] = packet["traceability_events"][0]["traceability_id"]
        packet["traceability_events"].append(dup)
        self._run_compile(packet, expect_ok=False)

    def test_rejects_timeline_duration_disagreeing_with_frame_count(self) -> None:
        packet = _base_packet()
        packet["timeline"]["duration_seconds"] = 9.0
        self._run_compile(packet, expect_ok=False)

    def test_rejects_invalid_dependency_evidence_sha256(self) -> None:
        packet = _base_packet()
        packet["dependency_authority"]["row084_evidence_sha256"] = "not-a-sha256"
        self._run_compile(packet, expect_ok=False)

    def _load_fixture(self, path: Path) -> dict:
        self.assertTrue(path.is_file(), f"missing fixture: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _canonical_sha256(self, payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def test_fixture_blocked_dependency_hold_compiles(self) -> None:
        packet = self._load_fixture(BLOCKED_HOLD_FIXTURE)
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertEqual(compiled["coverage"]["required_events"], 1)
        self.assertEqual(compiled["coverage"]["blocked_events"], 1)
        self.assertEqual(compiled["coverage"]["covered_events"], 0)
        self.assertEqual(compiled["events"][0]["event_id"], "evt_blocked_footstep_001")
        self.assertEqual(compiled["events"][0]["authority_ceiling"], "candidate")
        self.assertEqual(compiled["events"][0]["anchor_sample"], 26000)

    def test_fixture_intentional_silence_hold_compiles(self) -> None:
        packet = self._load_fixture(SILENCE_HOLD_FIXTURE)
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertEqual(compiled["coverage"]["silent_events"], 1)
        self.assertEqual(compiled["coverage"]["blocked_events"], 0)
        self.assertEqual(compiled["events"][0]["event_id"], "evt_silent_breath_001")
        self.assertEqual(compiled["events"][0]["anchor_sample"], 44000)
        self.assertTrue(
            any(evidence.get("kind") == "traceability_decision" for evidence in compiled["events"][0]["evidence"])
        )

    def test_fixture_mixed_coverage_hold_compiles(self) -> None:
        packet = self._load_fixture(MIXED_HOLD_FIXTURE)
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertEqual(compiled["coverage"]["required_events"], 2)
        self.assertEqual(compiled["coverage"]["blocked_events"], 1)
        self.assertEqual(compiled["coverage"]["silent_events"], 1)
        self.assertEqual(compiled["coverage"]["covered_events"], 0)
        by_id = {event["event_id"]: event for event in compiled["events"]}
        self.assertIn("evt_mixed_blocked_001", by_id)
        self.assertIn("evt_mixed_silent_002", by_id)

    def test_fixture_decision_phase_packets_deterministic_replay_hash(self) -> None:
        digests: dict[str, str] = {}
        for path in (BLOCKED_HOLD_FIXTURE, SILENCE_HOLD_FIXTURE, MIXED_HOLD_FIXTURE):
            packet = self._load_fixture(path)
            _, first = self._run_compile(packet, expect_ok=True)
            _, second = self._run_compile(packet, expect_ok=True)
            assert first is not None and second is not None
            digest_a = self._canonical_sha256(first)
            digest_b = self._canonical_sha256(second)
            self.assertEqual(digest_a, digest_b, f"non-deterministic compile for {path.name}")
            self.assertEqual(first["coverage"]["covered_events"], 0)
            digests[path.name] = digest_a
        self.assertEqual(len(set(digests.values())), 3)


if __name__ == "__main__":
    unittest.main()
