from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/validate_wave64_row023_local_reaffirm_20260720.py"
)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("row023_local_reaffirm", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Row023LocalReaffirmTests(unittest.TestCase):
    def test_offline_reaffirm_holds_without_visual_pass(self) -> None:
        report = MODULE.validate(PROJECT_ROOT)
        self.assertEqual(report["result"], "pass_offline_reaffirm_hold")
        self.assertEqual(report["candidate_sha256"], MODULE.CANDIDATE_SHA)
        self.assertGreaterEqual(report["blue_excess_delta_end_minus_start"], MODULE.MIN_BLUE_DELTA)
        self.assertEqual(len(report["missing_wan_assets"]), 3)
        self.assertFalse(report["visual_qa_pass_bounded"])
        self.assertFalse(report["row_complete"])


if __name__ == "__main__":
    unittest.main()
