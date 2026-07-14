from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_video_keyframe_context.py"
SPEC = importlib.util.spec_from_file_location("video_keyframe_context", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class VideoKeyframeContextTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        qa = json.loads((ROOT / MODULE.QA).read_text(encoding="utf-8-sig"))
        candidate = json.loads((ROOT / MODULE.CANDIDATE).read_text(encoding="utf-8-sig"))
        image_source = ROOT / qa["outputs"]["generated_image"]["path"]
        keypoints_source = ROOT / qa["outputs"]["generated_keypoints"]["path"]
        shutil.copyfile(image_source, root / "source.png")
        shutil.copyfile(keypoints_source, root / "keypoints.json")
        qa["outputs"]["generated_image"]["path"] = "source.png"
        qa["outputs"]["generated_keypoints"]["path"] = "keypoints.json"
        candidate["candidate"]["keyframe_artifact"]["path"] = "source.png"
        qa_path, candidate_path = root / "qa.json", root / "candidate.json"
        write(qa_path, qa)
        write(candidate_path, candidate)
        return qa_path, candidate_path

    def build(self, root: Path, qa_path: Path | None = None, candidate_path: Path | None = None):
        if qa_path is None or candidate_path is None:
            qa_path, candidate_path = self.fixture(root)
        return MODULE.build(root, "2026-07-14T14:10:00-05:00", qa_path, candidate_path, {name: ROOT / path for name, path in MODULE.SCHEMAS.items()})

    def test_context_and_standard_components_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payloads = self.build(Path(temporary))
            for name, payload in payloads.items():
                schema_name = name if name != "context" else "context"
                schema = json.loads((ROOT / MODULE.SCHEMAS[schema_name]).read_text())
                Draft202012Validator(schema).validate(payload)

    def test_context_advances_only_three_structural_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.build(Path(temporary))["context"]
            self.assertEqual(context["gates"], {
                "frame_contract_exported": True,
                "environment_profile_exists": True,
                "character_profile_exists": True,
                "identity_camera_environment_continuity_passed": False,
            })
            self.assertTrue(context["boundaries"]["single_image_anchor_only"])
            self.assertFalse(context["boundaries"]["skeleton_geometry_authority_claimed"])
            self.assertFalse(context["boundaries"]["promotion_claimed"])

    def test_component_bindings_match_serialized_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = self.build(root)
            for name, key in (("body", "body_visibility_profile"), ("frame", "frame_composition_contract"), ("frame_evidence", "frame_composition_evidence")):
                binding = payloads["context"]["component_artifacts"][key]
                self.assertEqual(binding["sha256"], __import__("hashlib").sha256(MODULE.encoded(payloads[name])).hexdigest())

    def test_source_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qa, candidate = self.fixture(root)
            (root / "source.png").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "source image binding failed"):
                self.build(root, qa, candidate)

    def test_candidate_source_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qa, candidate = self.fixture(root)
            value = json.loads(candidate.read_text())
            value["candidate"]["keyframe_artifact"]["sha256"] = "0" * 64
            write(candidate, value)
            with self.assertRaisesRegex(ValueError, "candidate source binding mismatch"):
                self.build(root, qa, candidate)

    def test_promoted_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qa, candidate = self.fixture(root)
            value = json.loads(candidate.read_text())
            value["candidate"]["candidate_only"] = False
            write(candidate, value)
            with self.assertRaisesRegex(ValueError, "not candidate-only"):
                self.build(root, qa, candidate)

    def test_skeleton_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qa, candidate = self.fixture(root)
            (root / "keypoints.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "person count invalid"):
                self.build(root, qa, candidate)


if __name__ == "__main__":
    unittest.main()
