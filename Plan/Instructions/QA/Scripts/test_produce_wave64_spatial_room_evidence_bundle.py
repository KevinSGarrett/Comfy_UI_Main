#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_spatial_room_evidence_bundle.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_spatial_room_evidence_bundle.schema.json"
SPEC = importlib.util.spec_from_file_location("row029_producer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PRODUCER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRODUCER)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpatialRoomBundleProducerTests(unittest.TestCase):
    def build_case(self, base: Path) -> dict[str, Path]:
        base.mkdir(parents=True, exist_ok=True)
        spatial = {
            "mix_id": "mix",
            "scene_id": "scene",
            "shot_id": "shot",
            "audio_events": ["dialogue"],
            "room_profile": "small_soft_room",
            "camera_listener_state": {"camera": "present", "listener": "present"},
            "spatial_layers": [],
            "qa_scores": {},
            "promotion_decision": "hold",
            "run_id": "run",
            "take_id": "take",
            "is_synthetic": True,
        }
        room = {
            "room_profile_id": "small_soft_room",
            "environment_type": "interior",
            "room_size": "small",
            "surface_materials": ["fabric"],
            "furniture_density": "medium",
            "reverb_profile": "short_warm_room",
            "ambience_profile": "quiet_room_tone",
            "run_id": "run",
            "scene_id": "scene",
            "shot_id": "shot",
            "take_id": "take",
            "is_synthetic": True,
        }
        paths = {"spatial_mix": base / "spatial.json", "room_acoustics": base / "room.json"}
        paths["spatial_mix"].write_text(json.dumps(spatial) + "\n", encoding="utf-8")
        paths["room_acoustics"].write_text(json.dumps(room) + "\n", encoding="utf-8")
        for name in (
            "dry_dialogue",
            "spatial_dialogue",
            "ambience_bed",
            "final_mix",
            "previous_ambience",
            "current_ambience",
        ):
            paths[name] = base / f"{name}.wav"
            paths[name].write_bytes(f"RIFF-{name}".encode())
        paths["optional_dir"] = base / "optional"
        paths["optional_dir"].mkdir()
        paths["output"] = base / "request.json"
        return paths

    def args(self, paths: dict[str, Path]) -> list[str]:
        result: list[str] = []
        for name in (
            "spatial_mix",
            "room_acoustics",
            "dry_dialogue",
            "spatial_dialogue",
            "ambience_bed",
            "final_mix",
            "previous_ambience",
            "current_ambience",
            "optional_dir",
            "output",
        ):
            result.extend((f"--{name.replace('_', '-')}", str(paths[name])))
        result.extend(
            (
                "--run-id", "run", "--scene-id", "scene", "--shot-id", "shot", "--take-id", "take",
                "--listener-position", "0,0,0", "--camera-position", "0.2,0,0",
                "--camera-right", "1,0,0", "--camera-forward", "0,1,0", "--source-position", "1,1,0",
            )
        )
        return result

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(ROOT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_emits_schema_valid_bundle_with_registry_thresholds_and_null_proofs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            result = self.run_cli(*self.args(paths))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(paths["output"].read_text(encoding="utf-8"))
            Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(payload)
            self.assertEqual(payload["threshold_overrides"]["min_rt60_seconds"], 0.2)
            self.assertEqual(payload["threshold_overrides"]["max_rt60_seconds"], 0.8)
            self.assertTrue(payload["is_synthetic"])
            self.assertEqual(payload["evidence_origin"], "synthetic_fixture")
            self.assertTrue(all(payload[field] is None for field in (
                "playback_proof_binding", "runtime_proof_binding", "production_authority_bundle_binding"
            )))

    def test_binds_fixed_optional_files_and_embeds_hard_cut_contract(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            optional = paths["optional_dir"]
            for filename in ("playback_proof.json", "runtime_proof.json", "production_authority_bundle.json"):
                (optional / filename).write_text(json.dumps({"kind": filename}) + "\n", encoding="utf-8")
            contract = {"cut_id": "cut", "reason": "fixture_reset", "approver_id": "fixture_cut_approver"}
            (optional / "hard_cut_contract.json").write_text(json.dumps(contract) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 0)
            payload = json.loads(paths["output"].read_text(encoding="utf-8"))
            self.assertEqual(payload["playback_proof_binding"]["sha256"], sha256(optional / "playback_proof.json"))
            self.assertEqual(payload["ambience_continuity_evidence"]["hard_cut_contract"], contract)

    def test_production_flag_requires_matching_manifest_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            failed = self.run_cli(*self.args(paths), "--production-input")
            self.assertEqual(failed.returncode, 2)
            for name in ("spatial_mix", "room_acoustics"):
                payload = json.loads(paths[name].read_text(encoding="utf-8"))
                payload["is_synthetic"] = False
                paths[name].write_text(json.dumps(payload) + "\n", encoding="utf-8")
            passed = self.run_cli(*self.args(paths), "--production-input")
            self.assertEqual(passed.returncode, 0, passed.stdout)
            payload = json.loads(paths["output"].read_text(encoding="utf-8"))
            self.assertFalse(payload["is_synthetic"])
            self.assertEqual(payload["evidence_origin"], "technical_capture")

    def test_rejects_manifest_identity_mismatch_and_unknown_room_profile(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            spatial = json.loads(paths["spatial_mix"].read_text(encoding="utf-8"))
            spatial["scene_id"] = "wrong"
            paths["spatial_mix"].write_text(json.dumps(spatial) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            spatial["scene_id"] = "scene"
            paths["spatial_mix"].write_text(json.dumps(spatial) + "\n", encoding="utf-8")
            room = json.loads(paths["room_acoustics"].read_text(encoding="utf-8"))
            room["room_profile_id"] = "unknown"
            paths["room_acoustics"].write_text(json.dumps(room) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_missing_manifest_identity_and_malformed_optional_json(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            spatial = json.loads(paths["spatial_mix"].read_text(encoding="utf-8"))
            del spatial["run_id"]
            paths["spatial_mix"].write_text(json.dumps(spatial) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "optional")
            (paths["optional_dir"] / "runtime_proof.json").write_text("", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            (paths["optional_dir"] / "runtime_proof.json").write_text("[]\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_invalid_vector_missing_artifact_and_duplicate_binding(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            args = self.args(paths)
            index = args.index("--source-position") + 1
            args[index] = "1,2"
            self.assertEqual(self.run_cli(*args).returncode, 2)
            paths = self.build_case(Path(temporary) / "missing")
            paths["final_mix"].unlink()
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "duplicate")
            paths["current_ambience"] = paths["previous_ambience"]
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_root_escape_output_collision_and_output_under_optional_dir(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            outside = Path(tempfile.gettempdir()) / "row029_outside.wav"
            outside.write_bytes(b"outside")
            paths["dry_dialogue"] = outside
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            outside.unlink(missing_ok=True)
            paths = self.build_case(Path(temporary) / "collision")
            paths["output"] = paths["spatial_mix"]
            original = paths["spatial_mix"].read_text(encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertEqual(paths["spatial_mix"].read_text(encoding="utf-8"), original)
            paths = self.build_case(Path(temporary) / "optional-output")
            paths["output"] = paths["optional_dir"] / "runtime_proof.json"
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertFalse(paths["output"].exists())

    def test_existing_output_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            paths["output"].write_text("keep", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertEqual(paths["output"].read_text(encoding="utf-8"), "keep")

    def test_canonical_root_guard_and_atomic_race_preserve_destination(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            args = self.args(paths)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(Path(temporary)), *args],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(paths["output"].exists())

            destination = Path(temporary) / "race.json"
            original_link = os.link

            def create_racing_destination(source: str, target: str) -> None:
                destination.write_text("racer", encoding="utf-8")
                original_link(source, target)

            with mock.patch.object(PRODUCER.os, "link", side_effect=create_racing_destination):
                with self.assertRaises(FileExistsError):
                    PRODUCER.write_atomic(destination, {"value": 1})
            self.assertEqual(destination.read_text(encoding="utf-8"), "racer")


if __name__ == "__main__":
    unittest.main()
