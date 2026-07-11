#!/usr/bin/env python3
"""Unit tests for bounded Base-remediation OpenPose QA helpers."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qa_base_two_character_openpose_contact_pair import (
    VISUAL_CHECKS,
    nodes_of_type,
    normalize_profile_for_invariance,
    prompt_binding_checks,
    qa_exit_code,
)


class QABaseOpenPoseContactPairTests(unittest.TestCase):
    def test_normalize_profile_removes_only_seed_identity_fields(self) -> None:
        profile = {
            "profile_id": "example_seed_1",
            "request_patch_values": {
                "seed": 1,
                "save_prefix": "a",
                "positive_prompt": "positive",
            },
            "expected_outputs": {"output_prefix": "a", "artifact_type": "image"},
        }
        normalized = normalize_profile_for_invariance(profile)
        self.assertEqual(normalized["request_patch_values"]["positive_prompt"], "positive")
        self.assertNotIn("seed", normalized["request_patch_values"])
        self.assertNotIn("output_prefix", normalized["expected_outputs"])

    def test_nodes_of_type_filters_graph(self) -> None:
        graph = {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "SaveImage", "inputs": {}},
        }
        self.assertEqual(len(nodes_of_type(graph, "LoadImage")), 1)
        self.assertEqual(len(nodes_of_type(graph, "KSampler")), 0)

    def test_prompt_binding_checks_accept_exact_contract(self) -> None:
        profile = {
            "request_patch_values": {
                "positive_prompt": "positive",
                "negative_prompt": "negative",
                "seed": 7152026253,
                "save_prefix": "out",
                "controlnet_settings": {"strength": 0.75, "start_percent": 0, "end_percent": 1},
                "latent_resolution": {"width": 1024, "height": 1024},
                "sampler_settings": {
                    "steps": 30,
                    "cfg": 5.4,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                },
            }
        }
        graph = {
            "1": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "OpenPoseXL2.safetensors"}},
            "2": {"class_type": "LoadImage", "inputs": {"image": "controlnet_openpose_two_character_contact_w70_v1.png"}},
            "3": {"class_type": "ControlNetApplyAdvanced", "inputs": {"strength": 0.75, "start_percent": 0, "end_percent": 1}},
            "4": {"class_type": "KSampler", "inputs": {"seed": 7152026253, "steps": 30, "cfg": 5.4, "sampler_name": "dpmpp_2m", "scheduler": "karras"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "positive"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "negative"}},
            "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "out"}},
        }
        self.assertTrue(all(prompt_binding_checks(graph, profile, 7152026253).values()))

    def test_visual_contract_has_expected_six_checks(self) -> None:
        self.assertEqual(len(VISUAL_CHECKS), 6)

    def test_exit_code_allows_technical_pending_visual_stage(self) -> None:
        self.assertEqual(qa_exit_code(True, False, None, True), 0)

    def test_exit_code_rejects_visual_failure(self) -> None:
        self.assertEqual(qa_exit_code(True, True, False, True), 2)

    def test_exit_code_rejects_invalid_visual_contract(self) -> None:
        self.assertEqual(qa_exit_code(True, True, True, False), 2)


if __name__ == "__main__":
    unittest.main()
