import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_fluid_state_masked_inpaint.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("run_wave64_fluid_state_masked_inpaint", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class RunWave64FluidStateMaskedInpaintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = MODULE.pair.read_json(MODULE.DEFAULT_PROFILE)
        cls.workflow = MODULE.pair.read_json(MODULE.DEFAULT_WORKFLOW)

    def test_workflow_accepts_exact_contract(self):
        MODULE.validate_workflow(self.workflow, self.profile)

    def test_workflow_rejects_grow_mask_drift(self):
        payload = json.loads(json.dumps(self.workflow))
        payload["7"]["inputs"]["grow_mask_by"] = 20
        with self.assertRaisesRegex(ValueError, "grow_mask_by drift"):
            MODULE.validate_workflow(payload, self.profile)

    def test_workflow_rejects_denoise_drift(self):
        payload = json.loads(json.dumps(self.workflow))
        payload["8"]["inputs"]["denoise"] = 0.9
        with self.assertRaisesRegex(ValueError, "denoise drift"):
            MODULE.validate_workflow(payload, self.profile)

    def test_mask_is_bounded_nonblank_and_not_truth(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "mask.png"
            binding = MODULE.generate_edit_mask(self.profile["mask_contract"], output)
            self.assertGreater(binding["nonzero_pixel_ratio"], 0.01)
            self.assertLess(binding["nonzero_pixel_ratio"], 0.20)
            self.assertTrue(binding["edit_region_mask_is_not_geometry_or_segmentation_truth"])
            self.assertTrue(binding["mask_promotion_forbidden"])
            with Image.open(output) as image:
                self.assertEqual(image.size, (768, 1024))

    def test_revision_is_one_candidate_without_retry(self):
        contract = self.profile["revision_contract"]
        self.assertEqual(contract["authorized_candidate_count"], 1)
        self.assertFalse(contract["retry_allowed"])

    def test_asset_visibility_and_mask_boundaries_remain_explicit(self):
        boundaries = self.profile["boundaries"]
        self.assertFalse(boundaries["content_based_suppression"])
        self.assertFalse(boundaries["adult_or_nsfw_asset_visibility_restricted"])
        self.assertFalse(boundaries["edit_mask_consumed_as_truth"])
        self.assertFalse(boundaries["body_or_contact_mask_authority_claimed"])


if __name__ == "__main__":
    unittest.main()
