from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "run_wave64_qwen3_tts_continuity_matrix.py"
SPEC = importlib.util.spec_from_file_location("qwen_continuity_runner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class QwenContinuityRunnerTests(unittest.TestCase):
    def test_line_plan_has_nine_unique_new_lines_and_three_scenes(self) -> None:
        MODULE.validate_line_plan(MODULE.LINE_PLAN)
        self.assertEqual(9, len(MODULE.LINE_PLAN))
        self.assertEqual({"SCENE-A", "SCENE-B", "SCENE-C"}, {line["scene_id"] for line in MODULE.LINE_PLAN})

    def test_line_plan_covers_multilingual_and_code_switch_roles(self) -> None:
        roles = {line["language_role"] for line in MODULE.LINE_PLAN}
        self.assertEqual({"english", "multilingual", "code_switch"}, roles)
        self.assertEqual({"English", "Spanish", "French", "Auto"}, {line["language"] for line in MODULE.LINE_PLAN})

    def test_line_plan_rejects_duplicate_seed(self) -> None:
        plan = [dict(line) for line in MODULE.LINE_PLAN]
        plan[-1]["seed"] = plan[0]["seed"]
        with self.assertRaises(MODULE.MatrixError):
            MODULE.validate_line_plan(plan)

    def test_runtime_requires_pinned_onnxruntime(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('onnxruntime.__version__ != "1.27.0"', source)
        self.assertIn("onnxruntime_system_site_packages", source)
        self.assertIn("broad system site-packages path remained active", source)

    def test_import_preflight_precedes_immutable_output_creation(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(source.index("from transformers import AutoProcessor"), source.index("output_dir.mkdir(parents=True)"))
        self.assertLess(source.index("from qwen_tts import Qwen3TTSModel"), source.index("output_dir.mkdir(parents=True)"))


if __name__ == "__main__":
    unittest.main()
