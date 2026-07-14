#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / (
    "Plan/07_IMPLEMENTATION/scripts/"
    "evaluate_wave64_recovered_strict_audio_review_readiness.py"
)
SPEC = importlib.util.spec_from_file_location("row031_recovered_strict_audio", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredStrictAudioReviewReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = MODULE.build_evidence(ROOT, "2026-07-14T08:50:00-05:00")

    def test_two_recovered_mix_candidates_are_hash_verified_and_decodable(self) -> None:
        candidates = self.evidence["recovered_mix_candidates"]
        self.assertEqual(len(candidates), 2)
        for candidate in candidates.values():
            self.assertTrue(candidate["decode_probe_succeeded"])
            self.assertEqual(candidate["duration_seconds"], 10.0)
            self.assertTrue(candidate["copied_not_generated"])
            self.assertTrue(candidate["eligible_as_mix_wav_binding"])

    def test_mix_bytes_do_not_become_review_proofs(self) -> None:
        for candidate in self.evidence["recovered_mix_candidates"].values():
            self.assertFalse(candidate["eligible_as_prompt_alignment_proof"])
            self.assertFalse(candidate["eligible_as_playback_review_proof"])

    def test_required_bindings_prevent_request_and_evaluator(self) -> None:
        decision = self.evidence["mapping_decision"]
        self.assertEqual(set(decision["missing_required_bindings"]), set(MODULE.MISSING_REQUIRED_BINDINGS))
        self.assertFalse(decision["eligible_for_strict_request"])
        self.assertFalse(decision["strict_producer_invoked"])
        self.assertFalse(decision["strict_evaluator_invoked"])

    def test_production_authority_is_empty_and_legacy_qa_is_rejected(self) -> None:
        authority = self.evidence["authority_state"]
        self.assertEqual(authority["approved_non_synthetic_prompt_alignment_producer_count"], 0)
        self.assertEqual(authority["approved_non_synthetic_playback_producer_count"], 0)
        self.assertEqual(authority["approved_production_review_authority_count"], 0)
        self.assertEqual(authority["approved_production_review_bundle_count"], 0)
        self.assertFalse(authority["legacy_qa_labels_accepted_as_prompt_alignment"])
        self.assertFalse(authority["legacy_qa_labels_accepted_as_playback_review"])

    def test_supporting_rows_are_not_promoted_to_row031_authority(self) -> None:
        supporting = self.evidence["supporting_recovered_evidence"]
        self.assertEqual(set(supporting), set(MODULE.SUPPORTING_EVIDENCE))
        self.assertTrue(all(not item["accepted_as_row031_authority"] for item in supporting.values()))

    def test_status_and_external_boundaries_remain_fail_closed(self) -> None:
        self.assertEqual(
            self.evidence["status_decision"],
            "Blocked_Strict_Audio_Production_Review_Proof_Missing",
        )
        self.assertEqual(
            self.evidence["result"],
            "blocked_recovered_mixes_decodable_but_not_strict_audio_review_request_eligible",
        )
        for key in (
            "generation_executed",
            "audio_modified_or_remixed",
            "identity_or_review_proof_invented",
            "legacy_provisional_result_promoted",
            "aws_contacted",
            "ec2_started",
            "mask_or_wave71_touched",
            "jira_mutated",
        ):
            self.assertFalse(self.evidence["boundaries"][key], key)


if __name__ == "__main__":
    unittest.main()
