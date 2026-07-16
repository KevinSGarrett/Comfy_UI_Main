from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_rows029_030_056_room_spatial_runtime.py"
SPEC = importlib.util.spec_from_file_location("finalize_wave64_rows029_030_056_room_spatial_runtime", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FinalizeRows029030056Tests(unittest.TestCase):
    def test_statuses_are_blocked_and_non_pass_like(self) -> None:
        self.assertEqual({"029", "030", "056"}, set(MODULE.ROW_STATUS))
        self.assertTrue(all(status.startswith("Blocked_") for status in MODULE.ROW_STATUS.values()))

    def test_validate_runtime_rejects_authority_promotion(self) -> None:
        runtime = {
            "classification": MODULE.EXPECTED_CLASSIFICATION,
            "technical_gates": {"technical": True},
            "authority_gates": {"production": True},
            "row_results": {number: {"row_complete": False, "pass_like": False} for number in MODULE.ROW_STATUS},
            "boundaries": {},
        }
        correction = {"classification": MODULE.CORRECTION_CLASSIFICATION}
        with self.assertRaisesRegex(MODULE.FinalizationError, "not fail-closed"):
            MODULE.validate_runtime(runtime, correction)

    def test_csv_update_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fields = ["Tracker_ID", "Status", "Status_Decision", "Evidence_Path", "Coverage_Audit_Status", "Notes"]
            rows = [
                {field: (f"TRK-W64-{number}" if field == "Tracker_ID" else "old") for field in fields}
                for number in ("029", "030", "056")
            ]
            rows.append({field: ("TRK-W64-999" if field == "Tracker_ID" else "keep") for field in fields})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            MODULE.update_rows(path, "Tracker_ID", "TRK", "evidence.json")
            first = path.read_bytes()
            MODULE.update_rows(path, "Tracker_ID", "TRK", "evidence.json")
            self.assertEqual(first, path.read_bytes())
            with path.open("r", encoding="utf-8", newline="") as handle:
                updated = list(csv.DictReader(handle))
            self.assertEqual("keep", updated[-1]["Status"])

    def test_advanced_registry_updates_only_room_system(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            MODULE.write_json_atomic(path, {
                "advanced_systems": [
                    {"system_id": "room_acoustics_spatial_audio", "runtime_promotion_state": "old", "blockers": []},
                    {"system_id": "other", "runtime_promotion_state": "keep", "blockers": ["keep"]},
                ],
                "proof_summary": {"direct_runtime_proof_missing": 5},
            })
            updated = MODULE.update_advanced_registry(path, {"path": "evidence.json", "sha256": "a" * 64})
            self.assertEqual("bounded_technical_runtime_partial_authority_blocked", updated["advanced_systems"][0]["runtime_promotion_state"])
            self.assertEqual("keep", updated["advanced_systems"][1]["runtime_promotion_state"])
            self.assertEqual(4, updated["proof_summary"]["direct_runtime_proof_missing"])

    def test_copy_exact_rejects_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"source")
            destination.write_bytes(b"conflict")
            with self.assertRaises(MODULE.FinalizationError):
                MODULE.copy_exact(source, destination)


if __name__ == "__main__":
    unittest.main()
