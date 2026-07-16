from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/reconcile_wave64_flux2_klein_capability.py"
SPEC = importlib.util.spec_from_file_location("reconcile_wave64_flux2_klein_capability", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Flux2KleinReconciliationTests(unittest.TestCase):
    def test_append_unique_is_idempotent(self) -> None:
        self.assertEqual(MODULE.append_unique(["a"], ["a", "b"]), ["a", "b"])
        self.assertEqual(MODULE.append_unique(["a", "b"], ["b"]), ["a", "b"])

    def test_semicolon_append_is_idempotent(self) -> None:
        value = MODULE.append_semicolon("a; b", "b")
        self.assertEqual(value, "a; b")
        self.assertEqual(MODULE.append_semicolon(value, "c"), "a; b; c")

    def test_three_exact_model_hashes_are_declared(self) -> None:
        self.assertEqual(len(MODULE.MODEL_HASHES), 3)
        self.assertTrue(all(len(value) == 64 for value in MODULE.MODEL_HASHES))

    def test_evidence_paths_are_distinct(self) -> None:
        self.assertNotEqual(MODULE.EVIDENCE_REL, MODULE.RECONCILIATION_REL)
        self.assertNotEqual(MODULE.STATIC_EVIDENCE_REL, MODULE.EVIDENCE_REL)
        self.assertTrue(MODULE.MIRROR_REL.startswith("Plan/Tracker/Evidence/"))

    def test_existing_lane_manifest_mismatch_is_detected(self) -> None:
        queue = {
            "workflow_path": "wrong.json",
            "text_to_image_workflow_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/text_to_image.api.json",
            "edit_workflow_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/single_reference_edit.api.json",
            "smoke_request_catalog_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/smoke_test_requests.json",
            "readme_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/README.md",
            "requirements_path": "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux2_klein_4b_distilled/runtime_requirements.json",
        }
        active = {
            "workflow": "Workflows/base_generation/flux2_klein_4b_distilled/workflow.api.json",
            "text_to_image_workflow": "Workflows/base_generation/flux2_klein_4b_distilled/text_to_image.api.json",
            "edit_workflow": "Workflows/base_generation/flux2_klein_4b_distilled/single_reference_edit.api.json",
            "smoke_request": "Workflows/base_generation/flux2_klein_4b_distilled/smoke_test_request.json",
            "smoke_request_catalog": "Workflows/base_generation/flux2_klein_4b_distilled/smoke_test_requests.json",
            "runtime_requirements": "Workflows/base_generation/flux2_klein_4b_distilled/runtime_requirements.json",
        }
        self.assertEqual(MODULE.lane_manifest_defects(queue, active), ["queue_workflow"])


if __name__ == "__main__":
    unittest.main()
