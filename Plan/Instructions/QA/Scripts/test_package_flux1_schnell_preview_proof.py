from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/package_flux1_schnell_preview_proof.py"
SPEC = importlib.util.spec_from_file_location("package_flux1_schnell_preview_proof", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FluxSchnellProofTests(unittest.TestCase):
    def test_extract_history_entry_rejects_wrong_prompt_id(self) -> None:
        history = {"p1": {"prompt": [1, "other", {}, {}, []]}}
        with self.assertRaisesRegex(ValueError, "ID binding mismatch"):
            MODULE.extract_history_entry(history, "p1")

    def test_history_timing_requires_start_and_success(self) -> None:
        timing = MODULE.history_timing(
            {
                "messages": [
                    ["execution_start", {"timestamp": 1000}],
                    ["execution_cached", {"nodes": []}],
                    ["execution_success", {"timestamp": 4250}],
                ]
            }
        )
        self.assertEqual(timing["elapsed_seconds"], 3.25)
        self.assertEqual(timing["cached_nodes"], [])

    def test_output_records_are_normalized(self) -> None:
        entry = {
            "outputs": {
                "8": {
                    "images": [
                        {"filename": "preview.png", "subfolder": "flux", "type": "output"}
                    ]
                }
            }
        }
        self.assertEqual(
            MODULE.output_records(entry),
            [
                {
                    "node_id": "8",
                    "filename": "preview.png",
                    "subfolder": "flux",
                    "type": "output",
                }
            ],
        )

    def test_checkpoint_options_supports_classic_combo_shape(self) -> None:
        payload = {
            "CheckpointLoaderSimple": {
                "input": {"required": {"ckpt_name": [["a.safetensors"], {"tooltip": "x"}]}}
            }
        }
        self.assertEqual(MODULE.checkpoint_options(payload), ["a.safetensors"])

    def test_visual_review_is_hash_bound_and_all_true(self) -> None:
        good = {"artifact_sha256": "a" * 64, "checks": {"geometry": True}, "visual_pass": True}
        self.assertEqual(MODULE.validate_visual_review(good, "a" * 64), [])
        bad = {"artifact_sha256": "b" * 64, "checks": {"geometry": False}, "visual_pass": True}
        self.assertEqual(len(MODULE.validate_visual_review(bad, "a" * 64)), 2)

    def test_image_qa_rejects_flat_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "flat.png"
            Image.new("RGB", (16, 16), (20, 20, 20)).save(path)
            self.assertFalse(MODULE.image_qa(path)["nonblank_variance_pass"])

    def test_canonical_workflow_has_schnell_contract(self) -> None:
        workflow = json.loads(MODULE.DEFAULT_WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual(workflow["1"]["inputs"]["ckpt_name"], "flux1-schnell-fp8.safetensors")
        self.assertEqual(workflow["6"]["inputs"]["steps"], 4)
        self.assertEqual(workflow["5"]["inputs"]["width"], 512)
        self.assertEqual(workflow["5"]["inputs"]["height"], 512)

    def test_runtime_requirements_bind_model_license_and_history(self) -> None:
        requirements = json.loads(MODULE.DEFAULT_REQUIREMENTS.read_text(encoding="utf-8"))
        model = requirements["required_models"][0]
        self.assertEqual(model["sha256"], "ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72")
        self.assertEqual(model["bytes"], 17236328572)
        self.assertEqual(requirements["licensed_source"]["license_id"], "Apache-2.0")
        self.assertEqual(
            requirements["historical_lineage"]["historical_lane_id"],
            "true_flux_schnell_reference_smoke",
        )

    def test_plan_and_workflow_mirrors_are_byte_identical(self) -> None:
        project_root = SCRIPT.parents[3]
        plan_root = project_root / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_schnell_preview"
        workflow_root = project_root / "Workflows/base_generation/flux1_schnell_preview"
        for name in (
            "workflow.api.json",
            "runtime_requirements.json",
            "smoke_test_request.json",
            "patch_points.json",
            "README.md",
        ):
            self.assertEqual((plan_root / name).read_bytes(), (workflow_root / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
