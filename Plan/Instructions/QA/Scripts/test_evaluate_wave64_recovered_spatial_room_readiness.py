#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_recovered_spatial_room_readiness.py"
SPEC = importlib.util.spec_from_file_location("row029_recovered_spatial_room", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredSpatialRoomReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = MODULE.build_evidence(ROOT, "2026-07-14T08:25:00-05:00")

    def test_all_recovered_wavs_are_hash_verified_and_decodable(self) -> None:
        comparison = self.evidence["strict_profile_comparison"]
        self.assertEqual(comparison["checked_wav_count"], 9)
        self.assertTrue(comparison["all_recovered_wavs_decode"])
        for audio_set in self.evidence["recovered_audio_sets"].values():
            for artifact in audio_set.values():
                self.assertEqual(artifact["duration_seconds"], 10.0)
                self.assertTrue(artifact["copied_not_generated"])

    def test_recovered_profiles_are_real_but_not_strict(self) -> None:
        comparison = self.evidence["strict_profile_comparison"]
        self.assertEqual(comparison["required_sample_rate_hz"], 16000)
        self.assertEqual(comparison["required_channels"], 2)
        self.assertEqual(comparison["passed_wav_count"], 0)
        self.assertEqual(comparison["failed_wav_count"], 9)
        self.assertFalse(comparison["all_recovered_wavs_match_strict_profile"])

    def test_mono_audio_does_not_create_pan_or_room_measurements(self) -> None:
        comparison = self.evidence["strict_profile_comparison"]
        self.assertFalse(comparison["spatial_pan_measurable"])
        self.assertFalse(comparison["room_rt60_or_reverb_tail_measurable_from_current_evidence"])
        self.assertFalse(
            self.evidence["mapping_decision"][
                "legacy_level_metrics_accepted_as_room_or_spatial_measurements"
            ]
        )

    def test_missing_contract_bindings_prevent_bundle_and_evaluator(self) -> None:
        decision = self.evidence["mapping_decision"]
        self.assertEqual(set(decision["missing_required_bindings"]), set(MODULE.MISSING_REQUIRED_BINDINGS))
        self.assertIn("spatial_dialogue", decision["unproven_audio_roles"])
        self.assertFalse(decision["eligible_for_strict_bundle"])
        self.assertFalse(decision["strict_producer_invoked"])
        self.assertFalse(decision["strict_evaluator_invoked"])

    def test_production_authority_and_external_actions_remain_absent(self) -> None:
        decision = self.evidence["mapping_decision"]
        self.assertEqual(set(decision["missing_production_proofs"]), set(MODULE.MISSING_PRODUCTION_PROOFS))
        for key in (
            "legacy_provisional_result_promoted",
            "production_playback_claimed",
            "production_runtime_claimed",
            "production_bundle_claimed",
            "aws_contacted",
            "ec2_started",
            "mask_or_wave71_touched",
            "jira_mutated",
        ):
            self.assertFalse(self.evidence["boundaries"][key], key)

    def test_row029_status_remains_blocked(self) -> None:
        self.assertEqual(
            self.evidence["status_decision"],
            "Blocked_Spatial_Room_Production_Proof_Missing",
        )
        self.assertEqual(
            self.evidence["result"],
            "blocked_recovered_audio_decodable_but_not_spatial_room_bundle_eligible",
        )


if __name__ == "__main__":
    unittest.main()
