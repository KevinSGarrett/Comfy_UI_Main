import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_fluid_state_continuity_pair.py"
SPEC = importlib.util.spec_from_file_location("run_wave64_fluid_state_pair", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class RunWave64FluidStateContinuityPairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = MODULE.read_json(MODULE.DEFAULT_PROFILE)
        cls.baseline = MODULE.read_json(MODULE.DEFAULT_BASELINE)
        cls.state = MODULE.read_json(MODULE.DEFAULT_STATE)

    def test_templates_accept_exact_contract(self):
        MODULE.validate_workflow(self.baseline, "baseline_dry_state", self.profile)
        MODULE.validate_workflow(self.state, "generated_tears_state", self.profile)

    def test_metadata_is_removed_before_submission(self):
        prompt = MODULE.strip_metadata(self.baseline)
        self.assertNotIn("_meta", prompt)
        self.assertEqual(prompt["1"]["class_type"], "CheckpointLoaderSimple")

    def test_baseline_rejects_nonzero_adapter_strength(self):
        payload = MODULE.json.loads(MODULE.json.dumps(self.baseline))
        payload["2"]["inputs"]["strength_model"] = 0.1
        with self.assertRaisesRegex(ValueError, "baseline model strength"):
            MODULE.validate_workflow(payload, "baseline_dry_state", self.profile)

    def test_state_rejects_seed_drift(self):
        payload = MODULE.json.loads(MODULE.json.dumps(self.state))
        payload["6"]["inputs"]["seed"] += 1
        with self.assertRaisesRegex(ValueError, "seed drift"):
            MODULE.validate_workflow(payload, "generated_tears_state", self.profile)

    def test_unknown_pair_role_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown pair role"):
            MODULE.validate_workflow(self.state, "retry", self.profile)

    def test_model_name_normalization_accepts_separator_variants(self):
        left = MODULE.normalized_model_name("wave42/sdxl/file.safetensors")
        right = MODULE.normalized_model_name("wave42\\sdxl\\file.safetensors")
        self.assertEqual(left, right)

    def test_queue_idle_requires_both_lists_empty(self):
        self.assertTrue(MODULE.queue_is_idle({"queue_running": [], "queue_pending": []}))
        self.assertFalse(MODULE.queue_is_idle({"queue_running": [[1]], "queue_pending": []}))
        self.assertFalse(MODULE.queue_is_idle({"queue_running": [], "queue_pending": [[2]]}))

    def test_image_records_extracts_history_output(self):
        history = {
            "abc": {
                "outputs": {
                    "8": {
                        "images": [
                            {"filename": "one.png", "subfolder": "pair", "type": "output"}
                        ]
                    }
                }
            }
        }
        records = MODULE.image_records(history, "abc")
        self.assertEqual(records[0]["node_id"], "8")
        self.assertEqual(records[0]["filename"], "one.png")

    def test_image_technical_qa_detects_nonblank_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "image.png"
            image = Image.new("RGB", (4, 4), (10, 20, 30))
            image.putpixel((0, 0), (200, 100, 50))
            image.save(path)
            report = MODULE.image_technical_qa(path)
            self.assertTrue(report["png_opened"])
            self.assertTrue(report["nonblank_variance_pass"])

    def test_pair_comparison_records_difference_without_visual_promotion(self):
        with tempfile.TemporaryDirectory() as temporary:
            baseline = Path(temporary) / "baseline.png"
            state = Path(temporary) / "state.png"
            Image.new("RGB", (8, 8), (20, 20, 20)).save(baseline)
            Image.new("RGB", (8, 8), (80, 20, 20)).save(state)
            report = MODULE.compare_images(baseline, state)
            self.assertTrue(report["distinct_media_hashes"])
            self.assertGreater(report["changed_pixel_ratio"], 0.0)
            self.assertIsNone(report["identity_continuity_pass"])
            self.assertEqual(report["visual_review_status"], "pending_direct_codex_review")

    def test_profile_keeps_asset_visibility_unrestricted(self):
        boundaries = self.profile["boundaries"]
        self.assertFalse(boundaries["content_based_suppression"])
        self.assertFalse(boundaries["adult_or_nsfw_asset_visibility_restricted"])


if __name__ == "__main__":
    unittest.main()
