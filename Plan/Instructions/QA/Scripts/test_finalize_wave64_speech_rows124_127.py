from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "finalize_wave64_speech_rows124_127.py"
SPEC = importlib.util.spec_from_file_location("speech_finalize", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechRowsFinalizationTests(unittest.TestCase):
    def test_row_statuses_are_all_fail_closed(self) -> None:
        self.assertEqual({"124", "125", "126", "127"}, set(MODULE.ROW_STATUS))
        self.assertTrue(all(value.startswith("Blocked_") for value in MODULE.ROW_STATUS.values()))

    def test_csv_update_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fieldnames = ["Item_ID", "Status", "Coverage_Audit_Status", "Notes"]
            rows = [{"Item_ID": f"ITEM-W64-{number}", "Status": "Planned", "Coverage_Audit_Status": "planned", "Notes": "old"} for number in (124, 125, 126, 127)]
            rows.append({"Item_ID": "ITEM-W64-999", "Status": "UserOwned", "Coverage_Audit_Status": "keep", "Notes": "keep"})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader(); writer.writerows(rows)
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            first = path.read_bytes()
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            self.assertEqual(first, path.read_bytes())
            with path.open("r", encoding="utf-8", newline="") as handle:
                updated = list(csv.DictReader(handle))
            self.assertEqual("UserOwned", updated[-1]["Status"])
            self.assertTrue(all(updated[index]["Status"].startswith("Blocked_") for index in range(4)))


if __name__ == "__main__":
    unittest.main()
