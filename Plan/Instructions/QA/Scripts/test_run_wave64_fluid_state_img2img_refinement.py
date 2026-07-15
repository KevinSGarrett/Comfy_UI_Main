import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_fluid_state_img2img_refinement.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("run_wave64_fluid_state_img2img", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class RunWave64FluidStateImg2ImgRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = MODULE.pair.read_json(MODULE.DEFAULT_PROFILE)
        cls.workflow = MODULE.pair.read_json(MODULE.DEFAULT_WORKFLOW)

    def test_workflow_accepts_exact_revision_contract(self):
        MODULE.validate_workflow(self.workflow, self.profile)

    def test_workflow_rejects_denoise_drift(self):
        payload = json.loads(json.dumps(self.workflow))
        payload["7"]["inputs"]["denoise"] = 0.5
        with self.assertRaisesRegex(ValueError, "denoise drift"):
            MODULE.validate_workflow(payload, self.profile)

    def test_workflow_rejects_adapter_strength_drift(self):
        payload = json.loads(json.dumps(self.workflow))
        payload["2"]["inputs"]["strength_model"] = 0.4
        with self.assertRaisesRegex(ValueError, "model strength drift"):
            MODULE.validate_workflow(payload, self.profile)

    def test_revision_is_one_candidate_without_retry(self):
        contract = self.profile["revision_contract"]
        self.assertEqual(contract["authorized_candidate_count"], 1)
        self.assertFalse(contract["retry_allowed"])

    def test_revision_preserves_unrestricted_asset_visibility(self):
        boundaries = self.profile["boundaries"]
        self.assertFalse(boundaries["content_based_suppression"])
        self.assertFalse(boundaries["adult_or_nsfw_asset_visibility_restricted"])

    def test_multipart_body_contains_required_fields_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.png"
            path.write_bytes(b"png-bytes")
            body = MODULE.multipart_image_body(path, "source.png", "boundary")
            self.assertIn(b'name="type"', body)
            self.assertIn(b"input", body)
            self.assertIn(b'name="overwrite"', body)
            self.assertIn(b"png-bytes", body)
            self.assertTrue(body.endswith(b"--boundary--\r\n"))

    def test_metadata_is_not_submitted_as_node(self):
        self.assertNotIn("_meta", MODULE.pair.strip_metadata(self.workflow))


if __name__ == "__main__":
    unittest.main()
