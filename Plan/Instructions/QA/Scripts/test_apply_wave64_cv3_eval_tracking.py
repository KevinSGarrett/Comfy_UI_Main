import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/apply_wave64_cv3_eval_tracking.py"
SPEC = importlib.util.spec_from_file_location("apply_wave64_cv3_eval_tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CV3TrackingUpdateTests(unittest.TestCase):
    def test_append_unique_is_idempotent(self):
        value = MODULE.append_unique("one; two", "two", "; ")
        self.assertEqual(value, "one; two")

    def test_update_csv_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._fixture(Path(temporary))
            before = path.read_bytes()
            changed = MODULE.update_csv(path, "Tracker_ID", "Evidence_Path", self._specs(), False)
            self.assertEqual(len(changed), 1)
            self.assertEqual(path.read_bytes(), before)

    def test_update_csv_applies_without_changing_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._fixture(Path(temporary))
            MODULE.update_csv(path, "Tracker_ID", "Evidence_Path", self._specs(), True)
            with path.open("r", encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["Status"], "Blocked_Test")
            self.assertIn(MODULE.EVIDENCE_REL, row["Evidence_Path"])
            self.assertIn(MODULE.NOTE, row["Notes"])

    def test_update_csv_rejects_status_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._fixture(Path(temporary), status="Completed")
            with self.assertRaisesRegex(ValueError, "status drift"):
                MODULE.update_csv(path, "Tracker_ID", "Evidence_Path", self._specs(), False)

    @staticmethod
    def _specs():
        return {"test": {"Tracker_ID": "TRK-W64-999", "status": "Blocked_Test"}}

    @staticmethod
    def _fixture(root: Path, status: str = "Blocked_Test") -> Path:
        path = root / "tracker.csv"
        fields = ["Tracker_ID", "Status", "Status_Decision", "Evidence_Path", "Coverage_Audit_Status", "Notes"]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow(
                {
                    "Tracker_ID": "TRK-W64-999",
                    "Status": status,
                    "Status_Decision": status,
                    "Evidence_Path": "prior.json",
                    "Coverage_Audit_Status": "prior",
                    "Notes": "prior note",
                }
            )
        return path


if __name__ == "__main__":
    unittest.main()
