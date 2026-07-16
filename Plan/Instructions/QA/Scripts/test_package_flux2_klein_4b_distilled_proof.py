from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/package_flux2_klein_4b_distilled_proof.py"
SPEC = importlib.util.spec_from_file_location("package_flux2_klein_4b_distilled_proof", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Flux2KleinProofTests(unittest.TestCase):
    def test_history_binding_rejects_wrong_prompt(self) -> None:
        with self.assertRaisesRegex(ValueError, "binding"):
            MODULE.history_entry({"p": {"prompt": [0, "other", {}, {}]}}, "p")

    def test_timing_extracts_cache_and_elapsed(self) -> None:
        entry = {"status": {"messages": [["execution_start", {"timestamp": 1000}], ["execution_cached", {"nodes": ["1"]}], ["execution_success", {"timestamp": 4250}]]}}
        self.assertEqual(MODULE.timing(entry)["elapsed_seconds"], 3.25)
        self.assertEqual(MODULE.timing(entry)["cached_nodes"], ["1"])

    def test_outputs_are_normalized(self) -> None:
        entry = {"outputs": {"13": {"images": [{"filename": "a.png", "subfolder": "flux2", "type": "output"}]}}}
        self.assertEqual(MODULE.outputs(entry)[0]["node_id"], "13")

    def test_output_binding_requires_exact_node_name_subfolder_and_type(self) -> None:
        good = [{"node_id": "13", "filename": "a.png", "subfolder": MODULE.LANE_ID, "type": "output"}]
        self.assertTrue(MODULE.output_matches(good, Path("a.png"), "13"))
        self.assertFalse(MODULE.output_matches(good, Path("other.png"), "13"))
        self.assertFalse(MODULE.output_matches(good, Path("a.png"), "19"))

    def test_review_is_hash_and_check_bound(self) -> None:
        review = {"artifact_sha256": "a" * 64, "checks": {"geometry": True}, "visual_pass": True}
        self.assertEqual(MODULE.validate_review(review, "a" * 64), [])
        review["checks"]["geometry"] = False
        self.assertIn("review_checks_not_all_true", MODULE.validate_review(review, "a" * 64))

    def test_edit_metric_requires_change_concentration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.png"
            edited = Path(temp) / "edited.png"
            Image.new("RGB", (512, 512), "white").save(source)
            image = Image.new("RGB", (512, 512), "white")
            for x in range(40, 475):
                for y in range(120, 370):
                    image.putpixel((x, y), (0, 0, 255))
            image.save(edited)
            self.assertTrue(MODULE.edit_metrics(source, edited)["targeted_change_concentration_pass"])

    def test_canonical_workflows_are_separate_and_flux2_only(self) -> None:
        root = SCRIPT.parents[3] / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled"
        canonical = MODULE.load_json(root / "workflow.api.json")
        t2i = MODULE.load_json(root / "text_to_image.api.json")
        edit = MODULE.load_json(root / "single_reference_edit.api.json")
        self.assertEqual(canonical, t2i)
        self.assertNotEqual(t2i, edit)
        self.assertEqual(t2i["2"]["inputs"]["type"], "flux2")
        self.assertEqual(edit["9"]["class_type"], "ReferenceLatent")
        self.assertEqual(t2i["8"]["inputs"]["steps"], 4)

    def test_required_nodes_are_scoped_per_capability(self) -> None:
        root = SCRIPT.parents[3] / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled"
        requirements = MODULE.load_json(root / "runtime_requirements.json")
        t2i = MODULE.load_json(root / "text_to_image.api.json")
        edit = MODULE.load_json(root / "single_reference_edit.api.json")
        self.assertEqual(requirements["required_nodes"], requirements["required_nodes_by_capability"]["text_to_image"])
        self.assertNotIn("ReferenceLatent", requirements["required_nodes"])
        self.assertIn("ReferenceLatent", requirements["required_nodes_by_capability"]["single_reference_edit"])
        self.assertTrue(set(requirements["required_nodes_by_capability"]["text_to_image"]) <= {node["class_type"] for node in t2i.values()})
        self.assertTrue(set(requirements["required_nodes_by_capability"]["single_reference_edit"]) <= {node["class_type"] for node in edit.values()})

    def test_plan_and_workflow_mirrors_are_byte_identical(self) -> None:
        root = SCRIPT.parents[3]
        plan = root / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled"
        mirror = root / "Workflows/base_generation/flux2_klein_4b_distilled"
        for name in ("workflow.api.json", "text_to_image.api.json", "single_reference_edit.api.json", "runtime_requirements.json", "patch_points.json", "smoke_test_request.json", "smoke_test_requests.json", "README.md"):
            self.assertEqual((plan / name).read_bytes(), (mirror / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
