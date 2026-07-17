#!/usr/bin/env python3

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_ultimate_multimodal_workflow_control_package.py"
SPEC = importlib.util.spec_from_file_location("wave64_builder", SCRIPT)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILDER
SPEC.loader.exec_module(BUILDER)


class Wave64ControlPackageTests(unittest.TestCase):
    def test_exact_row_range_and_workstream_allocation(self) -> None:
        BUILDER.validate_rows()
        self.assertEqual([row.number for row in BUILDER.ROWS], list(range(149, 221)))
        counts: dict[str, int] = {}
        for row in BUILDER.ROWS:
            counts[row.workstream] = counts.get(row.workstream, 0) + 1
        self.assertEqual(len(counts), 18)
        self.assertTrue(all(count == 4 for count in counts.values()))

    def test_new_dependencies_are_acyclic(self) -> None:
        for row in BUILDER.ROWS:
            self.assertTrue(all(dependency < row.number for dependency in row.dependencies if dependency >= 149))

    def test_write_then_check_in_isolated_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = BUILDER.build_outputs(root)
            self.assertTrue(BUILDER.check_outputs(root, outputs))
            BUILDER.write_outputs(root, outputs)
            self.assertEqual(BUILDER.check_outputs(root, outputs), [])
            item_req = root / "Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_REQUIREMENTS.json"
            tracker_req = root / "Plan/Tracker/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_REQUIREMENTS.json"
            self.assertEqual(item_req.read_bytes(), tracker_req.read_bytes())
            payload = json.loads(item_req.read_text(encoding="utf-8"))
            self.assertFalse(payload["runtime_complete"])
            self.assertFalse(payload["content_based_suppression"])
            self.assertEqual(payload["row_range"], {"first": 149, "last": 220, "count": 72})

    def test_outputs_are_checkout_location_independent(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_outputs = BUILDER.build_outputs(Path(first))
            second_outputs = BUILDER.build_outputs(Path(second) / "nested-checkout")
            self.assertEqual(first_outputs, second_outputs)

            item_path = Path("Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_ITEM_ROWS.csv")
            first_item = next(csv.DictReader(io.StringIO(first_outputs[item_path].decode("utf-8"))))
            self.assertEqual(first_item["Source_Plan_Root"], r"C:\Comfy_UI_Main\Plan")
            self.assertTrue(first_item["Citation_Full_Path"].startswith(r"C:\Comfy_UI_Main\Plan" + "\\"))

    def test_csv_ids_and_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outputs = BUILDER.build_outputs(Path(directory))
            item_bytes = outputs[Path("Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_ITEM_ROWS.csv")]
            tracker_bytes = outputs[Path("Plan/Tracker/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_TRACKER_ROWS.csv")]
            items = list(csv.DictReader(io.StringIO(item_bytes.decode("utf-8"))))
            trackers = list(csv.DictReader(io.StringIO(tracker_bytes.decode("utf-8"))))
            self.assertEqual(items[0]["Item_ID"], "ITEM-W64-149")
            self.assertEqual(items[-1]["Item_ID"], "ITEM-W64-220")
            self.assertEqual(trackers[0]["Tracker_ID"], "TRK-W64-149")
            self.assertEqual(trackers[-1]["Tracker_ID"], "TRK-W64-220")
            self.assertTrue(all(row["Status"] == BUILDER.STATUS for row in items + trackers))

    def test_check_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = BUILDER.build_outputs(root)
            BUILDER.write_outputs(root, outputs)
            target = root / "Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_ITEM_ROWS.csv"
            target.write_bytes(target.read_bytes() + b"\n")
            problems = BUILDER.check_outputs(root, outputs)
            self.assertEqual(len(problems), 1)
            self.assertTrue(any("mismatch" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
