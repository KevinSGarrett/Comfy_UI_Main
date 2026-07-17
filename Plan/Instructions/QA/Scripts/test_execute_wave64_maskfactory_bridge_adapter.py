from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_maskfactory_bridge_adapter.py"


@pytest.fixture(scope="module")
def adapter():
    spec = importlib.util.spec_from_file_location("execute_wave64_maskfactory_bridge_adapter_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("adapter module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def request_fixture(adapter, *, mode="mode_b_live_predict"):
    request = copy.deepcopy(adapter.CORE.build_examples()["maskfactory_bridge_request_v2.example.json"])
    request["access_mode"] = mode
    if mode == "mode_a_package_read":
        for region in request["target_region_bindings"]:
            region["selector_kind"] = "mode_a_exact_package_artifact"
    adapter.VERIFY.validate_schema(request, "maskfactory_bridge_request_v2.schema.json")
    return request


def artifact_fixture(adapter, request, raw=b"fixture-mask-bytes"):
    digest = adapter.sha256_bytes(raw)
    return {
        "label": request["mask_intents"][0]["label"],
        "mask_type": request["mask_intents"][0]["mask_type"],
        "mask_ref": {
            "record_type": "mask_artifact",
            "record_id": f"mask_{digest[:16]}",
            "revision": "r001",
            "sha256": digest,
        },
        "path": "masks/person.bin",
        "sha256": digest,
        "bytes": len(raw),
        "width": request["source_artifact"]["width"],
        "height": request["source_artifact"]["height"],
        "coordinate_space": request["source_artifact"]["coordinate_space"],
        "owner": copy.deepcopy(request["owner_bindings"][0]),
        "authority": adapter.CORE.fixture_authority(state="draft"),
        "certificate_ref": None,
        "qa_record_refs": [adapter.CORE.ref("mask_qa_record", f"qa_{digest[:16]}", "7")],
    }


def package_fixture(adapter, request, artifact):
    return {
        "schema_version": "1.0.0",
        "record_type": "maskfactory_mode_a_package_manifest",
        "package_id": "mode_a_fixture_package_001",
        "revision": "r001",
        "created_at": request["created_at"],
        "fixture_only": True,
        "release_snapshot_ref": copy.deepcopy(request["release_snapshot_ref"]),
        "route_id": "mode_a_fixture_route",
        "execution_stack_ref": adapter.CORE.ref("execution_stack", "mode_a_fixture_stack", "5"),
        "source_artifact": copy.deepcopy(request["source_artifact"]),
        "media_scope": copy.deepcopy(request["media_scope"]),
        "owner_bindings": copy.deepcopy(request["owner_bindings"]),
        "transform_chain": copy.deepcopy(request["transform_chain"]),
        "ontology_labels": [artifact["label"]],
        "artifacts": [copy.deepcopy(artifact)],
    }


def materialize_package(tmp_path, artifact, raw=b"fixture-mask-bytes"):
    path = tmp_path / artifact["path"]
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)


def health_fixture(adapter, request):
    health = copy.deepcopy(adapter.CORE.build_examples()["maskfactory_health_capability_snapshot_v2.example.json"])
    health["release_snapshot_ref"] = copy.deepcopy(request["release_snapshot_ref"])
    health["routes"][0]["access_mode"] = request["access_mode"]
    return health


def not_found_evidence_fixture(adapter, request):
    return {
        "schema_version": "1.0.0",
        "record_type": "maskfactory_fixture_not_found_reconciliation_evidence",
        "fixture_only": True,
        "request_payload_sha256": adapter.sha256_bytes(adapter.canonical_json(request)),
        "idempotency_key": request["idempotency_key"],
        "outcome": "not_found_safe_to_submit",
        "remote_status": "not_found",
        "resubmission_authorized": True,
        "evidence_ref": adapter.CORE.ref("reconciliation_evidence", "signed_not_found_001", "9"),
        "signature_trust": adapter.CORE.fixture_signing_trust(
            trusted=False, signer_role="maskfactory_reconciliation_signer"
        ),
    }


