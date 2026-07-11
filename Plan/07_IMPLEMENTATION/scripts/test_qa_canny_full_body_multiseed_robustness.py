#!/usr/bin/env python3
"""Unit tests for Canny full-body multiseed QA helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qa_canny_full_body_multiseed_robustness import (  # noqa: E402
    VISUAL_CHECKS,
    dwpose_models_trusted,
    normalize_profile_for_invariance,
    points_are_in_frame,
    prompt_binding_checks,
    qa_exit_code,
)


class QACannyFullBodyTests(unittest.TestCase):
    def test_normalize_profile_removes_seed_identity_fields(self) -> None:
        profile = {
            "profile_id": "canny_full_body_standing_seed711570301",
            "request_patch_values": {
                "seed": 711570301,
                "save_prefix": "x",
                "positive_prompt": "positive",
            },
            "expected_outputs": {"output_prefix": "x", "artifact_type": "image"},
        }
        normalized = normalize_profile_for_invariance(profile)
        self.assertNotIn("seed", normalized["request_patch_values"])
        self.assertNotIn("save_prefix", normalized["request_patch_values"])
        self.assertNotIn("output_prefix", normalized["expected_outputs"])

    def test_prompt_binding_checks_accept_exact_contract(self) -> None:
        profile = {
            "request_patch_values": {
                "positive_prompt": "positive",
                "negative_prompt": "negative",
                "seed": 711570301,
                "save_prefix": "canny_full_body_standing_711570301",
                "model_asset": "realvisxlV50_v50Bakedvae.safetensors",
                "controlnet_asset": "controlnet-canny-sdxl-1.0-small.safetensors",
                "control_image": "controlnet_canny_full_body_standing_w70_v1.png",
                "controlnet_settings": {
                    "strength": 0.42,
                    "start_percent": 0.0,
                    "end_percent": 0.6,
                },
                "sampler_settings": {
                    "steps": 24,
                    "cfg": 5.5,
                    "sampler_name": "dpmpp_2m_sde",
                    "scheduler": "karras",
                    "denoise": 1,
                },
                "latent_resolution": {"width": 768, "height": 1024},
            }
        }
        graph = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "realvisxlV50_v50Bakedvae.safetensors"},
            },
            "2": {
                "class_type": "ControlNetLoader",
                "inputs": {"control_net_name": "controlnet-canny-sdxl-1.0-small.safetensors"},
            },
            "3": {
                "class_type": "LoadImage",
                "inputs": {"image": "controlnet_canny_full_body_standing_w70_v1.png"},
            },
            "4": {
                "class_type": "ControlNetApplyAdvanced",
                "inputs": {"strength": 0.42, "start_percent": 0.0, "end_percent": 0.6},
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 711570301,
                    "steps": 24,
                    "cfg": 5.5,
                    "sampler_name": "dpmpp_2m_sde",
                    "scheduler": "karras",
                    "denoise": 1,
                },
            },
            "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1024}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "positive"}},
            "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "negative"}},
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "canny_full_body_standing_711570301"},
            },
        }
        self.assertTrue(all(prompt_binding_checks(graph, profile, 711570301).values()))

    def test_points_are_in_frame_checks_bounds(self) -> None:
        valid_points = {
            0: (0.5, 0.1),
            4: (0.3, 0.4),
            7: (0.7, 0.4),
            10: (0.35, 0.9),
            13: (0.65, 0.9),
        }
        invalid_points = {**valid_points, 13: (1.2, 0.9)}
        self.assertTrue(points_are_in_frame(valid_points))
        self.assertFalse(points_are_in_frame(invalid_points))

    def test_visual_contract_has_expected_checks(self) -> None:
        self.assertEqual(
            VISUAL_CHECKS,
            (
                "exactly_one_adult",
                "full_body_in_frame",
                "both_hands_visible",
                "both_feet_visible",
                "coherent_limbs",
                "no_canny_edge_leakage_harsh_outlines_or_border_seam",
                "natural_skin_clothing_backdrop_coherence",
            ),
        )

    def test_qa_exit_code_handles_missing_visual_and_technical_only(self) -> None:
        self.assertEqual(qa_exit_code(True, True, False, True), 2)
        self.assertEqual(qa_exit_code(True, True, True, True), 0)
        self.assertEqual(qa_exit_code(True, False, None, True), 2)
        self.assertEqual(
            qa_exit_code(
                True,
                False,
                None,
                True,
                technical_only_allowed=True,
            ),
            0,
        )

    def test_dwpose_models_require_present_exact_hashes(self) -> None:
        trusted = [
            {"exists": True, "sha256_matches_expected": True},
            {"exists": True, "sha256_matches_expected": True},
        ]
        missing = [
            {"exists": True, "sha256_matches_expected": True},
            {"exists": False, "sha256_matches_expected": False},
        ]
        mismatched = [
            {"exists": True, "sha256_matches_expected": True},
            {"exists": True, "sha256_matches_expected": False},
        ]
        self.assertTrue(dwpose_models_trusted(trusted))
        self.assertFalse(dwpose_models_trusted(missing))
        self.assertFalse(dwpose_models_trusted(mismatched))


if __name__ == "__main__":
    unittest.main()
