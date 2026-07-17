from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/solve_wave64_fail_closed_route.py"
SPEC = importlib.util.spec_from_file_location("wave64_fail_closed_route_solver", SCRIPT)
assert SPEC and SPEC.loader
SOLVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SOLVER
SPEC.loader.exec_module(SOLVER)


def fixture():
    return SOLVER.load_json(ROOT / SOLVER.DEFAULT_FIXTURE)


def fixture_schema():
    return SOLVER.load_json(ROOT / SOLVER.DEFAULT_FIXTURE_SCHEMA)


def sources(candidate=None):
    candidate = candidate or fixture()
    activation = SOLVER.load_bound_source(ROOT, candidate["source_registries"]["activation_gate"], "activation_gate")
    capabilities = SOLVER.load_bound_source(ROOT, candidate["source_registries"]["capability_registry"], "capability_registry")
    return activation, capabilities


def solve(candidate=None):
    return SOLVER.validate_all(ROOT, candidate or fixture(), fixture_schema())


def test_live_fixture_abstains_without_ranking_or_execution():
    result = solve()
    assert result["classification"] == "WAVE64_FAIL_CLOSED_ROUTE_SOLVER_SLICE_PASS"
    assert result["rows_covered"] == [164, 165, 166, 167, 168]
    assert result["capability_card_count"] == 10
    assert result["execution_stack_count"] == 4
    assert result["unstacked_capability_card_count"] == 6
    assert result["eligible_stack_count"] == 0
    assert result["ranked_stack_count"] == 0
    assert result["llm_proposal_invoked"] is False
    assert result["runtime_execution_allowed"] is False


def test_activation_gate_source_hash_is_immutable():
    candidate = fixture()
    candidate["source_registries"]["activation_gate"]["sha256"] = "0" * 64
    with pytest.raises(SOLVER.RouteSolverError, match="source_hash_mismatch:activation_gate"):
        solve(candidate)


def test_capability_registry_source_hash_is_immutable():
    candidate = fixture()
    candidate["source_registries"]["capability_registry"]["sha256"] = "0" * 64
    with pytest.raises(SOLVER.RouteSolverError, match="source_hash_mismatch:capability_registry"):
        solve(candidate)


def test_source_paths_cannot_escape_project():
    candidate = fixture()
    candidate["source_registries"]["activation_gate"]["path"] = "../outside.json"
    with pytest.raises(SOLVER.RouteSolverError, match="source_path_not_bounded_relative"):
        solve(candidate)


def test_conformance_gate_requires_pose_framing_ownership_contact_and_protection():
    candidate = fixture()
    candidate["conformance_gate"]["required_checks"].remove("ownership")
    with pytest.raises(SOLVER.RouteSolverError, match="schema_validation_failed:solver_fixture"):
        solve(candidate)


def test_conformance_gate_blocks_without_runtime_output():
    result = solve()
    conformance = result["conformance_decision"]
    assert conformance["status"] == "blocked_missing_runtime_output"
    assert conformance["promotion_allowed"] is False
    assert all(check["status"] == "not_run" for check in conformance["checks"])


def test_all_capability_cards_validate_against_adopted_schema():
    _, capabilities = sources()
    card_schema = SOLVER.load_json(ROOT / SOLVER.CAPABILITY_CARD_SCHEMA)
    for index, card in enumerate(capabilities["capability_cards"]):
        SOLVER.validate_schema(card, card_schema, f"card.{index}")


def test_duplicate_capability_card_id_fails_closed():
    activation, capabilities = sources()
    capabilities["capability_cards"][1]["capability_card_id"] = capabilities["capability_cards"][0]["capability_card_id"]
    with pytest.raises(SOLVER.RouteSolverError, match="duplicate_capability_card_id"):
        SOLVER.evaluate_candidates(capabilities, fixture()["route_request"], activation, fixture()["hard_constraints"])


def test_stack_must_reference_known_capability_card():
    activation, capabilities = sources()
    capabilities["execution_stack_templates"][0]["capability_card_id"] = "missing_card"
    with pytest.raises(SOLVER.RouteSolverError, match="stack_capability_card_unknown"):
        SOLVER.evaluate_candidates(capabilities, fixture()["route_request"], activation, fixture()["hard_constraints"])


def test_stack_engine_family_must_match_capability_card():
    activation, capabilities = sources()
    capabilities["execution_stack_templates"][0]["engine_family"] = "wrong_engine"
    with pytest.raises(SOLVER.RouteSolverError, match="stack_engine_family_mismatch"):
        SOLVER.evaluate_candidates(capabilities, fixture()["route_request"], activation, fixture()["hard_constraints"])


def test_flux_candidate_reports_every_current_hard_blocker_category():
    result = solve()
    flux = next(
        candidate for candidate in result["route_decision"]["evaluated_candidates"]
        if candidate["execution_stack_id"] == "stack_template_flux2_dev_global_v1"
    )
    required = {
        "MODEL_LIBRARY_ACTIVATION_GATE_CLOSED",
        "STACK_AUTHORITY_NOT_CERTIFIED",
        "EXACT_MODEL_HASH_MISSING",
        "CERTIFIED_RUNTIME_ENVELOPE_MISSING",
        "CERTIFIED_BENCHMARK_BUCKET_MISSING",
        "HASHED_API_WORKFLOW_MISSING",
        "STACK_COMPONENT_HASH_MISSING",
        "CUSTOM_NODE_LOCK_MISSING",
        "LICENSE_USE_RECORD_MISSING_OR_MISMATCHED",
        "HARDWARE_ENVELOPE_INCOMPATIBLE",
    }
    assert required.issubset(set(flux["eligibility_reasons"]))


