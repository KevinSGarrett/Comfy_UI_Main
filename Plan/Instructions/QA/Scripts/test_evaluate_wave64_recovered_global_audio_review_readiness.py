#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / (
    "Plan/07_IMPLEMENTATION/scripts/"
    "evaluate_wave64_recovered_global_audio_review_readiness.py"
)
SPEC = importlib.util.spec_from_file_location("row032_recovered_global_audio", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredGlobalAudioReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = MODULE.build_evidence(ROOT, "2026-07-14T10:51:33-05:00")

    def test_two_recovered_mix_candidates_are_hash_verified_and_decodable(self) -> None:
        candidates = self.evidence["recovered_mix_candidates"]
        self.assertEqual(set(candidates), set(MODULE.EXPECTED_CANDIDATE_CLASSES))
        for candidate in candidates.values():
            self.assertTrue(candidate["decode_probe_succeeded"])
            self.assertEqual(candidate["duration_seconds"], 10.0)
            self.assertTrue(candidate["copied_not_generated"])
            self.assertTrue(candidate["eligible_as_row032_mix_wav_binding_candidate"])

    def test_mix_candidates_do_not_become_strict_lineage_or_review_proof(self) -> None:
        for candidate in self.evidence["recovered_mix_candidates"].values():
            self.assertFalse(candidate["eligible_as_row031_strict_report"])
            self.assertFalse(candidate["eligible_as_wave30_lineage"])
            self.assertFalse(candidate["eligible_as_global_playback_authority"])

    def test_required_bindings_and_semantics_prevent_request(self) -> None:
        decision = self.evidence["mapping_decision"]
        self.assertEqual(
            set(decision["missing_required_bindings"]),
            set(MODULE.MISSING_REQUIRED_BINDINGS),
        )
        self.assertEqual(
            set(decision["unresolved_comparison_semantics"]),
            set(MODULE.UNRESOLVED_COMPARISON_SEMANTICS),
        )
        self.assertFalse(decision["baseline_candidate_pair_selected"])
        self.assertFalse(decision["eligible_for_strict_request"])
        self.assertFalse(decision["strict_producer_invoked"])
        self.assertFalse(decision["strict_evaluator_invoked"])

    def test_production_authority_remains_empty(self) -> None:
        authority = self.evidence["authority_state"]
        self.assertEqual(authority["approved_production_baseline_count"], 0)
        self.assertEqual(authority["approved_production_bundle_count"], 0)
        self.assertFalse(authority["diagnostic_mix_promoted_to_baseline"])
        self.assertFalse(authority["provisional_mix_promoted_to_candidate"])
        self.assertFalse(authority["recovered_wav_pair_claimed_as_comparable_change_pair"])

    def test_project_path_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            outside = Path(directory) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "path escapes project root"):
                MODULE.project_path(root, outside)

    def test_status_and_external_boundaries_remain_fail_closed(self) -> None:
        self.assertEqual(
            self.evidence["status_decision"],
            "Blocked_Global_Audio_Production_Review_Proof_Missing",
        )
        self.assertEqual(
            self.evidence["result"],
            "blocked_recovered_mixes_not_global_audio_review_request_eligible",
        )
        for key in (
            "generation_executed",
            "audio_modified_or_remixed",
            "comparison_identity_invented",
            "legacy_provisional_result_promoted",
            "aws_contacted",
            "ec2_started",
            "mask_or_wave71_touched",
            "jira_mutated",
        ):
            self.assertFalse(self.evidence["boundaries"][key], key)


if __name__ == "__main__":
    unittest.main()
