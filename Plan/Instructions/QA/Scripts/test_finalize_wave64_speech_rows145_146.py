from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "finalize_wave64_speech_rows145_146.py"
SPEC = importlib.util.spec_from_file_location("wave64_speech_bridge_finalizer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_smoke() -> dict:
    return {
        "classification": MODULE.EXPECTED_CLASSIFICATION,
        "media_tree_unchanged": True,
        "queue_idle_before": True,
        "result": {
            "classification": "W64_SPEECH_BRIDGE_DRY_RUN_VALIDATED_AUTHORITY_BLOCKED",
            "status": "BLOCKED",
            "cache_key": "a" * 64,
            "blockers": ["BLOCKED_VOICE_AUTHORITY_MISSING", "BLOCKED_PRODUCTION_CERTIFICATION_INCOMPLETE"],
            "boundaries": {"dry_run": True, "engine_subprocess_called": False},
            "result_binding": {},
            "telemetry_binding": {},
        },
        "boundaries": {
            "media_generated": False, "candidate_media_written": False, "promotion_attempted": False,
            "production_authority_claimed": False, "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False, "content_based_suppression": False,
        },
        "node_object_info": {"category": "Wave64/Speech", "output_node": True},
    }


class Wave64SpeechBridgeFinalizerTests(unittest.TestCase):
    def test_row_statuses_are_fail_closed(self) -> None:
        self.assertEqual({"145", "146"}, set(MODULE.ROW_STATUS))
        self.assertTrue(all(status.startswith("Blocked_") for status in MODULE.ROW_STATUS.values()))

    def test_validate_smoke_rejects_false_promotion_before_bindings(self) -> None:
        value = valid_smoke()
        value["boundaries"]["promotion_attempted"] = True
        with self.assertRaisesRegex(MODULE.FinalizationError, "improperly claims"):
            MODULE.validate_smoke(value)

    def test_validate_smoke_requires_authority_blockers(self) -> None:
        value = valid_smoke()
        value["result"]["blockers"] = []
        with self.assertRaisesRegex(MODULE.FinalizationError, "blockers are missing"):
            MODULE.validate_smoke(value)

    def test_validate_smoke_requires_live_output_node(self) -> None:
        value = valid_smoke()
        value["node_object_info"]["output_node"] = False
        with self.assertRaisesRegex(MODULE.FinalizationError, "object_info"):
            MODULE.validate_smoke(value)

    def test_csv_update_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fields = ["Item_ID", "Status", "Coverage_Audit_Status", "Evidence_Path", "Status_Decision", "Notes"]
            rows = [{name: "old" for name in fields} | {"Item_ID": f"ITEM-W64-{number}"} for number in (145, 146)]
            rows.append({name: "keep" for name in fields} | {"Item_ID": "ITEM-W64-999", "Status": "UserOwned"})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            first = path.read_bytes()
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            self.assertEqual(first, path.read_bytes())
            with path.open("r", encoding="utf-8", newline="") as handle:
                updated = list(csv.DictReader(handle))
            self.assertEqual("UserOwned", updated[-1]["Status"])
            self.assertTrue(all(updated[index]["Status"].startswith("Blocked_") for index in range(2)))

    def test_copy_exact_rejects_hash_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            target = root / "target.json"
            source.write_text("source", encoding="utf-8")
            target.write_text("target", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.FinalizationError, "hash conflict"):
                MODULE.copy_exact(source, target)


if __name__ == "__main__":
    unittest.main()
