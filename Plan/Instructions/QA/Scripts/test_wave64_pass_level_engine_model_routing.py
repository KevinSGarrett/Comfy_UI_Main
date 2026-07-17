#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_pass_level_engine_model_routing.py"
SPEC = importlib.util.spec_from_file_location("wave64_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class Wave64RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schemas, cls.registry = VALIDATOR.load_contracts(PROJECT_ROOT)
        cls.single = json.loads((PROJECT_ROOT / "Plan/08_SCHEMAS/examples/wave64_single_character_flux_to_sdxl_specialist.example.json").read_text(encoding="utf-8"))
        cls.multi = json.loads((PROJECT_ROOT / "Plan/08_SCHEMAS/examples/wave64_two_character_ownership_and_mask_binding.example.json").read_text(encoding="utf-8"))
        _, cls.stack_authority = VALIDATOR.validate_registry(
            PROJECT_ROOT, cls.schemas, cls.registry
        )

    def test_full_validator_passes(self) -> None:
        result = VALIDATOR.validate_all(PROJECT_ROOT)
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["runtime_completion_claimed"])
        self.assertEqual(result["preserved_paths_verified"], 49)
        self.assertEqual(result["missing_baseline_references"], 2)

    def test_ineligible_candidate_cannot_be_ranked(self) -> None:
        decision = copy.deepcopy(self.single["route_decision"])
        candidate = next(entry for entry in decision["evaluated_candidates"] if not entry["eligible"])
        candidate["rank_score"] = 0.99
        with self.assertRaises(VALIDATOR.ValidationFailure):
            VALIDATOR.validate_route_decision(decision, "negative")

    def test_selected_stack_must_have_passed_hard_filter(self) -> None:
        decision = copy.deepcopy(self.single["route_decision"])
        decision["selected_execution_stack_id"] = "stack_unverified_similarly_named_hand_model"
        with self.assertRaises(VALIDATOR.ValidationFailure):
            VALIDATOR.validate_route_decision(decision, "negative")

    def test_planned_stack_cannot_self_declare_eligibility(self) -> None:
        decision = copy.deepcopy(self.single["route_decision"])
        candidate = decision["evaluated_candidates"][0]
        candidate["eligible"] = True
        candidate["rank_score"] = 0.99
        decision["ranked_eligible_stack_ids"] = [candidate["execution_stack_id"]]
        decision["decision_status"] = "selected"
        decision["selected_execution_stack_id"] = candidate["execution_stack_id"]
        with self.assertRaises(VALIDATOR.ValidationFailure):
            VALIDATOR.validate_route_decision(
                decision, "negative", self.stack_authority
            )

    def test_cross_engine_latent_transfer_is_rejected(self) -> None:
        bridge = copy.deepcopy(self.single["bridge_contract"])
        bridge["transfer_objects"][0]["transfer_type"] = "cross_family_latent"
        with self.assertRaises(VALIDATOR.ValidationFailure):
            VALIDATOR.validate_bridge(bridge, "negative")

    def test_uncertified_bridge_cannot_execute(self) -> None:
        bridge = copy.deepcopy(self.single["bridge_contract"])
        bridge["bridge_status"] = "validated"
        bridge["execution_allowed"] = True
        schema = self.schemas["cross_engine_bridge_contract.schema.json"]
        errors = list(VALIDATOR.validator(schema, self.registry).iter_errors(bridge))
        self.assertTrue(errors)

    def test_certified_bridge_requires_compatibility_certificate(self) -> None:
        bridge = copy.deepcopy(self.single["bridge_contract"])
        bridge["bridge_status"] = "certified"
        bridge["execution_allowed"] = True
        bridge["compatibility_certificate_id"] = None
        schema = self.schemas["cross_engine_bridge_contract.schema.json"]
        errors = list(VALIDATOR.validator(schema, self.registry).iter_errors(bridge))
        self.assertTrue(errors)

    def test_mode_b_is_draft_only(self) -> None:
        binding = copy.deepcopy(self.multi["mask_bindings"][0])
        binding["access_mode"] = "mode_b_live_predict"
        binding["authority"]["truth_tier"] = "approved_package"
        binding["can_satisfy_promotion_gate"] = True
        schema = self.schemas["mask_factory_binding.schema.json"]
        errors = list(VALIDATOR.validator(schema, self.registry).iter_errors(binding))
        self.assertTrue(errors)

    def test_mode_a_promotion_requires_certificate(self) -> None:
        binding = copy.deepcopy(self.multi["mask_bindings"][0])
        binding["authority"]["certificate_id"] = None
        binding["can_satisfy_promotion_gate"] = True
        schema = self.schemas["mask_factory_binding.schema.json"]
        errors = list(VALIDATOR.validator(schema, self.registry).iter_errors(binding))
        self.assertTrue(errors)

    def test_wrong_person_crosswalk_is_detectable(self) -> None:
        package = self.multi["shot_pose_package"]
        bindings = copy.deepcopy(self.multi["mask_bindings"])
        bindings[1]["person_index"] = 0
        expected = {(entry["character_instance_id"], entry["person_index"]) for entry in package["instances"]}
        actual = {(entry["character_instance_id"], entry["person_index"]) for entry in bindings}
        self.assertNotEqual(actual, expected)

    def test_provider_person_index_and_render_order_are_semantically_unique(self) -> None:
        package = copy.deepcopy(self.multi["shot_pose_package"])
        package["instances"][1]["mask_provider_person_index"] = 0
        with self.assertRaises(VALIDATOR.ValidationFailure):
            VALIDATOR.validate_shot_pose_semantics(package, "negative")

    def test_contact_unknown_owner_is_rejected(self) -> None:
        package = copy.deepcopy(self.multi["shot_pose_package"])
        package["contacts"][0]["participants"][1]["owner_instance_id"] = "unknown"
        with self.assertRaises(VALIDATOR.ValidationFailure):
            VALIDATOR.validate_shot_pose_semantics(package, "negative")

    def test_missing_route_field_fails_schema(self) -> None:
        request = copy.deepcopy(self.single["route_request"])
        del request["registry_snapshot_id"]
        schema = self.schemas["multimodal_pass_route_request.schema.json"]
        errors = list(VALIDATOR.validator(schema, self.registry).iter_errors(request))
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
