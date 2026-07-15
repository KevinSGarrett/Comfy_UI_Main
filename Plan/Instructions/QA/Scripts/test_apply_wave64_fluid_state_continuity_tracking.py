import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/apply_wave64_fluid_state_continuity_tracking.py"
SPEC = importlib.util.spec_from_file_location("apply_wave64_fluid_state_tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ApplyWave64FluidStateContinuityTrackingTests(unittest.TestCase):
    def _fluid(self):
        return {
            "system_id": "fluid_body_state_continuity",
            "blockers": ["model_or_runtime_capability_proof_missing"],
            "runtime_promotion_state": "blocked_missing_direct_runtime_evidence",
        }

    def test_fluid_entry_replaces_missing_proof_with_exact_failure(self):
        updated = MODULE.updated_fluid_entry(self._fluid())
        self.assertEqual(updated["runtime_promotion_state"], "bounded_direct_runtime_review_fail_shot_continuity")
        self.assertNotIn("model_or_runtime_capability_proof_missing", updated["blockers"])
        self.assertEqual(updated["direct_proof_scope"]["local_generation_count"], 4)
        self.assertEqual(updated["direct_proof_scope"]["candidate_retry_count"], 0)

    def test_system_update_requires_exactly_one_fluid_entry(self):
        with self.assertRaisesRegex(ValueError, "expected one"):
            MODULE.update_systems([])
        with self.assertRaisesRegex(ValueError, "expected one"):
            MODULE.update_systems([self._fluid(), self._fluid()])

    def test_registry_summary_preserves_only_micro_motion_as_pass(self):
        payload = {"advanced_systems": [self._fluid()]}
        updated = MODULE.update_registry(payload)
        self.assertEqual(updated["proof_summary"]["bounded_direct_runtime_proof_pass"], 1)
        self.assertEqual(updated["proof_summary"]["direct_runtime_review_fail"], 1)
        self.assertEqual(updated["proof_summary"]["direct_runtime_proof_missing"], 5)
        self.assertEqual(updated["status"], MODULE.STATUS)

    def test_item_remains_blocked_and_incomplete(self):
        payload = {"evidence": [], "remaining_blockers": {}, "row_complete": False}
        updated = MODULE.update_item(payload)
        self.assertFalse(updated["row_complete"])
        self.assertEqual(updated["status"], MODULE.STATUS)
        self.assertIn(MODULE.EVIDENCE_REL, updated["evidence"])

    def test_tracker_update_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tracker.csv"
            fieldnames = ["Tracker_ID", "Status", "Status_Decision", "Evidence_Path", "Notes"]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({"Tracker_ID": "TRK-W64-056", "Status": "old", "Notes": "existing"})
            MODULE.update_tracker(path)
            MODULE.update_tracker(path)
            with path.open("r", encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["Status"], MODULE.STATUS)
            self.assertEqual(row["Notes"].count(MODULE.NOTE_MARKER), 1)

    def test_hydration_prepend_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "hydration.md"
            path.write_text("old\n", encoding="utf-8")
            MODULE.prepend_hydration(path)
            MODULE.prepend_hydration(path)
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(MODULE.HYDRATION_MARKER), 1)
            self.assertTrue(text.endswith("old\n"))


if __name__ == "__main__":
    unittest.main()
