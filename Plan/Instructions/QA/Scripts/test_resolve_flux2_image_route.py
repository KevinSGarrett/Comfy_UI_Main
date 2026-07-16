from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/resolve_flux2_image_route.py"
SPEC = importlib.util.spec_from_file_location("resolve_flux2_image_route", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Flux2ImageRouteTests(unittest.TestCase):
    def test_missing_proof_fails_closed(self) -> None:
        result = MODULE.select_route("text_to_image", None)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["selected_lane"])

    def test_one_capability_cannot_promote_the_other(self) -> None:
        proof = {
            "lane_id": MODULE.KLEIN_LANE,
            "production_ready": False,
            "capabilities": {
                "text_to_image": {
                    "runtime_pass": True,
                    "artifact_hash_bound": True,
                    "direct_visual_qa_pass": True,
                    "workflow_path": "t2i.json",
                }
            },
        }
        self.assertEqual(MODULE.select_route("single_reference_edit", proof)["status"], "BLOCKED")

    def test_complete_capability_selects_bounded_lane(self) -> None:
        proof = {
            "lane_id": MODULE.KLEIN_LANE,
            "production_ready": False,
            "capabilities": {
                "single_reference_edit": {
                    "runtime_pass": True,
                    "artifact_hash_bound": True,
                    "direct_visual_qa_pass": True,
                    "workflow_path": "edit.json",
                }
            },
        }
        result = MODULE.select_route("single_reference_edit", proof)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["production_ready"])

    def test_production_ready_claim_is_rejected(self) -> None:
        proof = {
            "lane_id": MODULE.KLEIN_LANE,
            "production_ready": True,
            "capabilities": {
                "text_to_image": {
                    "runtime_pass": True,
                    "artifact_hash_bound": True,
                    "direct_visual_qa_pass": True,
                }
            },
        }
        self.assertEqual(MODULE.select_route("text_to_image", proof)["status"], "BLOCKED")

    def test_unknown_capability_is_rejected(self) -> None:
        result = MODULE.select_route("multi_reference_edit", {})
        self.assertEqual(result["classification"], "BLOCKED_FLUX2_CAPABILITY_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
