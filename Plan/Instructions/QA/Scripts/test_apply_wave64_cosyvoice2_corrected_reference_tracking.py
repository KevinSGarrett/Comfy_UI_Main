#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/apply_wave64_cosyvoice2_corrected_reference_tracking.py"
)
SPEC = importlib.util.spec_from_file_location("track_corrected_cosyvoice2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def report() -> dict:
    return {
        "item_id": "ITEM-W64-027",
        "tracker_id": "TRK-W64-027",
        "status": "Blocked_Voice_Dialogue_Production_Proof_Missing",
        "row_complete": False,
        "implementation": {},
        "validation": {},
        "acceptance_gates": {},
        "blockers": [{"classification": MODULE.BLOCKER, "reason": "old"}],
        "evidence": [],
        "runtime": {},
    }


class CorrectedReferenceTrackingTests(unittest.TestCase):
    def test_records_narrow_passes_without_row_promotion(self):
        payload = MODULE.update_report_payload(report())
        gates = payload["acceptance_gates"]
        self.assertTrue(gates["cosyvoice2_corrected_candidate_exact_content_pass"])
        self.assertTrue(gates["cosyvoice2_corrected_candidate_reference_speaker_score_pass"])
        self.assertFalse(gates["cosyvoice2_corrected_candidate_dialogue_timing_pass"])
        self.assertFalse(gates["production_review_authority_pass"])
        self.assertFalse(payload["row_complete"])

    def test_update_is_idempotent(self):
        once = MODULE.update_report_payload(report())
        twice = MODULE.update_report_payload(once)
        linked = [entry for entry in twice["evidence"] if entry.get("path") == MODULE.EVIDENCE_REL]
        self.assertEqual(len(linked), 1)
        self.assertEqual(twice["runtime"]["cosyvoice2_zero_shot_generation_count"], 2)


if __name__ == "__main__":
    unittest.main()
