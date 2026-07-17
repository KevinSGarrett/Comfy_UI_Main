from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_scorecard_benchmark_release_slice.py"
SPEC = importlib.util.spec_from_file_location("wave64_scorecard_release", SCRIPT); assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = RUNTIME; SPEC.loader.exec_module(RUNTIME)


def registry(): return RUNTIME.load_json(ROOT / RUNTIME.DEFAULT_REGISTRY)
def schema(): return RUNTIME.load_json(ROOT / RUNTIME.DEFAULT_SCHEMA)
def fixture(): return RUNTIME.execute_fixture(registry())
def calibration(): return {"false_accept_rate": 0.01, "false_reject_rate": 0.04, "abstention_rate": 0.10}
def scopes(): return {scope: True for scope in RUNTIME.SCOPES}


def test_registry_and_sources_validate(): RUNTIME.validate_registry(ROOT, registry(), schema())
def test_fixture_covers_rows_and_stays_fail_closed():
    result = fixture(); assert result["rows_covered"] == [209, 210, 211, 212]; assert result["gate_count"] == 14; assert result["benchmark_fixture_count"] == 11; assert result["release_readiness"]["status"] == "blocked"; assert result["production_release_allowed"] is False
def test_exact_modular_gate_set_and_no_subjective_scalar():
    value = registry()["scorecard_contract"]; assert set(value["required_gate_ids"]) == RUNTIME.GATES; assert value["single_subjective_scalar_allowed"] is False
def test_every_gate_has_required_metadata():
    for gate in registry()["scorecard_contract"]["gates"]: assert gate["applicability_rule"] and gate["threshold"] and gate["method"] and gate["authority"] and gate["evidence_type"] and gate["severity"]


def test_source_hash_drift_rejected():
    value = registry(); value["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="bound_hash_mismatch:scorecard_rules"): RUNTIME.validate_registry(ROOT, value, schema())
def test_source_path_escape_rejected():
    value = registry(); value["source_authorities"][0]["path"] = "../outside.json"
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="bound_path_not_relative"): RUNTIME.validate_registry(ROOT, value, schema())
def test_duplicate_source_name_rejected():
    value = registry(); value["source_authorities"][1]["name"] = "scorecard_rules"
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="duplicate_source_authority_name"): RUNTIME.validate_registry(ROOT, value, schema())
def test_fixture_payload_mutation_rejected():
    value = registry(); value["benchmark_contract"]["fixtures"][0]["expected_decision"] = "block"
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="benchmark_fixture_hash_mismatch"): RUNTIME.validate_registry(ROOT, value, schema())
def test_benchmark_has_exact_buckets_and_all_cohorts():
    value = registry()["benchmark_contract"]; assert {item["bucket"] for item in value["fixtures"]} == RUNTIME.BUCKETS; assert {item["cohort"] for item in value["fixtures"]} == RUNTIME.COHORTS; assert all(item["held_out"] for item in value["fixtures"])


def test_positive_ensemble_allows_bounded_candidate(): assert fixture()["positive_decision"]["decision"] == "allow"
def test_hard_failure_cannot_be_overridden_by_allow_signals():
    decision = fixture()["hard_failure_decision"]; assert decision["decision"] == "block"; assert decision["reason"] == "HARD_GATE_FAILURE"; assert decision["hard_failures"] == ["anatomy"]
def test_disagreement_forces_abstention():
    decision = fixture()["disagreement_decision"]; assert decision["decision"] == "abstain"; assert decision["disagreement"] is True
def test_missing_applicability_rejected():
    results = RUNTIME.passing_gate_results(registry()); results["pose"].pop("applicable")
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="applicability_missing:pose"): RUNTIME.evaluate_ensemble(registry(), results, scopes(), RUNTIME.signals("allow"), calibration())
def test_not_applicable_requires_reason():
    results = RUNTIME.passing_gate_results(registry()); results["speech"] = {"applicable": False}
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="not_applicable_reason_missing:speech"): RUNTIME.evaluate_ensemble(registry(), results, scopes(), RUNTIME.signals("allow"), calibration())
def test_not_applicable_with_reason_is_accepted():
    results = RUNTIME.passing_gate_results(registry()); results["speech"] = {"applicable": False, "not_applicable_reason": "no_speech"}
    assert RUNTIME.evaluate_ensemble(registry(), results, scopes(), RUNTIME.signals("allow"), calibration())["decision"] == "allow"
def test_all_target_protected_and_whole_scopes_required():
    value = scopes(); value["protected"] = False
    decision = RUNTIME.evaluate_ensemble(registry(), RUNTIME.passing_gate_results(registry()), value, RUNTIME.signals("allow"), calibration()); assert decision["reason"] == "SCOPED_GATE_FAILURE"; assert decision["failed_scopes"] == ["protected"]
def test_exact_signal_type_set_required():
    signals = RUNTIME.signals("allow"); signals.pop()
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="runtime_signal_type_set_mismatch"): RUNTIME.evaluate_ensemble(registry(), RUNTIME.passing_gate_results(registry()), scopes(), signals, calibration())
@pytest.mark.parametrize("name,limit", [("false_accept_rate", 0.02), ("false_reject_rate", 0.10), ("abstention_rate", 0.25)])
def test_calibration_limits_fail_closed(name, limit):
    value = calibration(); value[name] = limit + 0.01
    assert RUNTIME.evaluate_ensemble(registry(), RUNTIME.passing_gate_results(registry()), scopes(), RUNTIME.signals("allow"), value)["reason"] == "CALIBRATION_LIMIT_EXCEEDED"


def test_current_release_is_blocked_on_rows_and_certificates():
    result = fixture()["release_readiness"]; assert result["missing_rows"] == list(range(213, 221)); assert result["missing_certificates"] == ["promotion", "quality", "release", "runtime"]; assert result["promotion_request_eligible"] is False; assert result["certificate_issued"] is False
def test_complete_rows_and_certificates_can_only_make_projection_eligible():
    ready = RUNTIME.release_readiness(registry(), fixture()["positive_decision"], set(range(149, 221)), {name: True for name in registry()["release_policy"]["required_certificates"]}); assert ready["status"] == "eligible"; assert ready["projection_only"] is True; assert ready["actual_promotion_state"] == "not_requested"; assert ready["certificate_issued"] is False
def test_non_allow_ensemble_blocks_even_with_all_rows_and_certificates():
    ready = RUNTIME.release_readiness(registry(), fixture()["disagreement_decision"], set(range(149, 221)), {name: True for name in registry()["release_policy"]["required_certificates"]}); assert ready["status"] == "blocked"; assert "ensemble:abstain" in ready["blockers"]
def test_false_boundary_rejected():
    value = registry(); value["boundaries"]["certificate_issued"] = True
    with pytest.raises(RUNTIME.ReleaseAuthorityError, match="schema_validation_failed"): RUNTIME.validate_registry(ROOT, value, schema())
def test_evidence_is_mirrorable_and_records_worker_boundary(tmp_path):
    evidence = RUNTIME.build_evidence(ROOT, fixture(), RUNTIME.DEFAULT_REGISTRY, RUNTIME.DEFAULT_SCHEMA); qa = tmp_path / "qa.json"; tracker = tmp_path / "tracker.json"; RUNTIME.write_json(qa, evidence); RUNTIME.write_json(tracker, evidence); assert qa.read_bytes() == tracker.read_bytes(); assert evidence["worker_dispatch"]["result"] == "AI_WORKER_RETRY_BUDGET_EXHAUSTED_REGISTERED_PRIMARY_WORKTREE_REQUIRED"; assert not any(evidence["boundaries"].values())