def test_incompatible_specialist_reports_component_family_constraints():
    result = solve()
    sdxl = next(
        candidate for candidate in result["route_decision"]["evaluated_candidates"]
        if candidate["execution_stack_id"] == "stack_template_sdxl_regional_specialist_v1"
    )
    assert {
        "ENGINE_FAMILY_INCOMPATIBLE",
        "VAE_FAMILY_INCOMPATIBLE",
        "TEXT_ENCODER_FAMILY_INCOMPATIBLE",
        "ADAPTER_FAMILY_INCOMPATIBLE",
        "CONTROL_FAMILY_INCOMPATIBLE",
        "WORKFLOW_MODULE_INCOMPATIBLE",
    }.issubset(set(sdxl["eligibility_reasons"]))


def test_required_package_contract_loss_is_typed_before_ranking():
    candidate = fixture()
    candidate["route_request"]["input_contract"].remove("character_package")
    activation, capabilities = sources(candidate)
    evaluations, _ = SOLVER.evaluate_candidates(
        capabilities, candidate["route_request"], activation, candidate["hard_constraints"]
    )
    assert all("REQUIRED_PACKAGE_CONTRACT_MISSING" in entry["eligibility_reasons"] for entry in evaluations)


def test_undeclared_required_capability_is_typed_before_ranking():
    candidate = fixture()
    candidate["route_request"]["required_capabilities"].append("undeclared_capability")
    activation, capabilities = sources(candidate)
    evaluations, _ = SOLVER.evaluate_candidates(
        capabilities, candidate["route_request"], activation, candidate["hard_constraints"]
    )
    assert all("REQUIRED_CAPABILITY_UNSATISFIED" in entry["eligibility_reasons"] for entry in evaluations)


def test_license_policy_checks_exact_record_not_noncommercial_label():
    result = solve()
    reasons = {reason for candidate in result["route_decision"]["evaluated_candidates"] for reason in candidate["eligibility_reasons"]}
    assert "LICENSE_USE_RECORD_MISSING_OR_MISMATCHED" in reasons
    assert not any("NON_COMMERCIAL" in reason for reason in reasons)


def test_no_ineligible_candidate_receives_score_or_rank_components():
    decision = solve()["route_decision"]
    assert all(candidate["eligible"] is False for candidate in decision["evaluated_candidates"])
    assert all(candidate["rank_score"] is None for candidate in decision["evaluated_candidates"])
    assert all(candidate["rank_components"] == {} for candidate in decision["evaluated_candidates"])


def test_route_decision_is_schema_valid_typed_abstention():
    decision = solve()["route_decision"]
    assert decision["decision_status"] == "blocked_no_eligible_stack"
    assert decision["selected_execution_stack_id"] is None
    assert decision["ranked_eligible_stack_ids"] == []
    assert {blocker["blocker_type"] for blocker in decision["blockers"]} == {
        "MODEL_LIBRARY_ACTIVATION_GATE_CLOSED", "NO_CERTIFIED_EXECUTION_STACK"
    }


def test_request_constraint_hash_is_replayable():
    candidate = fixture()
    decision = solve(candidate)["route_decision"]
    assert decision["request_constraints_sha256"] == SOLVER.canonical_sha256(candidate["route_request"])


def test_llm_cannot_bypass_hard_filters():
    candidate = fixture()
    candidate["ranking_policy"]["llm_can_bypass_hard_filters"] = True
    with pytest.raises(SOLVER.RouteSolverError, match="schema_validation_failed:solver_fixture"):
        solve(candidate)


def test_silent_substitution_and_seed_only_retry_remain_forbidden():
    candidate = fixture()
    candidate["fallback_policy"]["silent_substitution_allowed"] = True
    with pytest.raises(SOLVER.RouteSolverError, match="schema_validation_failed:solver_fixture"):
        solve(candidate)
    candidate = fixture()
    candidate["fallback_policy"]["seed_only_retry_allowed"] = True
    with pytest.raises(SOLVER.RouteSolverError, match="schema_validation_failed:solver_fixture"):
        solve(candidate)


def test_route_fallback_preserves_accepted_parent_and_waits_for_activation():
    decision = solve()["route_decision"]
    assert decision["fallback_sequence"] == [
        "abstain_preserve_accepted_parent", "wait_for_explicit_model_library_activation"
    ]
    assert decision["prohibited_substitutions"]["component_substitution"] == "forbidden"


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    result = solve()
    evidence = SOLVER.build_evidence(ROOT, result, SOLVER.DEFAULT_FIXTURE, SOLVER.DEFAULT_FIXTURE_SCHEMA)
    qa = tmp_path / "qa.json"
    tracker = tmp_path / "tracker.json"
    SOLVER.write_json(qa, evidence)
    SOLVER.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert evidence["boundaries"]["model_library_gate_changed"] is False
    assert evidence["boundaries"]["ranking_executed"] is False
