from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "evaluate_wave64_qwen3_tts_continuity_matrix.py"
SPEC = importlib.util.spec_from_file_location("qwen_continuity_evaluator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenContinuityEvaluatorTests(unittest.TestCase):
    def test_partitions_are_disjoint_and_cover_all_lines(self) -> None:
        self.assertFalse(MODULE.CALIBRATION_IDS & MODULE.HELD_OUT_IDS)
        self.assertEqual({f"L{index:02d}" for index in range(1, 11)}, MODULE.CALIBRATION_IDS | MODULE.HELD_OUT_IDS)

    def test_partition_summary_does_not_invent_false_acceptance(self) -> None:
        metrics = [{"line_id": line_id, "speaker_similarity_to_reference": 0.5} for line_id in sorted(MODULE.CALIBRATION_IDS)]
        summary = MODULE.summarize_partition(metrics, MODULE.CALIBRATION_IDS, 0.4)
        self.assertFalse(summary["false_acceptance_measured"])
        self.assertIsNone(summary["false_acceptance_rate"])
        self.assertFalse(summary["production_calibration_allowed"])

    def test_partition_summary_counts_false_rejections(self) -> None:
        metrics = [{"line_id": line_id, "speaker_similarity_to_reference": 0.5} for line_id in sorted(MODULE.HELD_OUT_IDS)]
        metrics[0]["speaker_similarity_to_reference"] = 0.2
        summary = MODULE.summarize_partition(metrics, MODULE.HELD_OUT_IDS, 0.4)
        self.assertEqual(1, summary["false_rejection_count_at_chain_specific_threshold"])
        self.assertEqual(0.2, summary["false_rejection_rate_at_chain_specific_threshold"])

    def test_source_keeps_all_authority_gates_fail_closed(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"false_acceptance_measured": False', source)
        self.assertIn('"certified_character_authority_pass": False', source)
        self.assertIn('"multilingual_content_qa_pass": False', source)
        self.assertIn('"production_promotion_claimed": False', source)


if __name__ == "__main__":
    unittest.main()
