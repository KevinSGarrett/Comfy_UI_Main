from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[4]
BUILDER = (
    ROOT
    / "Plan"
    / "07_IMPLEMENTATION"
    / "scripts"
    / "build_wave64_autonomous_model_intelligence_control_package.py"
)


def load_builder():
    spec = importlib.util.spec_from_file_location("wave64_model_intelligence_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def schema_registry(builder):
    schemas = builder.build_schemas()
    resources = [
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
    ]
    return schemas, Registry().with_resources(resources)


def immutable_ref(record_type: str, record_id: str):
    return {
        "schema_id": "https://comfy-ui-main.local/schemas/test/1.0.0",
        "record_type": record_type,
        "record_id": record_id,
        "revision": "1",
        "sha256": "0" * 64,
        "bytes": 1,
        "path_or_uri": "registry://%s/%s/1" % (record_type, record_id),
    }


def test_builder_check_is_clean():
    result = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"runtime_completion_claimed": false' in result.stdout


def test_generated_rows_are_checkout_location_independent(tmp_path):
    builder = load_builder()
    original_root = builder.ROOT
    try:
        builder.ROOT = tmp_path / "first-checkout"
        first_outputs = builder.build_expected_outputs()
        builder.ROOT = tmp_path / "nested" / "second-checkout"
        second_outputs = builder.build_expected_outputs()
    finally:
        builder.ROOT = original_root

    assert first_outputs == second_outputs
    item_path = "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_ITEM_ROWS.csv"
    first_item = next(csv.DictReader(first_outputs[item_path].decode("utf-8").splitlines()))
    assert first_item["Citation_Full_Path"].startswith(r"C:\Comfy_UI_Main\Plan" + "\\")


def test_rows_are_contiguous_unique_and_four_per_workstream():
    builder = load_builder()
    numbers = [row.number for row in builder.ROWS]
    assert numbers == list(range(221, 261))
    assert len(set(numbers)) == 40
    counts = Counter(row.workstream for row in builder.ROWS)
    assert len(counts) == 10
    assert set(counts.values()) == {4}


def test_item_and_tracker_sidecars_cover_every_row():
    item_path = (
        ROOT
        / "Plan/Items/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_ITEM_ROWS.csv"
    )
    tracker_path = (
        ROOT
        / "Plan/Tracker/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_TRACKER_ROWS.csv"
    )
    with item_path.open(encoding="utf-8", newline="") as handle:
        items = list(csv.DictReader(handle))
    with tracker_path.open(encoding="utf-8", newline="") as handle:
        trackers = list(csv.DictReader(handle))
    assert len(items) == 40
    assert len(trackers) == 40
    assert {row["Item_ID"] for row in items} == {
        "W64-MI-%03d" % number for number in range(221, 261)
    }
    assert {row["Source_Item_ID"] for row in trackers} == {
        "W64-MI-%03d" % number for number in range(221, 261)
    }
    item_by_id = {row["Item_ID"]: row for row in items}
    tracker_by_id = {row["Source_Item_ID"]: row for row in trackers}
    for number in (221, 222):
        item_id = "W64-MI-%03d" % number
        assert item_by_id[item_id]["Status"] == "Planned_Static_Control_Allowed_Pre_Activation"
        assert tracker_by_id[item_id]["Status"] == "Planned_Static_Control_Allowed_Pre_Activation"
    deferred = (
        "Deferred_Pending_Complete_Model_Library_Download_Inventory_Verification_"
        "And_Main_Task_Acknowledgement"
    )
    for number in range(223, 261):
        item_id = "W64-MI-%03d" % number
        assert item_by_id[item_id]["Status"] == deferred
        assert tracker_by_id[item_id]["Status"] == deferred
        assert "ActivationGate=" in tracker_by_id[item_id]["Dependency_Prerequisite"]


def test_requirement_mirrors_are_identical_and_planning_only():
    item_req = ROOT / (
        "Plan/Items/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_REQUIREMENTS.json"
    )
    tracker_req = ROOT / (
        "Plan/Tracker/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_REQUIREMENTS.json"
    )
    assert item_req.read_bytes() == tracker_req.read_bytes()
    data = json.loads(item_req.read_text(encoding="utf-8"))
    assert data["runtime_completion_claimed"] is False
    assert data["runtime_execution_allowed"] is False
    assert data["activation_gate_state"] == "deferred_waiting_for_complete_model_download"
    assert data["content_based_suppression"] is False
    assert len(data["requirements"]) == 40
    assert [row["row"] for row in data["requirements"]] == list(range(221, 261))
    by_row = {row["row"]: row for row in data["requirements"]}
    assert all(
        by_row[number]["runtime_truth"] == "not_started_static_control_allowed"
        and by_row[number]["activation_gate_required"] is False
        for number in (221, 222)
    )
    assert all(
        by_row[number]["runtime_truth"] == "deferred_prerequisites_not_satisfied"
        and by_row[number]["activation_gate_required"] is True
        and by_row[number]["execution_authorized"] is False
        for number in range(223, 261)
    )


def test_all_schemas_are_valid_and_have_unique_ids():
    builder = load_builder()
    schemas = builder.build_schemas()
    assert len(schemas) >= 25
    ids = []
    for name, schema in schemas.items():
        jsonschema.Draft202012Validator.check_schema(schema)
        ids.append(schema["$id"])
        if name != "model_intelligence_common.schema.json":
            assert schema["additionalProperties"] is False
            assert schema["properties"]["schema_version"]["const"] == "1.0.0"
            assert "record_type" in schema["required"]
            assert "provenance" in schema["required"]
    assert len(ids) == len(set(ids))


def test_examples_validate_against_record_schemas():
    builder = load_builder()
    schemas = builder.build_schemas()
    common = schemas["model_intelligence_common.schema.json"]
    resources = [(common["$id"], Resource.from_contents(common))]
    by_record_type = {}
    for schema in schemas.values():
        record_type = schema.get("properties", {}).get("record_type", {}).get("const")
        if record_type:
            by_record_type[record_type] = schema
            resources.append((schema["$id"], Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    for name, example in builder.build_examples().items():
        schema = by_record_type[example["record_type"]]
        validator = jsonschema.Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))
        assert not errors, name + ": " + "; ".join(error.message for error in errors)


def test_source_snapshot_is_discovery_only_and_hash_bound():
    snapshot = read_json(
        "Plan/10_REGISTRIES/wave64_wave30_model_os_source_snapshot.json"
    )
    schema = read_json("Plan/08_SCHEMAS/model_library_source_snapshot.schema.json")
    common = read_json("Plan/08_SCHEMAS/model_intelligence_common.schema.json")
    registry = Registry().with_resources([
        (common["$id"], Resource.from_contents(common)),
        (schema["$id"], Resource.from_contents(schema)),
    ])
    jsonschema.Draft202012Validator(schema, registry=registry).validate(snapshot)
    assert snapshot["logical_archive"]["zip_entries"] == 675
    assert snapshot["inventory"]["artifact_rows"] == 7282
    assert snapshot["inventory"]["model_family_rows"] == 3770
    assert snapshot["inventory"]["model_binary_count"] == 0
    assert snapshot["inventory"]["all_artifact_qa_status"] == "open"
    assert snapshot["authority"]["maximum"] == "discovery_metadata"
    assert snapshot["authority"]["runtime_selection_allowed"] is False
    assert snapshot["authority"]["promotion_allowed"] is False
    assert snapshot["authority"]["activation_gate_id"] == (
        "wave64_model_library_download_readiness_gate_v1"
    )
    assert snapshot["authority"]["complete_model_download_declared"] is False
    assert snapshot["authority"]["complete_binary_inventory_verified"] is False
    assert snapshot["authority"]["main_task_activation_acknowledged"] is False
    assert snapshot["authority"]["bulk_ingestion_or_qualification_allowed"] is False
    assert len(snapshot["parts"]) == 5
    assert snapshot["logical_archive"]["sha256"] == (
        "ab87f86c120085834d86b004e886e733a383ac9246f5f0f34087b6627d373351"
    )


def test_ranking_policy_is_hard_filtered_conservative_and_replayable():
    policy = read_json(
        "Plan/10_REGISTRIES/"
        "wave64_model_selection_feature_and_ranking_policy_registry.json"
    )
    assert policy["source_metadata_role"] == "discovery_and_qualification_priority_only"
    assert policy["hard_filter_order"][0] == "lifecycle_and_binary_integrity"
    assert "lower_confidence_bound" in policy["formula"]["quality"]
    assert "upper_confidence_bound" in policy["formula"]["risk"]
    assert policy["formula"]["composite_applied_after"] == "pareto_frontier"
    assert policy["cold_start"]["metadata_priors_production_quality_authority"] is False
    assert policy["exploration"]["accepted_parent_mutation"] is False
    assert policy["exploration"]["single_success_promotion"] is False
    assert {
        "selection_context_hash",
        "registry_snapshot_ids",
        "certificate_snapshot_ids",
        "feature_snapshot_hash",
        "ranking_policy_id",
        "normalization_and_weight_policy_id",
    } == set(policy["replay_requirements"])


def test_role_registry_has_no_execution_or_promotion_authority():
    roles = read_json(
        "Plan/10_REGISTRIES/wave64_autonomous_model_role_registry.json"
    )
    assert roles["status"] == "roles_defined_stacks_unselected_unqualified_and_activation_deferred"
    assert roles["runtime_role_activation_allowed"] is False
    assert len(roles["roles"]) >= 10
    assert all(role["may_execute"] is False for role in roles["roles"])
    assert all(role["may_promote"] is False for role in roles["roles"])
    assert roles["qualification_floors"]["planner_held_out_requests"] >= 100
    assert roles["qualification_floors"]["reviewer_adjudicated_panels"] >= 200
    assert roles["qualification_floors"]["complete_shadow_jobs"] >= 30
    reference = roles["reviewer_reference_authority"]
    assert reference["core_profile"] == "autonomous_adjudicated_reference_panels"
    assert "known_defect_transform" in reference["panel_components"]
    assert reference["human_profile"] == "independent_perceptual_calibration"
    assert reference["human_required_for_core"] is False


def test_qa_registry_requires_progressive_empirical_authority():
    qa = read_json(
        "Plan/10_REGISTRIES/wave64_model_qualification_and_qa_registry.json"
    )
    assert [stage["stage"] for stage in qa["qualification_stages"]] == [
        "L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"
    ]
    assert qa["pre_l0_activation_gate"]["required"] is True
    assert qa["pre_l0_activation_gate"]["qualification_execution_allowed"] is False
    assert qa["pre_l0_activation_gate"]["catalog_dry_run_ingestion_allowed"] is False
    assert qa["initial_sample_floors"]["functional_candidate"]["matched_seeds"] >= 3
    assert qa["initial_sample_floors"]["production_certificate"]["paired_outputs"] >= 50
    assert "metadata_only" in qa["promotion_prohibitions"]
    assert "self_promotion_by_generator_or_reviewer" in qa["promotion_prohibitions"]
    reference = qa["autonomous_adjudicated_reference_panel_policy"]
    assert reference["required_for_core_qualification"] is True
    assert {
        "deterministic_source_fixture",
        "known_defect_transform",
        "frozen_expected_outcome_and_tolerance",
        "qualified_multi_critic_disagreement_and_abstention_policy",
        "independent_deterministic_policy_decision",
    } <= set(reference["required_components"])
    assert reference["generator_reviewer_planner_self_promotion_allowed"] is False
    assert reference["human_adjudication_required_for_core"] is False
    assert reference["human_absence_can_block_or_revoke_core"] is False


def test_decision_example_excludes_metadata_only_candidate():
    decision = read_json(
        "Plan/08_SCHEMAS/examples/model_intelligence/"
        "wave64_contextual_model_selection_decision.example.json"
    )
    candidates = {
        row["execution_bundle_id"]: row for row in decision["evaluated_candidates"]
    }
    source_only = candidates["bundle_wave30_metadata_only_candidate"]
    assert source_only["eligible"] is False
    assert source_only["utility"] is None
    assert {
        "binary_missing", "runtime_unproven", "certificate_missing"
    } <= set(source_only["eligibility_reasons"])
    assert decision["no_silent_substitution"] is True


def test_preservation_manifest_hashes_every_generated_file():
    manifest = read_json(
        "Plan/Instructions/Hydration_Rehydration/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_PRESERVATION_MANIFEST.json"
    )
    assert manifest["status"] == "PRESERVE_PENDING_MAIN_TASK_FORMAL_ADOPTION"
    assert manifest["main_task_id"] == "019f422f-88b1-7382-872b-21de2089e983"
    for record in manifest["generated_files"] + manifest["static_control_files"]:
        if record["sha256"] is None:
            continue
        path = ROOT / record["path"]
        assert path.exists(), record["path"]
        data = path.read_bytes()
        assert len(data) == record["bytes"]
        assert hashlib.sha256(data).hexdigest() == record["sha256"]


def test_work_package_does_not_claim_runtime_or_certified_models():
    package = read_json(
        "Plan/10_REGISTRIES/"
        "wave64_autonomous_model_intelligence_work_package_registry.json"
    )
    assert package["reserved_row_range"] == {"first": 221, "last": 260, "count": 40}
    assert package["runtime_completion_claimed"] is False
    assert package["activation_gate_id"] == "wave64_model_library_download_readiness_gate_v1"
    assert package["activation_gate_state"] == "deferred_waiting_for_complete_model_download"
    assert package["runtime_execution_allowed"] is False
    assert package["production_models_certified_by_this_static_package"] == 0
    assert package["autonomous_role_stacks_selected_by_this_static_package"] == 0
    assert package["content_based_suppression"] is False


def test_model_library_activation_gate_is_schema_valid_and_fail_closed():
    builder = load_builder()
    gate = read_json(
        "Plan/10_REGISTRIES/wave64_model_library_activation_gate_registry.json"
    )
    schema = read_json("Plan/08_SCHEMAS/model_library_activation_gate.schema.json")
    common = read_json("Plan/08_SCHEMAS/model_intelligence_common.schema.json")
    registry = Registry().with_resources([
        (common["$id"], Resource.from_contents(common)),
        (schema["$id"], Resource.from_contents(schema)),
    ])
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    validator.validate(gate)
    assert builder.validate_activation_gate_semantics(gate) == []
    assert gate["gate_state"] == "deferred_waiting_for_complete_model_download"
    assert gate["runtime_execution_allowed"] is False
    assert gate["prerequisites"]["download_completion_declared"] is False
    assert gate["prerequisites"]["all_intended_assets_accounted_for"] is False
    assert gate["prerequisites"]["main_task_acknowledged"] is False
    assert gate["prerequisites"]["all_prerequisites_satisfied"] is False
    assert {
        "authoritative_wave30_staging_import",
        "model_qualification_sweep_benchmark_or_pilot",
        "autonomous_model_router_or_rag_activation",
        "production_selection_promotion_or_release",
    } <= set(gate["blocked_actions"])

    invalid_active = copy.deepcopy(gate)
    invalid_active["gate_state"] = "activated_for_staged_ingestion_and_qualification"
    invalid_active["runtime_execution_allowed"] = True
    assert not validator.is_valid(invalid_active)
    assert builder.validate_activation_gate_semantics(invalid_active)


def test_phase_safe_staging_gate_cannot_open_qualification_or_selection():
    builder = load_builder()
    schemas, registry = schema_registry(builder)
    schema = schemas["model_library_activation_gate.schema.json"]
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    gate = builder.build_activation_gate_record()
    gate["gate_state"] = "active_staging_only"
    gate["authorized_phase"] = "staging"
    gate["runtime_execution_allowed"] = True
    gate["phase_permissions"] = builder.phase_permissions_for("staging")
    gate["activation_scope"].update({
        "scope_authority": "main_task_declared_complete_scope",
        "scope_manifest_ref": builder.rr(
            "model_library_expected_download_scope", "scope_complete_v1"
        ),
    })
    gate["prerequisites"].update({
        "download_completion_declared": True,
        "download_completion_declaration_ref": builder.rr(
            "model_download_completion_manifest", "download_complete_v1"
        ),
        "download_manifest_ref": builder.rr(
            "model_download_completion_manifest", "download_complete_v1"
        ),
        "inventory_verification_ref": builder.rr(
            "model_binary_inventory_verification_report", "inventory_v1"
        ),
        "expected_in_scope_assets": 10,
        "verified_in_scope_assets": 8,
        "missing_in_scope_assets": 0,
        "hash_pending_assets": 0,
        "quarantined_assets": 1,
        "failed_assets": 1,
        "unresolved_assets": 0,
        "all_intended_assets_accounted_for": True,
        "main_task_acknowledgement_ref": builder.rr(
            "main_task_model_library_activation_acknowledgement", "ack_staging_v1"
        ),
        "main_task_acknowledged": True,
        "all_prerequisites_satisfied": True,
    })
    gate["activation_decision_ref"] = builder.rr(
        "model_library_phase_transition_decision", "transition_staging_v1"
    )
    validator.validate(gate)
    assert builder.validate_activation_gate_semantics(gate) == []
    assert gate["phase_permissions"]["source_staging_import"] is True
    assert gate["phase_permissions"]["qualification_execution"] is False
    assert gate["phase_permissions"]["production_selection"] is False

    overreach = copy.deepcopy(gate)
    overreach["phase_permissions"]["qualification_execution"] = True
    assert builder.validate_activation_gate_semantics(overreach)

    unresolved = copy.deepcopy(gate)
    unresolved["prerequisites"]["unresolved_assets"] = 1
    assert not validator.is_valid(unresolved)
    assert builder.validate_activation_gate_semantics(unresolved)


def test_phase_transition_ladder_rejects_skips_and_scope_spillover():
    builder = load_builder()
    transition = {
        "from_phase": "none",
        "to_phase": "staging",
        "decision": "authorized",
        "implicit_phase_cascade": False,
        "other_runtime_lanes_affected": False,
    }
    assert builder.validate_phase_transition_semantics(transition) == []
    skipped = dict(transition, to_phase="production_selection")
    assert builder.validate_phase_transition_semantics(skipped)
    spill = dict(transition, other_runtime_lanes_affected=True)
    assert builder.validate_phase_transition_semantics(spill)


def test_activation_prerequisite_and_runtime_contract_schemas_exist():
    builder = load_builder()
    schemas = builder.build_schemas()
    required = {
        "model_library_expected_download_scope.schema.json",
        "model_download_completion_manifest.schema.json",
        "model_binary_inventory_verification_report.schema.json",
        "main_task_model_library_activation_acknowledgement.schema.json",
        "model_library_phase_transition_decision.schema.json",
        "comfyui_runtime_lock.schema.json",
        "workflow_release_manifest.schema.json",
        "comfyui_submission_envelope.schema.json",
        "comfyui_execution_receipt.schema.json",
        "comfyui_artifact_locator.schema.json",
        "runtime_reconciliation_report.schema.json",
        "runtime_worker_lease.schema.json",
        "orchestrator_event_payload_envelope.schema.json",
        "orchestrator_state_transition_definition.schema.json",
    }
    assert required <= set(schemas)


def test_inventory_arithmetic_allows_accounted_quarantine_but_not_unresolved():
    builder = load_builder()
    report = {
        "expected_binary_count": 10,
        "accounted_binary_count": 10,
        "hash_verified_binary_count": 8,
        "quarantined_binary_count": 1,
        "failed_binary_count": 1,
        "missing_binary_count": 0,
        "hash_pending_binary_count": 0,
        "unresolved_binary_count": 0,
        "quarantined_and_failed_excluded_from_runtime": True,
    }
    assert builder.validate_inventory_report_semantics(report) == []
    bad = dict(report, accounted_binary_count=9)
    assert builder.validate_inventory_report_semantics(bad)
    bad = dict(report, unresolved_binary_count=1)
    assert builder.validate_inventory_report_semantics(bad)


def test_generated_activation_docs_freeze_scope_first_and_account_for_quarantine():
    builder = load_builder()
    rendered = "\n".join(content.decode("utf-8") for content in builder.build_docs().values())
    assert "frozen before the completion signal" in rendered
    assert "verified + quarantined + failed == expected" in rendered
    assert "runtime exclusion of quarantined/failed" in rendered
    assert "zero missing/hash-pending/corrupt/quarantined/failed/unresolved" not in rendered
    assert "any in-scope model is missing, hash-pending, corrupt, quarantined, failed" not in rendered
    assert "autonomous adjudicated reference panels" in rendered
    assert "optional `independent_perceptual_calibration`" in rendered


def test_selection_semantics_require_eligible_certified_hash_bound_pareto_bundle():
    builder = load_builder()
    decision = builder.build_examples()[
        "wave64_contextual_model_selection_decision.example.json"
    ]
    assert builder.validate_selection_decision_semantics(decision) == []
    bad = copy.deepcopy(decision)
    bad["evaluated_candidates"][0]["eligible"] = False
    assert builder.validate_selection_decision_semantics(bad)
    bad = copy.deepcopy(decision)
    bad["evaluated_candidates"][0]["certificate_ids"] = []
    assert builder.validate_selection_decision_semantics(bad)
    bad = copy.deepcopy(decision)
    bad["pareto_frontier_bundle_ids"] = []
    assert builder.validate_selection_decision_semantics(bad)
    bad = copy.deepcopy(decision)
    bad["selected_execution_bundle_ref"]["record_id"] = "different_bundle"
    assert builder.validate_selection_decision_semantics(bad)


def test_certificate_policy_and_tool_authority_negative_cases():
    builder = load_builder()
    schemas, registry = schema_registry(builder)
    provenance = {
        "producer": "test",
        "source_refs": [],
        "evidence_refs": [],
        "registry_snapshot_ids": [],
    }
    certificate = {
        "schema_version": "1.0.0",
        "record_type": "model_capability_certificate",
        "capability_certificate_id": "cert_test",
        "revision": "1",
        "status": "candidate",
        "created_at": "2026-07-16T19:30:00-05:00",
        "execution_bundle_ref": immutable_ref("model_execution_bundle", "bundle_test"),
        "capability_scope": {
            "modality": "image", "pass_intent": "skin_detail",
            "target_types": ["skin"], "engine_family": "sdxl",
            "character_count_min": 1, "character_count_max": 1,
        },
        "benchmark_result_refs": [{
            "record_type": "model_benchmark_result", "record_id": "result_test",
            "revision": "1", "sha256": None, "path_or_uri": None,
        }],
        "sample_counts": {"paired_outputs": 50, "distinct_cases": 10, "distinct_seeds": 10},
        "confidence_bounds": {"quality_lcb": 0.9, "serious_failure_rate_ucb": 0.05, "confidence_level": 0.95},
        "parameter_envelope": {"parameter_schema_id": "params_v1", "minimums": {"weight": 0.2}, "maximums": {"weight": 0.8}, "tested_values_sha256": "0" * 64},
        "hard_gate_status": "pass",
        "authority": "production_eligible",
        "valid_from": "2026-07-16T19:30:00-05:00",
        "valid_until": "2026-08-16T19:30:00-05:00",
        "exclusions": [],
        "revocation_event_id": None,
        "provenance": provenance,
    }
    cert_validator = jsonschema.Draft202012Validator(
        schemas["model_capability_certificate.schema.json"], registry=registry
    )
    cert_validator.validate(certificate)
    failed_cert = copy.deepcopy(certificate)
    failed_cert["hard_gate_status"] = "fail"
    assert not cert_validator.is_valid(failed_cert)
    undersampled = copy.deepcopy(certificate)
    undersampled["sample_counts"]["paired_outputs"] = 49
    assert not cert_validator.is_valid(undersampled)

    policy = {
        "schema_version": "1.0.0",
        "record_type": "autonomous_policy_decision",
        "policy_decision_id": "policy_test",
        "revision": "1", "status": "decision", "created_at": "2026-07-16T19:30:00-05:00",
        "subject_refs": [{"record_type": "x", "record_id": "x", "revision": "1", "sha256": None, "path_or_uri": None}],
        "policy_id": "policy_v1",
        "gate_results": [{"gate_id": "hard", "result": "fail", "evidence_ids": ["e1"]}],
        "decision": "certify", "decision_authority": "deterministic_policy",
        "reason_codes": ["attempt"], "evidence_ids": ["e1"], "provenance": provenance,
    }
    policy_validator = jsonschema.Draft202012Validator(
        schemas["autonomous_policy_decision.schema.json"], registry=registry
    )
    assert not policy_validator.is_valid(policy)

    tool = {
        "schema_version": "1.0.0", "record_type": "autonomous_tool_gateway_action",
        "tool_action_id": "tool_test", "revision": "1", "status": "requested",
        "created_at": "2026-07-16T19:30:00-05:00", "actor_role_id": "planner",
        "requested_action": "retrieve_registry_records", "allowlisted_target_id": None,
        "arguments": {"argument_schema_id": "args_v1", "payload_sha256": "0" * 64, "payload": {}},
        "authorization_decision": "allowed", "authorization_policy_id": "allow_v1",
        "denial_reasons": [], "execution_result": {"result_state": "succeeded", "evidence_ids": ["e1"]},
        "credential_exposure": False, "registry_mutation": False, "provenance": provenance,
    }
    tool_validator = jsonschema.Draft202012Validator(
        schemas["autonomous_tool_gateway_action.schema.json"], registry=registry
    )
    assert not tool_validator.is_valid(tool)


def test_mask_requirements_are_owner_transform_certificate_and_authority_bound():
    builder = load_builder()
    schemas, registry = schema_registry(builder)
    context = builder.build_examples()["wave64_model_selection_context.example.json"]
    validator = jsonschema.Draft202012Validator(
        schemas["model_selection_context.schema.json"], registry=registry
    )
    validator.validate(context)
    no_binding = copy.deepcopy(context)
    no_binding["control_and_mask_requirements"]["mask_binding_ids"] = []
    assert not validator.is_valid(no_binding)
    upgrades = copy.deepcopy(context)
    upgrades["control_and_mask_requirements"]["authority_upgrade_allowed"] = True
    assert not validator.is_valid(upgrades)
    writes_gold = copy.deepcopy(context)
    writes_gold["control_and_mask_requirements"]["writes_gold"] = True
    assert not validator.is_valid(writes_gold)


def test_artifact_locator_rejects_absolute_and_traversal_paths():
    builder = load_builder()
    schemas, registry = schema_registry(builder)
    schema = schemas["comfyui_artifact_locator.schema.json"]
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    locator = {
        "schema_version": "1.0.0", "record_type": "comfyui_artifact_locator",
        "artifact_locator_id": "locator_test", "revision": "1", "status": "verified",
        "created_at": "2026-07-16T19:30:00-05:00", "scheme": "comfyui_output",
        "runtime_id": "runtime_test", "folder_root_id": "output_root",
        "folder_type": "output", "subfolder": "run_001/pass_001", "filename": "image.png",
        "node_id": "9", "output_slot": 0,
        "view_parameters": {"filename": "image.png", "subfolder": "run_001/pass_001", "type": "output"},
        "bytes": 10, "sha256": "0" * 64, "media_type": "image/png",
        "cas_artifact_id": None, "s3_object_version_id": None,
        "absolute_path_allowed": False, "path_traversal_allowed": False,
        "verified_at": "2026-07-16T19:30:00-05:00",
        "provenance": {"producer": "test", "source_refs": [], "evidence_refs": [], "registry_snapshot_ids": []},
    }
    validator.validate(locator)
    absolute = copy.deepcopy(locator)
    absolute["subfolder"] = "C:/escape"
    assert not validator.is_valid(absolute)
    traversal = copy.deepcopy(locator)
    traversal["subfolder"] = "run/../escape"
    assert not validator.is_valid(traversal)


def test_release_row_transitively_depends_on_every_prior_model_intelligence_row():
    builder = load_builder()
    by_number = {row.number: row for row in builder.ROWS}
    pending = [dependency for dependency in by_number[260].dependencies if dependency in by_number]
    ancestors = set()
    while pending:
        number = pending.pop()
        if number in ancestors:
            continue
        ancestors.add(number)
        pending.extend(
            dependency for dependency in by_number[number].dependencies
            if dependency in by_number
        )
    assert ancestors == set(range(221, 260))


def test_citations_are_real_line_addressable_master_plan_headings():
    builder = load_builder()
    master_lines = builder.render_master_plan().splitlines()
    for item in builder.build_item_rows():
        start = int(item["Citation_Line_Start"])
        end = int(item["Citation_Line_End"])
        assert start > 0 and end >= start
        assert master_lines[start - 1].startswith("### Row")
        assert item["Citation_Excerpt"] in master_lines[start - 1]
    for tracker in builder.build_tracker_rows():
        assert int(tracker["Citation_Line_Start"]) > 0


def test_coverage_count_matches_preservation_generated_file_count():
    coverage = read_json(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_PLANNING_COVERAGE.json"
    )
    manifest = read_json(
        "Plan/Instructions/Hydration_Rehydration/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_PRESERVATION_MANIFEST.json"
    )
    assert coverage["generated_output_count_without_preservation_manifest"] == len(
        manifest["generated_files"]
    )


def test_role_activation_projection_and_numeric_ranker_are_explicitly_inactive_and_frozen():
    activation = read_json(
        "Plan/10_REGISTRIES/"
        "wave64_autonomous_role_activation_projection_registry.json"
    )
    assert activation["production_role_count"] == 0
    assert activation["shadow_role_count"] == 0
    assert all(
        projection["activation_state"] == "inactive_unselected"
        and projection["selected_stack_id"] is None
        and projection["direct_execution_authority"] is False
        for projection in activation["role_projections"]
    )
    ranking = read_json(
        "Plan/10_REGISTRIES/"
        "wave64_model_selection_feature_and_ranking_policy_registry.json"
    )["numeric_policy"]
    assert sum(ranking["quality_feature_weights"].values()) == pytest.approx(1.0)
    assert sum(ranking["risk_feature_weights"].values()) == pytest.approx(1.0)
    assert ranking["missing_data_rules"]["mandatory_feature"] == "candidate_ineligible"
    assert ranking["selection_bias_controls"]["record_propensity_or_assignment_probability"] is True


def test_runtime_entrypoint_blocks_legacy_production_compilation():
    path = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_orchestrator_run_plan.py"
    spec = importlib.util.spec_from_file_location("legacy_orchestrator_compiler", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="LEGACY_ORCHESTRATOR_COMPILER_PRODUCTION_INVOCATION_BLOCKED"):
        module.compile_plan({"execution_mode": "production"})
    dry = module.compile_plan({"execution_mode": "dry_run_plan_only"})
    assert dry["execution_mode"] == "dry_run_plan_only"


def test_second_pass_assurance_truth_does_not_claim_runtime_completion():
    assurance = read_json(
        "Plan/10_REGISTRIES/wave64_second_pass_autonomy_assurance_gap_registry.json"
    )
    assert assurance["truthful_readiness"]["production_controller"] == "not_built"
    assert assurance["truthful_readiness"]["model_library"].startswith("download_incomplete")
    assert assurance["truthful_readiness"]["autonomous_roles"] == "unselected_unqualified_inactive"
    gate = read_json(
        "Plan/10_REGISTRIES/wave64_model_library_activation_gate_registry.json"
    )
    assert gate["activation_scope"]["does_not_block_independently_governed_lanes"] is True
    assert gate["authorized_phase"] == "none"
    assert not any(gate["phase_permissions"].values())
