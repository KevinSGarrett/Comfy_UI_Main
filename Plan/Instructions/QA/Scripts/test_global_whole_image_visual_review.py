from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "Plan"
VALIDATOR = PLAN / "07_IMPLEMENTATION/scripts/validate_global_whole_image_visual_review.py"
EXAMPLE = PLAN / "09_EXAMPLES/global_whole_image_visual_review.example.json"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), "--input", str(path)], cwd=ROOT, capture_output=True, text=True, check=False)


def _load_validator():
    scripts = str(PLAN / "07_IMPLEMENTATION/scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("validate_global_whole_image_visual_review", VALIDATOR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class GlobalWholeImageVisualReviewTests(unittest.TestCase):
    def test_current_blocked_example_validates(self):
        result = run(EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_print_vlm_env_defaults_to_llava_13b(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("WAVE64_VLM", "OLLAMA_HOST", "WAVE64_LLM"))}
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--print-vlm-env"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["WAVE64_VLM_URL"], "http://127.0.0.1:11434")
        self.assertEqual(payload["WAVE64_VLM_MODEL"], "llava:13b")
        self.assertFalse(payload["product_completion_claimed"])
        self.assertTrue(payload["row074_pcm_left_alone"])
        self.assertFalse(payload["row_complete"])

    def test_vlm_env_receipt_reads_wave64_env(self):
        mod = _load_validator()
        with mock.patch.dict(
            "os.environ",
            {
                "WAVE64_VLM_URL": "http://127.0.0.1:11434",
                "WAVE64_VLM_MODEL": "llava:13b",
            },
            clear=True,
        ):
            receipt = mod.vlm_env_receipt()
            self.assertEqual(mod.resolve_vlm_model(), "llava:13b")
            self.assertEqual(mod.resolve_base_url(), "http://127.0.0.1:11434")
        self.assertEqual(receipt["WAVE64_VLM_URL"], "http://127.0.0.1:11434")
        self.assertEqual(receipt["WAVE64_VLM_MODEL"], "llava:13b")
        self.assertEqual(mod.DEFAULT_VLM_MODEL, "llava:13b")

    def test_fully_bound_review_can_pass(self):
        value = self.passing()
        self.assert_valid(value)

    def test_local_target_pass_with_non_target_failure_is_rejected(self):
        value = self.passing()
        value["required_non_target_region_scan"]["status"] = "fail"
        self.assert_rejected(value, "target, and non-target gates")

    def test_global_defect_cannot_coexist_with_pass(self):
        value = self.passing()
        value["reject_on_any_global_defect"]["global_defects"] = [{"code": "background_drift", "severity": "blocking", "region": "background"}]
        self.assert_rejected(value, "any global defect requires")

    def test_global_defect_with_rejection_validates(self):
        value = self.passing()
        value["reject_on_any_global_defect"].update({"status": "fail", "global_defects": [{"code": "background_drift", "severity": "blocking", "region": "background"}], "rejection_applied": True})
        value["overall_decision"] = "reject"
        self.assert_valid(value)

    def test_uninspected_category_is_rejected(self):
        value = self.passing()
        value["hands_face_body_background_contact_lighting_check"]["lighting"]["inspected"] = False
        self.assert_rejected(value, "lighting must be explicitly inspected")

    def test_not_visible_category_requires_reason(self):
        value = self.passing()
        value["hands_face_body_background_contact_lighting_check"]["hands"]["reason"] = ""
        self.assert_rejected(value, "hands not-applicable coverage requires")

    def test_target_names_must_match(self):
        value = self.passing()
        value["required_target_region_check"]["target_region"] = "wrong_region"
        self.assert_rejected(value, "must match localized_change.target_region")

    def test_invalid_artifact_hash_is_rejected(self):
        value = self.passing()
        value["artifact"]["sha256"] = "bad"
        self.assert_rejected(value, "lowercase SHA256")

    def passing(self) -> dict:
        value = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
        value["whole_frame_visual_scan"].update({"status": "pass", "pre_edit_status": "pass", "post_edit_status": "pass"})
        value["required_target_region_check"]["status"] = "pass"
        value["required_non_target_region_scan"]["status"] = "pass"
        value["reject_on_any_global_defect"].update({"status": "pass", "global_defects": [], "rejection_applied": False})
        value["overall_decision"] = "pass"
        return value

    def assert_valid(self, value: dict):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_rejected(self, value: dict, message: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stdout)


if __name__ == "__main__":
    unittest.main()
