from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_durable_controller_runtime_slice.py"
SPEC = importlib.util.spec_from_file_location("wave64_durable_controller_runtime", SCRIPT)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


def registry():
    return RUNTIME.load_json(ROOT / RUNTIME.DEFAULT_REGISTRY)


def schema():
    return RUNTIME.load_json(ROOT / RUNTIME.DEFAULT_SCHEMA)


def run_fixture(tmp_path):
    return RUNTIME.execute_fixture(tmp_path / "controller.sqlite3")


def test_registry_and_bound_sources_validate():
    RUNTIME.validate_registry(ROOT, registry(), schema())


def test_runtime_fixture_passes_all_bounded_invariants(tmp_path):
    result = run_fixture(tmp_path)
    assert result["classification"] == "WAVE64_DURABLE_CONTROLLER_RUNTIME_SLICE_PASS"
    assert result["rows_covered"] == [197, 198, 199, 200]
    assert result["hash_chain_valid"] is True
    assert result["replay_projection_matches"] is True
    assert result["promotion_exactly_once"] is True
    assert result["service_authority_chain_complete"] is True
    assert result["production_runtime_allowed"] is False


def test_service_record_ownership_is_exclusive():
    candidate = registry()
    candidate["service_separation"][1]["owns_records"] = ["plan_proposal"]
    with pytest.raises(RUNTIME.ControllerRuntimeError, match="record_has_multiple_service_owners"):
        RUNTIME.validate_registry(ROOT, candidate, schema())


def test_runtime_rejects_service_assuming_another_authority(tmp_path):
    controller = RUNTIME.DurableController(tmp_path / "db.sqlite3")
    try:
        controller.create_run("run_a")
        with pytest.raises(RUNTIME.ControllerRuntimeError, match="service_record_owner_mismatch:qa_policy_decision:planner"):
            controller.record_service_decision("run_a", "bad", "planner", "qa_policy_decision", "authorized", "forbidden")
    finally:
        controller.close()


def test_source_hash_drift_fails_closed():
    candidate = registry(); candidate["source_authorities"][0]["sha256"] = "0" * 64
    with pytest.raises(RUNTIME.ControllerRuntimeError, match="bound_hash_mismatch:controller_contract_registry"):
        RUNTIME.validate_registry(ROOT, candidate, schema())


def test_source_path_escape_fails_closed():
    candidate = registry(); candidate["source_authorities"][0]["path"] = "../outside.json"
    with pytest.raises(RUNTIME.ControllerRuntimeError, match="bound_path_not_relative:controller_contract_registry"):
        RUNTIME.validate_registry(ROOT, candidate, schema())


def test_duplicate_source_name_fails_closed():
    candidate = registry(); candidate["source_authorities"][6]["name"] = "worker_lease_schema"
    with pytest.raises(RUNTIME.ControllerRuntimeError, match="duplicate_source_authority_name"):
        RUNTIME.validate_registry(ROOT, candidate, schema())


def test_optimistic_version_rejects_concurrent_write(tmp_path):
    controller = RUNTIME.DurableController(tmp_path / "db.sqlite3")
    try:
        controller.create_run("run_a")
        with pytest.raises(RUNTIME.ControllerRuntimeError, match="optimistic_aggregate_version_mismatch"):
            controller.append_event("run_a", "bad", {"to_state": "bad"}, expected_version=0)
    finally:
        controller.close()


def test_event_hash_chain_detects_tampering(tmp_path):
    path = tmp_path / "db.sqlite3"
    controller = RUNTIME.DurableController(path)
    try:
        controller.create_run("run_a")
        controller.connection.execute("UPDATE events SET payload_json='{}'")
        controller.connection.commit()
        assert controller.verify_hash_chain("run_a") is False
    finally:
        controller.close()


def test_scheduler_unlocks_child_only_after_parent_acceptance(tmp_path):
    result = run_fixture(tmp_path)
    assert result["initial_ready_passes"] == ["pass_root"]
    assert result["ready_after_parent_acceptance"] == ["pass_child"]


def test_duplicate_submission_reuses_original_attempt(tmp_path):
    assert run_fixture(tmp_path)["duplicate_submission_returned_original_attempt"] is True


def test_fencing_tokens_are_monotonic_and_stale_worker_is_rejected(tmp_path):
    result = run_fixture(tmp_path)
    assert result["fencing_tokens_monotonic"] is True
    assert result["stale_fence_rejected"] is True


def test_ambiguous_attempt_blocks_cross_host_failover(tmp_path):
    result = run_fixture(tmp_path)
    assert result["ambiguous_cross_host_failover_allowed"] is False
    assert result["counts"]["blockers"] == 1


def test_accepted_parent_remains_immutable_after_retry(tmp_path):
    assert run_fixture(tmp_path)["accepted_parent_preserved"] is True


def test_promotion_is_exactly_once(tmp_path):
    result = run_fixture(tmp_path)
    assert result["promotion_exactly_once"] is True
    assert result["counts"]["promotions"] == 1
    assert result["counts"]["service_records"] == 8


def test_promotion_requires_separate_qa_and_policy_authority(tmp_path):
    controller = RUNTIME.DurableController(tmp_path / "db.sqlite3")
    artifact_hash = "a" * 64
    try:
        controller.create_run("run_a")
        controller.add_pass("run_a", "pass_a")
        controller.connection.execute("UPDATE passes SET status='accepted', accepted_artifact_hash=? WHERE pass_id='pass_a'", (artifact_hash,))
        controller.connection.commit()
        with pytest.raises(RUNTIME.ControllerRuntimeError, match="promotion_preconditions_not_met"):
            controller.promote("run_a", "promotion_bad", "promote:bad", artifact_hash)
    finally:
        controller.close()


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        ({"submitted": True, "receipt": False}, "ambiguous_submission"),
        ({"receipt": True, "output": False}, "missing_output"),
        ({"output": True, "receipt": False}, "orphan_output"),
        ({"stale_lease": True}, "stale_lease"),
        ({"duplicate_idempotency": True}, "duplicate_delivery"),
        ({"conflicting_hashes": True}, "conflicting_artifact"),
    ],
)
def test_recovery_classifier_has_typed_fail_closed_results(observation, expected):
    assert RUNTIME.classify_recovery(observation) == expected


def test_recovery_classifier_rejects_ambiguous_multi_class_observation():
    with pytest.raises(RUNTIME.ControllerRuntimeError, match="recovery_observation_not_exactly_classifiable"):
        RUNTIME.classify_recovery({"stale_lease": True, "duplicate_idempotency": True})


def test_production_and_external_boundaries_remain_false(tmp_path):
    result = run_fixture(tmp_path)
    assert result["comfyui_submission_performed"] is False
    assert result["media_generated"] is False
    assert result["promotion_to_production_performed"] is False


def test_evidence_outputs_are_exact_mirrors(tmp_path):
    result = run_fixture(tmp_path)
    evidence = RUNTIME.build_evidence(ROOT, result, RUNTIME.DEFAULT_REGISTRY, RUNTIME.DEFAULT_SCHEMA)
    qa, tracker = tmp_path / "qa.json", tmp_path / "tracker.json"
    RUNTIME.write_json(qa, evidence); RUNTIME.write_json(tracker, evidence)
    assert qa.read_bytes() == tracker.read_bytes()
    assert not any(evidence["boundaries"].values())


def test_database_has_foreign_key_integrity(tmp_path):
    controller = RUNTIME.DurableController(tmp_path / "db.sqlite3")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            controller.connection.execute("INSERT INTO passes VALUES ('orphan', 'missing', NULL, 'planned', NULL)")
    finally:
        controller.close()
