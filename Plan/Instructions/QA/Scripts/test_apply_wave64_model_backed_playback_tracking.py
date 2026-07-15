from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/apply_wave64_model_backed_playback_tracking.py"
SPEC = importlib.util.spec_from_file_location("apply_wave64_model_backed_playback_tracking", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ModelBackedPlaybackTrackingTests(unittest.TestCase):
    def _payload(self, row: str) -> dict:
        spec = MODULE.ROW_SPECS[row]
        return {
            "item_id": spec["item_id"],
            "tracker_id": spec["tracker_id"],
            "status": spec["status"],
            "row_complete": False,
            "implementation": {},
            "validation": {},
            "acceptance_gates": {},
            "blockers": [],
            "evidence": [],
            "runtime": {},
        }

    def test_evidence_mirrors_are_exact_and_fail_closed(self) -> None:
        result = MODULE.verify_evidence()
        self.assertEqual(result["sha256"], MODULE.EVIDENCE_SHA256)

    def test_canonical_json_hash_is_line_ending_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            lf.write_bytes(b'{\n  "status": "BLOCKED"\n}\n')
            crlf.write_bytes(b'{\r\n  "status": "BLOCKED"\r\n}\r\n')
            self.assertEqual(
                MODULE.canonical_json_sha256(lf),
                MODULE.canonical_json_sha256(crlf),
            )

    def test_each_row_remains_blocked_and_incomplete(self) -> None:
        for row in MODULE.ROW_SPECS:
            with self.subTest(row=row):
                updated = MODULE.update_report_payload(self._payload(row))
                self.assertEqual(updated["status"], MODULE.ROW_SPECS[row]["status"])
                self.assertFalse(updated["row_complete"])
                self.assertFalse(updated["acceptance_gates"]["candidate_model_backed_playback_proof_present"])
                self.assertFalse(updated["acceptance_gates"]["replacement_candidate_intelligibility_verified"])
                self.assertFalse(updated["acceptance_gates"]["production_review_authority_pass"])

    def test_existing_playback_blocker_is_replaced_not_duplicated(self) -> None:
        payload = self._payload("027")
        payload["blockers"] = [
            {
                "classification": "Blocked_Voice_Playback_Quality_Edge_Review_Missing",
                "scope": "old",
                "reason": "old",
            }
        ]
        updated = MODULE.update_report_payload(payload)
        matching = [
            blocker
            for blocker in updated["blockers"]
            if blocker["classification"] == MODULE.BLOCKER_CLASSIFICATION
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["scope"], "dialogue_candidates")

    def test_reapplication_is_idempotent(self) -> None:
        payload = MODULE.update_report_payload(self._payload("031"))
        updated = MODULE.update_report_payload(payload)
        evidence = [entry for entry in updated["evidence"] if entry["path"] == MODULE.EVIDENCE_REL]
        blockers = [
            entry for entry in updated["blockers"] if entry["classification"] == MODULE.BLOCKER_CLASSIFICATION
        ]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(len(blockers), 1)


if __name__ == "__main__":
    unittest.main()
