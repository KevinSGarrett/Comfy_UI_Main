#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_hyperreal_audio_asset_catalog.py"
SPEC = importlib.util.spec_from_file_location("asset_catalog", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HyperrealAudioAssetCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        MODULE.main(ROOT)
        cls.catalog = json.loads((ROOT / MODULE.CATALOG).read_text(encoding="utf-8"))

    def test_official_assets_are_immutable_and_hash_bound(self) -> None:
        assets = self.catalog["official_asset_groups"]
        self.assertGreaterEqual(len(assets), 31)
        self.assertEqual(len({asset["asset_id"] for asset in assets}), len(assets))
        for asset in assets:
            self.assertEqual(len(asset["revision"]), 40)
            self.assertTrue(asset["key_files"])
            self.assertTrue(all(len(file["sha256"]) == 64 and file["bytes"] > 0 for file in asset["key_files"]))
            self.assertFalse(asset["production_ready"])

    def test_civitai_candidates_are_exact_and_not_model_authority(self) -> None:
        candidates = self.catalog["civitai_integration_candidates"]
        self.assertGreaterEqual(len(candidates), 13)
        discovered = {}
        discovery_root = ROOT / MODULE.DISCOVERY_ROOT
        for packet in discovery_root.glob("*.json"):
            payload = json.loads(packet.read_text(encoding="utf-8"))
            for model in payload.get("candidates", []):
                for file in model.get("files", []):
                    discovered[str(file["file_id"])] = {
                        "model_id": str(model["model_id"]),
                        "model_version_id": str(model["model_version_id"]),
                        "filename": file["filename"],
                        "sha256": file["sha256"],
                    }
        for candidate in candidates:
            self.assertTrue(candidate["model_id"].isdigit())
            self.assertTrue(candidate["model_version_id"].isdigit())
            self.assertTrue(candidate["file_id"].isdigit())
            self.assertEqual(len(candidate["sha256"]), 64)
            self.assertTrue(candidate["underlying_official_weights_required"])
            self.assertIn("not_model_authority", candidate["authority_level"])
            self.assertIn(candidate["file_id"], discovered)
            self.assertEqual(
                {key: candidate[key] for key in ("model_id", "model_version_id", "filename", "sha256")},
                discovered[candidate["file_id"]],
            )

    def test_required_capabilities_and_row_bindings_exist(self) -> None:
        capabilities = {asset["capability"] for asset in self.catalog["official_asset_groups"]}
        required = {
            "high_fidelity_custom_voice_and_cloning",
            "designed_synthetic_character_voice",
            "multilingual_zero_shot_and_instruction_speech",
            "video_conditioned_48khz_foley",
            "reference_conditioned_sfx_generation_and_editing",
            "high_fidelity_audio_conditioned_lip_synchronization",
            "semantic_audio_retrieval_and_similarity",
            "content_asr_and_word_timing_baseline",
            "speaker_turn_and_overlap_diarization",
        }
        self.assertTrue(required.issubset(capabilities))
        for row in (117, 118, 123, 124, 125, 128, 133, 135, 137, 141, 145, 147, 148):
            self.assertIn(f"TRK-W64-{row:03d}", self.catalog["row_asset_bindings"])

    def test_license_access_and_truth_boundaries_fail_closed(self) -> None:
        dispositions = {asset["disposition"] for asset in self.catalog["official_asset_groups"]}
        self.assertIn("blocked_until_license_terms_recorded", dispositions)
        self.assertIn("blocked_until_gated_access_and_license_are_recorded", dispositions)
        boundaries = self.catalog["boundaries"]
        self.assertFalse(boundaries["content_based_suppression"])
        self.assertFalse(boundaries["community_workflow_is_model_authority"])
        self.assertFalse(boundaries["download_is_runtime_ready"])
        self.assertFalse(boundaries["runtime_or_generation_executed"])
        self.assertFalse(boundaries["bulk_download_allowed"])

    def test_evidence_mirror_is_exact_and_civitai_api_is_recorded(self) -> None:
        source = (ROOT / MODULE.EVIDENCE).read_bytes()
        mirror = (ROOT / MODULE.EVIDENCE_MIRROR).read_bytes()
        self.assertEqual(source, mirror)
        evidence = json.loads(source)
        self.assertEqual(evidence["result"], "pass_provider_resolved_acquisition_catalog_second_pass")
        self.assertTrue(evidence["checks"]["civitai_api_used"])
        self.assertTrue(evidence["checks"]["exact_huggingface_commits_recorded"])
        self.assertTrue(evidence["checks"]["exact_civitai_model_version_file_and_sha256_recorded"])


if __name__ == "__main__":
    unittest.main()
