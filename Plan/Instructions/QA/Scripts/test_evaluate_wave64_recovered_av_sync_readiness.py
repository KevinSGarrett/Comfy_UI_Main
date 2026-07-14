#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_recovered_av_sync_readiness.py"
SPEC = importlib.util.spec_from_file_location("row030_recovered_av_sync", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredAvSyncReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = MODULE.build_evidence(ROOT, "2026-07-14T07:55:00-05:00")

    def test_recovered_mux_and_audio_hashes_decode(self) -> None:
        artifacts = self.evidence["recovered_artifacts"]
        self.assertTrue(artifacts["final_mux_candidate"]["decode_probe_succeeded"])
        self.assertEqual(artifacts["final_mux_candidate"]["duration_seconds"], 10.0)
        self.assertEqual(artifacts["final_audio_mix"]["duration_seconds"], 10.0)

    def test_observed_profile_is_real_but_not_strict(self) -> None:
        comparison = self.evidence["strict_profile_comparison"]
        self.assertEqual(comparison["observed_profile"]["video_codec"], "h264")
        self.assertEqual(comparison["observed_profile"]["audio_codec"], "aac")
        self.assertEqual(comparison["observed_profile"]["audio_channels"], 1)
        self.assertFalse(comparison["strict_mux_profile_pass"])
        self.assertEqual(comparison["passed_check_count"], 1)
        self.assertEqual(comparison["failed_check_count"], 4)

    def test_legacy_pass_is_not_promoted(self) -> None:
        report = self.evidence["recovered_artifacts"]["legacy_av_report"]
        self.assertEqual(report["reported_overall_status"], "pass")
        self.assertFalse(report["accepted_as_current_strict_proof"])
        self.assertFalse(self.evidence["boundaries"]["legacy_provisional_pass_promoted"])

    def test_missing_contract_fields_prevent_packet_and_evaluator(self) -> None:
        decision = self.evidence["mapping_decision"]
        self.assertEqual(set(decision["missing_required_fields"]), set(MODULE.MISSING_REQUIRED_FIELDS))
        self.assertFalse(decision["eligible_for_strict_packet"])
        self.assertFalse(decision["strict_evaluator_invoked"])
        self.assertIsNone(decision["legacy_report_current_proof_role"])

    def test_production_authority_remains_absent(self) -> None:
        decision = self.evidence["mapping_decision"]
        self.assertEqual(set(decision["missing_production_proofs"]), set(MODULE.MISSING_PRODUCTION_PROOFS))
        for key in (
            "production_playback_claimed",
            "production_runtime_claimed",
            "production_bundle_claimed",
            "aws_contacted",
            "ec2_started",
            "mask_or_wave71_touched",
            "jira_mutated",
        ):
            self.assertFalse(self.evidence["boundaries"][key], key)

    def test_row030_status_remains_blocked(self) -> None:
        self.assertEqual(
            self.evidence["status_decision"],
            "Blocked_AV_Sync_Production_Proof_Missing",
        )
        self.assertEqual(
            self.evidence["result"],
            "blocked_recovered_mux_decodable_but_not_strict_packet_eligible",
        )


if __name__ == "__main__":
    unittest.main()
