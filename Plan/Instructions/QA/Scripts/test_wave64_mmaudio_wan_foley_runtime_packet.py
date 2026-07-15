from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_PATH = ROOT / "Workflows/audio/mmaudio_wan_foley/workflow.api.json"
REQUIREMENTS_PATH = ROOT / "Workflows/audio/mmaudio_wan_foley/runtime_requirements.json"
PATCH_PATH = ROOT / "Workflows/audio/mmaudio_wan_foley/patches/huggingface_hub_1_22_bigvgan.patch"
ARTIFACT_ROOT = (
    ROOT
    / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
    / "w64_mmaudio_wan_foley_20260714T211502-0500"
)
MANIFEST_PATH = ARTIFACT_ROOT / "runtime_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MMAudioWanFoleyRuntimePacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = read_json(WORKFLOW_PATH)
        self.requirements = read_json(REQUIREMENTS_PATH)
        self.manifest = read_json(MANIFEST_PATH)

    def test_minimal_workflow_has_expected_nodes_and_links(self) -> None:
        self.assertEqual(len(self.workflow), 6)
        self.assertEqual(
            {node["class_type"] for node in self.workflow.values()},
            {
                "LoadVideo",
                "GetVideoComponents",
                "MMAudioModelLoader",
                "MMAudioFeatureUtilsLoader",
                "MMAudioSampler",
                "SaveAudio",
            },
        )
        self.assertEqual(self.workflow["5"]["inputs"]["images"], ["2", 0])
        self.assertEqual(self.workflow["6"]["inputs"]["audio"], ["5", 0])

    def test_official_model_substitution_is_explicit(self) -> None:
        substitution = self.requirements["model_substitution"]
        self.assertFalse(substitution["silent_substitution"])
        self.assertFalse(substitution["content_filter_added"])
        self.assertNotEqual(substitution["template_filename"], substitution["runtime_filename"])
        self.assertEqual(
            self.workflow["3"]["inputs"]["mmaudio_model"],
            substitution["runtime_filename"],
        )

    def test_runtime_lineage_hashes_match(self) -> None:
        workflow = self.manifest["workflow"]
        self.assertEqual(sha256_file(WORKFLOW_PATH), workflow["sha256"])
        self.assertEqual(sha256_file(REQUIREMENTS_PATH), workflow["runtime_requirements_sha256"])
        self.assertEqual(sha256_file(PATCH_PATH), self.manifest["compatibility_patch"]["sha256"])
        for output in self.manifest["outputs"].values():
            path = ROOT / output["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, output["bytes"])
            self.assertEqual(sha256_file(path), output["sha256"])

    def test_success_history_is_bound_and_completed(self) -> None:
        success = self.manifest["attempts"][1]
        history_path = ROOT / success["history_path"]
        self.assertEqual(sha256_file(history_path), success["history_sha256"])
        history = read_json(history_path)
        prompt_id = success["prompt_id"]
        self.assertTrue(history[prompt_id]["status"]["completed"])
        self.assertEqual(history[prompt_id]["status"]["status_str"], "success")
        self.assertEqual(success["node_errors"], 0)

    def test_fail_closed_authority_boundaries_remain(self) -> None:
        acceptance = self.manifest["acceptance"]
        self.assertTrue(acceptance["genuine_video_conditioned_audio_runtime_pass"])
        self.assertFalse(acceptance["independent_perceptual_playback_review_present"])
        self.assertFalse(acceptance["contact_owner_alignment_present"])
        self.assertFalse(acceptance["production_audio_certification_allowed"])
        self.assertFalse(self.manifest["row_complete"])
        self.assertFalse(self.requirements["boundaries"]["production_audio_certification_claimed"])


if __name__ == "__main__":
    unittest.main()
