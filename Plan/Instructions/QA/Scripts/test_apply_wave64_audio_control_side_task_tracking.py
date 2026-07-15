import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/apply_wave64_audio_control_side_task_tracking.py"
SPEC = importlib.util.spec_from_file_location("audio_control_tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AudioControlSideTaskTrackingTests(unittest.TestCase):
    def test_report_reconciliation_keeps_rows_blocked(self):
        for item_id, relative in MODULE.REPORT_PATHS.items():
            payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            updated = MODULE.update_report_payload(payload)
            self.assertFalse(updated["row_complete"])
            self.assertEqual(updated["status"], MODULE.ROW_STATUS[item_id[-3:]])
            self.assertTrue(updated["implementation"]["human_playback_review_authority_path_ready"])

    def test_csv_update_is_idempotent_and_limits_human_work_to_audio_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary) / "tracker.csv"
            shutil.copy2(ROOT / MODULE.TRACKER_PATHS[0], temp)
            first = MODULE.update_csv(temp, key="Tracker_ID", evidence_field="Evidence_Path", apply=True)
            first_bytes = temp.read_bytes()
            second = MODULE.update_csv(temp, key="Tracker_ID", evidence_field="Evidence_Path", apply=True)
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, temp.read_bytes())
            with temp.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            audio = [row for row in rows if row["Tracker_ID"] in {f"TRK-W64-{number:03d}" for number in range(25, 34)}]
            self.assertEqual(len(audio), 9)
            self.assertTrue(all(row["Human_Input_Allowed"] == "TRUE" for row in audio))
            self.assertTrue(all("bounded human playback" in row["Autonomous_Execution_Mode"] for row in audio))


if __name__ == "__main__":
    unittest.main()
