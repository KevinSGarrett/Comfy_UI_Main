from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/reconcile_wave64_animatediff_meaningful_sequence.py"
spec = importlib.util.spec_from_file_location("reconcile_wave64_animatediff_meaningful_sequence", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class MeaningfulSequenceReconciliationTest(unittest.TestCase):
    def test_add_entries_is_idempotent(self) -> None:
        value = module.add_entries("alpha; beta", ["beta", "gamma"])
        self.assertEqual(value, "alpha; beta; gamma")
        self.assertEqual(module.add_entries(value, ["gamma"]), value)

    def test_evidence_is_hash_bound_and_fail_closed(self) -> None:
        result = module.validate_evidence()
        self.assertEqual(result["failed_checks"], [])
        self.assertEqual(len(result["checks"]), 9)


if __name__ == "__main__":
    unittest.main()
