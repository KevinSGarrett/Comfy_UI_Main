#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_sound_intelligence_planning_authority.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_row067_planning_authority", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MOD = _load_module()


def _copy_authority_tree(dst: Path) -> None:
    for rel in MOD.AUTHORITY_PATHS:
        src = ROOT / rel
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)


def _rewrite_tracker(dst: Path, mutator) -> None:
    path = dst / MOD.TRACKER_CSV
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())
    mutator(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class Row067PlanningAuthorityTests(unittest.TestCase):
    def test_live_tree_structural_gates_pass(self) -> None:
        payload = MOD.evaluate_planning_authority(ROOT)
        structural = [
            check
            for check in payload["checks"]
            if check["result"] != "advisory_fail" and not check["name"].endswith("_advisory")
        ]
        self.assertTrue(all(check["result"] == "pass" for check in structural), payload["checks"])
        self.assertTrue(payload["row_complete"])
        self.assertTrue(payload["planning_authority_accepted"])
        self.assertFalse(payload["runtime_completion_claimed"])
        self.assertFalse(payload["product_completion_claimed"])
        self.assertEqual(payload["dependency_graph"]["root_tracker_ids"], ["TRK-W64-067"])
        self.assertEqual(payload["dependency_graph"]["cycle_count"], 0)

    def test_missing_row_fails_parity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp)
            _copy_authority_tree(dst)

            def drop_last(rows):
                del rows[-1]

            _rewrite_tracker(dst, drop_last)
            payload = MOD.evaluate_planning_authority(dst)
            check = next(c for c in payload["checks"] if c["name"] == "SIP-V002_exact_tracker_rows067_112_present_once")
            self.assertEqual(check["result"], "fail")
            self.assertFalse(payload["row_complete"])

    def test_dependency_cycle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp)
            _copy_authority_tree(dst)

            def cycle(rows):
                # 067 -> 068 and 068 -> 067
                for row in rows:
                    if row["Tracker_ID"] == "TRK-W64-067":
                        row["Dependency_Prerequisite"] = "TRK-W64-068"
                    if row["Tracker_ID"] == "TRK-W64-068":
                        row["Dependency_Prerequisite"] = "TRK-W64-067"

            _rewrite_tracker(dst, cycle)
            # Keep item Notes parity with the mutated tracker deps so the cycle check is reached.
            items_path = dst / MOD.ITEMS_CSV
            with items_path.open(encoding="utf-8-sig", newline="") as handle:
                items = list(csv.DictReader(handle))
                fieldnames = list(items[0].keys())
            for row in items:
                if row["Item_ID"] == "ITEM-W64-067":
                    row["Notes"] = "Dependencies=ITEM-W64-068. synthetic cycle."
                if row["Item_ID"] == "ITEM-W64-068":
                    row["Notes"] = "Dependencies=ITEM-W64-067. synthetic cycle."
            with items_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(items)

            payload = MOD.evaluate_planning_authority(dst)
            check = next(c for c in payload["checks"] if c["name"] == "SIP-V007_dependency_graph_acyclic")
            self.assertEqual(check["result"], "fail")
            self.assertFalse(payload["row_complete"])

    def test_false_runtime_completion_flag_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp)
            _copy_authority_tree(dst)
            for rel in (MOD.TRACKER_REQUIREMENTS, MOD.ITEMS_REQUIREMENTS):
                path = dst / rel
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["planning_complete_runtime_complete"] = True
                path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            result = MOD.evaluate_planning_authority(dst)
            check = next(c for c in result["checks"] if c["name"] == "SIP-V012_planning_runtime_completion_false")
            self.assertEqual(check["result"], "fail")
            false_completion = next(c for c in result["checks"] if c["name"] == "SIP-V016_no_false_completion_claim")
            self.assertEqual(false_completion["result"], "fail")
            self.assertFalse(result["row_complete"])

    def test_evaluate_row067_complete_reads_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp)
            evidence = dst / MOD.DEFAULT_EVIDENCE
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(
                json.dumps(
                    {
                        "row_complete": True,
                        "runtime_completion_claimed": False,
                        "status": "PASS_PLANNING_AUTHORITY_ACCEPTED_NO_RUNTIME_COMPLETION",
                    }
                ),
                encoding="utf-8",
            )
            result = MOD.evaluate_row067_complete(dst)
            self.assertTrue(result["row067_complete"])
            self.assertTrue(result["dependency_satisfied"])


if __name__ == "__main__":
    unittest.main()