def test_mode_a_reads_exact_package_without_mutating_source(adapter, tmp_path):
    request = request_fixture(adapter, mode="mode_a_package_read")
    artifact = artifact_fixture(adapter, request)
    manifest = package_fixture(adapter, request, artifact)
    materialize_package(tmp_path, artifact)
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    result = adapter.execute_mode_a_fixture(request, manifest, tmp_path, allow_fixture=True)
    after = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert before == after
    assert result["status"] == "succeeded"
    assert result["access_mode"] == "mode_a_package_read"
    assert result["authority"]["authority_state"] == "draft"
    assert result["operational_certificate_ref"] is None
    assert result["cache_state"] == "bypassed"


@pytest.mark.parametrize("field", ["release_snapshot_ref", "source_artifact", "media_scope", "owner_bindings", "transform_chain"])
def test_mode_a_exact_request_bindings_fail_closed(adapter, tmp_path, field):
    request = request_fixture(adapter, mode="mode_a_package_read")
    artifact = artifact_fixture(adapter, request)
    manifest = package_fixture(adapter, request, artifact)
    materialize_package(tmp_path, artifact)
    manifest[field] = copy.deepcopy(manifest[field])
    if isinstance(manifest[field], list):
        manifest[field][0][next(iter(manifest[field][0]))] = "drifted"
    elif field == "release_snapshot_ref":
        manifest[field]["record_id"] = "drifted"
    elif field == "source_artifact":
        manifest[field]["sha256"] = "0" * 64
    elif field == "media_scope":
        manifest[field]["exact_frame_scope_only"] = False
    else:
        manifest[field]["chain_id"] = "drifted"
    with pytest.raises(ValueError, match="binding differs"):
        adapter.execute_mode_a_fixture(request, manifest, tmp_path, allow_fixture=True)


@pytest.mark.parametrize("mutation", ["hash", "size", "ref", "path"])
def test_mode_a_artifact_bytes_are_hash_size_ref_and_path_bound(adapter, tmp_path, mutation):
    request = request_fixture(adapter, mode="mode_a_package_read")
    artifact = artifact_fixture(adapter, request)
    manifest = package_fixture(adapter, request, artifact)
    materialize_package(tmp_path, artifact)
    target = manifest["artifacts"][0]
    if mutation == "hash":
        target["sha256"] = "0" * 64
    elif mutation == "size":
        target["bytes"] += 1
    elif mutation == "ref":
        target["mask_ref"]["sha256"] = "1" * 64
    else:
        target["path"] = "../escape.bin"
    with pytest.raises(ValueError, match="unsafe|hash/size/ref"):
        adapter.execute_mode_a_fixture(request, manifest, tmp_path, allow_fixture=True)


def test_fixture_mode_a_rejects_certificate_or_authority_elevation(adapter, tmp_path):
    request = request_fixture(adapter, mode="mode_a_package_read")
    artifact = artifact_fixture(adapter, request)
    manifest = package_fixture(adapter, request, artifact)
    materialize_package(tmp_path, artifact)
    manifest["artifacts"][0]["authority"] = adapter.CORE.fixture_authority(state="certified", certified=True)
    manifest["artifacts"][0]["certificate_ref"] = copy.deepcopy(manifest["artifacts"][0]["authority"]["certificate_ref"])
    with pytest.raises(ValueError, match="cannot assert certified"):
        adapter.execute_mode_a_fixture(request, manifest, tmp_path, allow_fixture=True)


def test_fixture_execution_requires_explicit_flag_and_never_accepts_production_request(adapter, tmp_path):
    request = request_fixture(adapter, mode="mode_a_package_read")
    artifact = artifact_fixture(adapter, request)
    manifest = package_fixture(adapter, request, artifact)
    materialize_package(tmp_path, artifact)
    with pytest.raises(ValueError, match="explicit allow_fixture"):
        adapter.execute_mode_a_fixture(request, manifest, tmp_path)
    request["fixture_only"] = False
    with pytest.raises(ValueError, match="production adapter execution requires"):
        adapter.execute_mode_a_fixture(request, manifest, tmp_path, allow_fixture=True)


