from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "evaluate_wave64_speech_acoustics.py"
SPEC = importlib.util.spec_from_file_location("speech_acoustics_evaluator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechAcousticsEvaluatorTests(unittest.TestCase):
    def test_classification_requires_rows129_and130(self) -> None:
        rows = {"128": {"automated_runtime_pass": False, "production_character_identity_authority_pass": False, "row_complete": False}, "129": {"automated_runtime_pass": True}, "130": {"automated_runtime_pass": True}}
        self.assertEqual(MODULE.EXPECTED_TEXT, "We hold the frame steady and move on the beat.")
        self.assertEqual("PASS_WAVE64_ROWS129_130_AUTOMATED_QA_ROW128_IDENTITY_AUTHORITY_BLOCKED", MODULE.classify(rows))
        rows["129"]["automated_runtime_pass"] = False
        self.assertEqual("FAIL_WAVE64_SPEECH_VIRTUAL_MICROPHONE_QA", MODULE.classify(rows))
        rows["129"]["automated_runtime_pass"] = True
        rows["130"]["automated_runtime_pass"] = False
        self.assertEqual("FAIL_WAVE64_SPEECH_RESTORATION_QA", MODULE.classify(rows))

    def test_classification_rejects_row128_false_authority_state(self) -> None:
        rows = {"128": {"automated_runtime_pass": False, "production_character_identity_authority_pass": False, "row_complete": False}, "129": {"automated_runtime_pass": True}, "130": {"automated_runtime_pass": True}}
        rows["128"]["automated_runtime_pass"] = True
        self.assertEqual("FAIL_WAVE64_NONVERBAL_FALSE_AUTHORITY_STATE", MODULE.classify(rows))
        rows["128"]["automated_runtime_pass"] = False
        rows["128"]["production_character_identity_authority_pass"] = True
        self.assertEqual("FAIL_WAVE64_NONVERBAL_FALSE_AUTHORITY_STATE", MODULE.classify(rows))

    def test_rms_delta_db_is_directional(self) -> None:
        self.assertEqual(0.0, MODULE.rms_delta_db({"rms": 0.1}, {"rms": 0.1}))
        self.assertGreater(MODULE.rms_delta_db({"rms": 0.1}, {"rms": 0.2}), 5.9)
        self.assertLess(MODULE.rms_delta_db({"rms": 0.2}, {"rms": 0.1}), -5.9)

    def test_bounded_repair_contract_is_part_of_source(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("bounded_repair_sample_ratio_pass", source)
        self.assertIn("declick_max_repair_sample_ratio", source)
        self.assertIn("nonverbal_identity_metric_calibrated_for_this_comparison", source)
        self.assertIn('"automated_runtime_pass": False', source)


if __name__ == "__main__":
    unittest.main()
