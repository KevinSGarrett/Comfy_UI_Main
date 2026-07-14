from __future__ import annotations

import importlib.util
import hashlib
import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_video_keyframe_handoff.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/video_keyframe_handoff.schema.json"
SPEC = importlib.util.spec_from_file_location("video_keyframe_handoff", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class VideoKeyframeHandoffTests(unittest.TestCase):
    def fixture(self, root: Path) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for name, source in MODULE.SOURCES.items():
            target = root / "sources" / f"{name}.json"
            value = json.loads((ROOT / source).read_text(encoding="utf-8-sig"))
            if name == "base_qa":
                value["outputs"]["generated_image"]["path"] = "source.png"
                value["inputs"]["profile"]["path"] = "profile.json"
                value["inputs"]["control_map"]["path"] = "control.png"
            if name == "runtime":
                value["input"]["path"] = "source.png"
            write(target, value)
            paths[name] = target
        source_image = ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_standing_seed711670301_20260711T035900-0500/images/normal_v4_fullbody_standing_711670301_00001_.png"
        shutil.copyfile(source_image, root / "source.png")
        profile_source = ROOT / "PromptProfiles/base_generation/controlnet_normal_v1_followup/normal_v4_full_body_standing_seed711670301.json"
        shutil.copyfile(profile_source, root / "profile.json")
        control_source = ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/normal_full_body_standing_w70_v1/controlnet_normal_bae_full_body_standing_w70_v1.png"
        shutil.copyfile(control_source, root / "control.png")
        return paths

    def build(self, root: Path, sources: dict[str, Path] | None = None):
        return MODULE.build(root, sources or self.fixture(root), "2026-07-14T14:00:00-05:00", SCHEMA)

    def mutate(self, path: Path, callback) -> None:
        value = json.loads(path.read_text())
        callback(value)
        write(path, value)

    def test_candidate_is_schema_valid_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, readiness = self.build(Path(temporary))
            Draft202012Validator(json.loads(SCHEMA.read_text())).validate(candidate)
            self.assertTrue(candidate["candidate"]["candidate_only"])
            self.assertFalse(candidate["eligibility"]["production_keyframe_eligible"])
            self.assertEqual(candidate["candidate"]["frame_rate_target"], 24)
            self.assertEqual(candidate["candidate"]["duration_seconds"], 2.04)
            self.assertIn("technical", candidate["provenance"]["source_bindings"])
            self.assertEqual(readiness["check_summary"], {"checked": 13, "passed": 13, "failed": 0})

    def test_checked_out_candidate_bytes_match_canonical_binding(self) -> None:
        candidate_path = ROOT / MODULE.CANDIDATE
        canonical = json.loads((ROOT / MODULE.CANONICAL).read_text(encoding="utf-8"))
        binding = canonical["keyframe_candidate_state"]["candidate_manifest"]
        self.assertEqual(candidate_path.stat().st_size, binding["bytes"])
        self.assertEqual(hashlib.sha256(candidate_path.read_bytes()).hexdigest(), binding["sha256"])

    def test_exact_passing_candidate_gates_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _ = self.build(Path(temporary))
            gates = candidate["eligibility"]["gates"]
            for name in (
                "base_image_qa_passed",
                "base_image_scored",
                "character_count_body_visibility_passed",
                "output_hash_recorded",
                "engine_route_valid",
                "model_assets_registered",
                "output_path_defined",
            ):
                self.assertTrue(gates[name], name)

    def test_exact_missing_eligibility_gates_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _ = self.build(Path(temporary))
            expected = [name for name in MODULE.GATE_KEYS if not candidate["eligibility"]["gates"][name]]
            self.assertEqual(candidate["eligibility"]["failed_gates"], expected)
            self.assertIn("refine_bridge_qa_passed", expected)
            self.assertIn("frame_contract_exported", expected)
            self.assertIn("promotion_allowed", expected)

    def test_source_image_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = self.fixture(root)
            (root / "source.png").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "image hash drift"):
                self.build(root, sources)

    def test_runtime_input_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = self.fixture(root)
            self.mutate(sources["runtime"], lambda value: value["input"].update({"sha256": "0" * 64}))
            with self.assertRaisesRegex(ValueError, "runtime input hash"):
                self.build(root, sources)

    def test_base_qa_failure_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = self.fixture(root)
            self.mutate(sources["base_qa"], lambda value: value.update({"pass": False}))
            with self.assertRaisesRegex(ValueError, "base image QA did not pass"):
                self.build(root, sources)

    def test_promotion_overclaim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = self.fixture(root)
            def promote(value):
                value["current_promotion_state"].update({"decision": "promote", "promotion_allowed": True, "promoted_lane_count": 1})
            self.mutate(sources["promotion"], promote)
            with self.assertRaisesRegex(ValueError, "unexpected promotion decision"):
                self.build(root, sources)

    def test_semantic_validator_rejects_eligibility_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _ = self.build(Path(temporary))
            candidate["eligibility"]["production_keyframe_eligible"] = True
            with self.assertRaisesRegex(ValueError, "eligibility overclaim"):
                MODULE.validate_semantics(candidate)

    def test_semantic_validator_rejects_failed_gate_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _ = self.build(Path(temporary))
            candidate["eligibility"]["failed_gates"] = []
            with self.assertRaisesRegex(ValueError, "failed gate list"):
                MODULE.validate_semantics(candidate)

    def test_schema_rejects_candidate_only_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _ = self.build(Path(temporary))
            overclaim = deepcopy(candidate)
            overclaim["promotion"]["promotion_allowed"] = True
            with self.assertRaises(ValidationError):
                Draft202012Validator(json.loads(SCHEMA.read_text())).validate(overclaim)

    def test_schema_accepts_complete_promoted_success_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, _ = self.build(Path(temporary))
            promoted = deepcopy(candidate)
            promoted["candidate"]["candidate_only"] = False
            promoted["eligibility"]["gates"] = {name: True for name in MODULE.GATE_KEYS}
            promoted["eligibility"]["failed_gates"] = []
            promoted["eligibility"]["all_required_gates_passed"] = True
            promoted["eligibility"]["production_keyframe_eligible"] = True
            promoted["promotion"].update({"promotion_allowed": True, "promotion_ready": True, "promoted_artifact": True})
            Draft202012Validator(json.loads(SCHEMA.read_text())).validate(promoted)
            MODULE.validate_semantics(promoted)

    def test_canonical_integration_keeps_keyframe_and_repair_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, readiness = self.build(Path(temporary))
            canonical = json.loads((ROOT / MODULE.CANONICAL).read_text())
            binding = {"path": MODULE.CANDIDATE.as_posix(), "sha256": "a" * 64, "bytes": len(MODULE.encoded(candidate))}
            integrated = MODULE.integrate_canonical(canonical, binding, MODULE.READINESS.as_posix(), readiness)
            self.assertFalse(integrated["acceptance_gates"]["keyframe_manifest"])
            self.assertFalse(integrated["acceptance_gates"]["frame_repair_effectiveness"])
            self.assertTrue(integrated["keyframe_candidate_state"]["candidate_hash_bound"])
            self.assertEqual(integrated["normalized_blockers"][0]["blocker_id"], "KEYFRAME_CANDIDATE_NOT_PROMOTION_ELIGIBLE")
            reintegrated = MODULE.integrate_canonical(integrated, binding, MODULE.READINESS.as_posix(), readiness)
            self.assertEqual(reintegrated, integrated)

    def test_note_and_evidence_append_are_idempotent(self) -> None:
        once = MODULE.normalize_note(f"old; {MODULE.NOTE}; {MODULE.NOTE}")
        self.assertEqual(MODULE.normalize_note(once), once)
        self.assertEqual(once.count("Wave64 Row019 keyframe handoff:"), 1)
        self.assertEqual(MODULE.append_many("a; b", ["b", "c"]), "a; b; c")


if __name__ == "__main__":
    unittest.main()
