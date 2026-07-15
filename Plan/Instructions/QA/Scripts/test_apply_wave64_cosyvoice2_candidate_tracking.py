#!/usr/bin/env python3
"""Tests for rejected CosyVoice2 candidate ledger tracking."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/apply_wave64_cosyvoice2_candidate_tracking.py"
)
SPEC = importlib.util.spec_from_file_location("track_cosyvoice2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def report_payload() -> dict:
    return {
        "item_id": "ITEM-W64-027",
        "tracker_id": "TRK-W64-027",
        "status": "Blocked_Voice_Dialogue_Production_Proof_Missing",
        "row_complete": False,
        "implementation": {},
        "validation": {},
        "acceptance_gates": {"candidate_reference_speaker_identity_verified": False},
        "blockers": [
            {"classification": "Blocked_Voice_Speaker_Reference_Missing", "reason": "old"},
            {"classification": "Blocked_Voice_Production_Proof_Authority_Missing"},
        ],
        "evidence": [],
        "runtime": {},
    }


class ApplyCosyVoice2TrackingTests(unittest.TestCase):
    def test_replaces_stale_reference_blocker_without_completing_row(self):
        payload = MODULE.update_report_payload(report_payload())
        classifications = [entry.get("classification") for entry in payload["blockers"]]
        self.assertNotIn(MODULE.SUPERSEDED_BLOCKER, classifications)
        self.assertIn(MODULE.CURRENT_BLOCKER, classifications)
        self.assertFalse(payload["row_complete"])
        self.assertEqual(payload["status"], "Blocked_Voice_Dialogue_Production_Proof_Missing")

    def test_records_score_pass_only_for_rejected_candidate(self):
        payload = MODULE.update_report_payload(report_payload())
        gates = payload["acceptance_gates"]
        self.assertTrue(gates["cosyvoice2_rejected_candidate_reference_speaker_score_pass"])
        self.assertTrue(gates["cosyvoice2_pytorch_model_stack_cuda_executed"])
        self.assertFalse(gates["cosyvoice2_onnx_frontend_cuda_executed"])
        self.assertIsNone(
            gates["cosyvoice2_rejected_candidate_dnsmos_quality_certification_pass"]
        )
        self.assertEqual(
            gates["cosyvoice2_candidate_intensity_taxonomy_status"],
            "unmeasured_no_calibrated_intensity_evaluator",
        )
        self.assertFalse(gates["candidate_reference_speaker_identity_verified"])
        self.assertFalse(gates["cosyvoice2_candidate_intelligibility_pass"])
        self.assertFalse(gates["cosyvoice2_candidate_dialogue_timing_pass"])
        self.assertFalse(gates["production_review_authority_pass"])

    def test_update_is_idempotent(self):
        once = MODULE.update_report_payload(report_payload())
        twice = MODULE.update_report_payload(once)
        current = [
            entry for entry in twice["blockers"] if entry.get("classification") == MODULE.CURRENT_BLOCKER
        ]
        evidence = [entry for entry in twice["evidence"] if entry.get("path") == MODULE.EVIDENCE_REL]
        self.assertEqual(len(current), 1)
        self.assertEqual(len(evidence), 1)


if __name__ == "__main__":
    unittest.main()