def test_mode_b_success_is_draft_hash_bound_and_lifecycle_complete(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    health = health_fixture(adapter, request)
    outcome = adapter.execute_mode_b_fixture(
        request, health, [artifact], tmp_path / "lifecycle.json", allow_fixture=True
    )
    result = outcome["result"]
    assert outcome["status"] == "succeeded"
    assert outcome["lifecycle_state"]["state"] == "succeeded"
    assert [item["to_state"] for item in outcome["lifecycle_state"]["transitions"]] == [
        "admitted", "submitted", "accepted", "running", "succeeded"
    ]
    assert result["authority"]["authority_state"] == "draft"
    assert result["raw_producer_receipt_payload_sha256"] != result["normalization_payload_sha256"]
    assert result["execution_observation"]["selected_route_id"] == result["route_id"]
    assert result["runtime_completion_claimed"] is False


def test_mode_b_ambiguous_transport_requires_reconciliation_before_resubmission(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    lifecycle = tmp_path / "lifecycle.json"
    outcome = adapter.execute_mode_b_fixture(
        request, health_fixture(adapter, request), [artifact], lifecycle,
        transport_outcome="ambiguous", allow_fixture=True,
    )
    assert outcome["status"] == "outcome_unknown"
    assert outcome["resubmission_allowed"] is False
    with pytest.raises(ValueError, match="existing lifecycle"):
        adapter.execute_mode_b_fixture(
            request, health_fixture(adapter, request), [artifact], lifecycle, allow_fixture=True
        )
    with pytest.raises(ValueError, match="unregistered lifecycle transition"):
        adapter.advance_lifecycle(lifecycle, request, "submitted")


def test_signed_not_found_evidence_authorizes_exactly_one_resubmission(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    lifecycle = tmp_path / "lifecycle.json"
    adapter.execute_mode_b_fixture(
        request, health_fixture(adapter, request), [artifact], lifecycle,
        transport_outcome="ambiguous", allow_fixture=True,
    )
    evidence = not_found_evidence_fixture(adapter, request)
    state = adapter.reconcile_not_found_for_resubmission(lifecycle, request, evidence)
    assert state["state"] == "submitted"
    assert state["resubmission_authorization_consumed"] is True
    with pytest.raises(ValueError):
        adapter.advance_lifecycle(lifecycle, request, "submitted", evidence_ref=evidence["evidence_ref"])


@pytest.mark.parametrize("mutation", ["request", "idempotency", "outcome", "signature"])
def test_reconciliation_evidence_is_exactly_bound_and_explicitly_nonproduction(adapter, tmp_path, mutation):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    lifecycle = tmp_path / "lifecycle.json"
    adapter.execute_mode_b_fixture(
        request, health_fixture(adapter, request), [artifact], lifecycle,
        transport_outcome="ambiguous", allow_fixture=True,
    )
    evidence = not_found_evidence_fixture(adapter, request)
    if mutation == "request":
        evidence["request_payload_sha256"] = "0" * 64
    elif mutation == "idempotency":
        evidence["idempotency_key"] = "different_idempotency"
    elif mutation == "outcome":
        evidence["outcome"] = "found_running"
    else:
        evidence["signature_trust"]["signature_verified"] = False
    with pytest.raises(ValueError, match="evidence|reconciliation"):
        adapter.reconcile_not_found_for_resubmission(lifecycle, request, evidence)


def test_lifecycle_write_lock_fails_closed(adapter, tmp_path):
    request = request_fixture(adapter)
    lifecycle = tmp_path / "lifecycle.json"
    lock = lifecycle.with_suffix(".json.lock")
    lock.write_text("held", encoding="utf-8")
    with pytest.raises(ValueError, match="locked"):
        adapter.advance_lifecycle(lifecycle, request, "admitted")
    assert lock.read_text(encoding="utf-8") == "held"


@pytest.mark.parametrize("mutation", ["stale", "release", "route", "authority"])
def test_health_admission_is_exact_and_fail_closed(adapter, mutation):
    request = request_fixture(adapter)
    health = health_fixture(adapter, request)
    if mutation == "stale":
        health["expires_at"] = "2026-07-17T02:19:59-05:00"
    elif mutation == "release":
        health["release_snapshot_ref"]["record_id"] = "other_release"
    elif mutation == "route":
        health["routes"][0]["supported_labels"] = ["hair"]
    else:
        health["routes"][0]["default_authority_state"] = "qa_passed_noncertified"
    with pytest.raises(ValueError):
        adapter.validate_health_for_request(request, health)


def test_normalization_rejects_input_output_collision_for_live_mode(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    artifact["sha256"] = request["target_region_bindings"][0]["region_sha256"]
    artifact["mask_ref"]["sha256"] = artifact["sha256"]
    with pytest.raises(ValueError, match="conflated"):
        adapter.execute_mode_b_fixture(
            request, health_fixture(adapter, request), [artifact], tmp_path / "lifecycle.json", allow_fixture=True
        )


def test_arbitration_preserves_stronger_authority_and_never_prefers_newer_draft(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    first = adapter.execute_mode_b_fixture(
        request, health_fixture(adapter, request), [artifact], tmp_path / "one.json", allow_fixture=True
    )["result"]
    stronger = copy.deepcopy(first)
    stronger["maskfactory_bridge_result_v2_id"] = "stronger_qa_candidate"
    stronger["authority"] = adapter.CORE.fixture_authority(state="qa_passed_noncertified")
    stronger["masks"][0]["authority"] = copy.deepcopy(stronger["authority"])
    adapter.CORE.seal_normalized_result(stronger)
    decision = adapter.arbitrate_results([(first, None), (stronger, None)])
    assert decision["decision"] == "selected"
    assert decision["selected_result_ref"]["record_id"] == "stronger_qa_candidate"


def test_equal_authority_ambiguity_abstains_or_branches_only_with_budget(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    first = adapter.execute_mode_b_fixture(
        request, health_fixture(adapter, request), [artifact], tmp_path / "one.json", allow_fixture=True
    )["result"]
    second = copy.deepcopy(first)
    second["maskfactory_bridge_result_v2_id"] = "equal_candidate_002"
    adapter.CORE.seal_normalized_result(second)
    assert adapter.arbitrate_results([(first, None), (second, None)])["decision"] == "abstain"
    bounded = adapter.arbitrate_results([(first, None), (second, None)], branch_budget=2)
    assert bounded["decision"] == "branch_for_bounded_qa"
    assert len(bounded["branch_result_refs"]) == 2


def test_scope_ambiguity_abstains(adapter, tmp_path):
    request = request_fixture(adapter)
    artifact = artifact_fixture(adapter, request)
    first = adapter.execute_mode_b_fixture(
        request, health_fixture(adapter, request), [artifact], tmp_path / "one.json", allow_fixture=True
    )["result"]
    second = copy.deepcopy(first)
    second["maskfactory_bridge_result_v2_id"] = "different_scope_candidate"
    second["media_scope"]["source_media_sha256"] = "f" * 64
    second["source_artifact"]["sha256"] = "f" * 64
    second["source_artifact"]["artifact_ref"]["sha256"] = "f" * 64
    second["media_scope"]["source_media_ref"]["sha256"] = "f" * 64
    adapter.CORE.seal_normalized_result(second)
    decision = adapter.arbitrate_results([(first, None), (second, None)])
    assert decision["decision"] == "abstain"
    assert decision["reason"] == "scope_ambiguity"
