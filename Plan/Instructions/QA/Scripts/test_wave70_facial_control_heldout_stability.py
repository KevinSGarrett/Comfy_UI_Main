#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/combine_wave70_facial_control_heldout_stability.py"
)
SPEC = importlib.util.spec_from_file_location("facial_stability", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record(name: str, passed: bool, empty: bool = False) -> dict:
    return {
        "class_name": name,
        "gate_pass": passed,
        "aggregate_iou": None if empty else (0.9 if passed else 0.5),
        "false_positive_ratio_vs_gold": None if empty else 0.05,
        "false_negative_ratio_vs_gold": None if empty else 0.05,
        "gold_empty_all_samples": empty,
        "failed_reasons": [] if passed else ["threshold_failed"],
    }


class StabilityTests(unittest.TestCase):
    def test_classifies_nonempty_empty_inconsistent_and_failed(self) -> None:
        control = {
            "hair": record("hair", True),
            "eye_g": record("eye_g", True, True),
            "neck": record("neck", False),
            "u_lip": record("u_lip", False),
        }
        heldout = {
            "hair": record("hair", True),
            "eye_g": record("eye_g", True, True),
            "neck": record("neck", True),
            "u_lip": record("u_lip", False),
        }
        decisions = {
            item["class_name"]: item["classification"]
            for item in MODULE.combine_class_records(control, heldout)
        }
        self.assertEqual(decisions["hair"], "cross_split_nonempty_candidate_evidence")
        self.assertEqual(decisions["eye_g"], "cross_split_empty_only_specificity_evidence")
        self.assertEqual(decisions["neck"], "split_inconsistent_blocked")
        self.assertEqual(decisions["u_lip"], "failed_both_splits_blocked")

    def test_rejects_class_coverage_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "class_coverage_mismatch"):
            MODULE.combine_class_records(
                {"hair": record("hair", True)},
                {"hair": record("hair", True), "skin": record("skin", True)},
            )

    def test_blocks_split_presence_mismatch_even_when_both_gates_pass(self) -> None:
        decision = MODULE.combine_class_records(
            {"hat": record("hat", True, True)},
            {"hat": record("hat", True, False)},
        )[0]
        self.assertEqual(
            decision["classification"], "split_presence_inconsistent_blocked"
        )

    def test_project_path_rejects_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory) / "project"
            project_root.mkdir()
            outside = Path(directory) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_path_outside_project"):
                MODULE.project_path(project_root, str(outside))

    def test_build_evidence_rejects_threshold_mismatch_before_benchmark_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            control_path = project_root / "control.json"
            heldout_path = project_root / "heldout.json"
            base = {
                "mask_promoted": False,
                "certification_authorized": False,
                "class_gate_records": [record("skin", True)],
            }
            control_path.write_text(
                json.dumps({**base, "thresholds": {"iou": 0.85}}),
                encoding="utf-8",
            )
            heldout_path.write_text(
                json.dumps({**base, "thresholds": {"iou": 0.90}}),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                project_root=project_root,
                control_gate=control_path,
                heldout_gate=heldout_path,
                timestamp="2026-07-14T10:32:56-05:00",
            )
            with self.assertRaisesRegex(ValueError, "gate_threshold_mismatch"):
                MODULE.build_evidence(args)

    def test_records_never_authorize_promotion(self) -> None:
        decision = MODULE.combine_class_records(
            {"hair": record("hair", True)}, {"hair": record("hair", True)}
        )[0]
        self.assertFalse(decision["promotion_authorized"])
        self.assertFalse(decision["certification_authorized"])


if __name__ == "__main__":
    unittest.main()
