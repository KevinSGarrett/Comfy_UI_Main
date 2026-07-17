from __future__ import annotations

import copy
import base64
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
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[4]
BUILDER = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_maskfactory_autonomous_bridge_package.py"
VALIDATOR = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_maskfactory_autonomous_bridge_package.py"
PRODUCER_ROOT_CANDIDATES = [
    ROOT.parent / "mask-autonomy-bridge-plan",
    Path(r"C:\Comfy_UI_Main_Masking"),
]


def producer_root() -> Path:
    for candidate in PRODUCER_ROOT_CANDIDATES:
        if (candidate / "src/maskfactory/schemas/maskfactory_release_snapshot.schema.json").is_file():
            return candidate
    raise AssertionError("frozen MaskFactory producer tree is required for exact bridge conformance tests")


def producer_fixture(name: str):
    root = producer_root() / "tests/fixtures/mask_bridge_contracts"
    if name in {"maskfactory_release_snapshot", "maskfactory_capability_snapshot", "mask_authority_invalidation_event", "mask_acquisition_request"}:
        return json.loads((root / "positive_contract_set_v1.json").read_text(encoding="utf-8"))[name]
    files = {
        "mask_acquisition_receipt": "positive_certified_mode_b_receipt_v1.json",
        "operational_autonomy_certificate": "positive_operational_autonomy_certificate_v1.json",
    }
    return json.loads((root / files[name]).read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location("wave64_maskfactory_bridge_builder_test", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return load_builder()


@pytest.fixture(scope="module")
def contracts(builder):
    schemas = builder.build_schemas()
    registry = Registry().with_resources([(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()])
    return schemas, registry


def schema_for_record_type(schemas, record_type):
    matches = [schema for schema in schemas.values() if schema.get("properties", {}).get("record_type", {}).get("const") == record_type]
    assert len(matches) == 1
    return matches[0]


def errors_for(schema, record, registry):
    return list(jsonschema.Draft202012Validator(schema, registry=registry, format_checker=jsonschema.FormatChecker()).iter_errors(record))


def test_builder_check_passes():
    result = subprocess.run([sys.executable, str(BUILDER), "--check"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["rows"] == 28
    assert payload["runtime_completion_claimed"] is False
    assert payload["runtime_adapter_implemented"] is False


def test_validator_passes():
    result = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["schemas"] >= 13


def test_rows_contiguous_unique_and_four_per_workstream(builder):
    rows = builder.build_rows()
    assert [row["row_number"] for row in rows] == list(range(321, 349))
    assert len({row["item_id"] for row in rows}) == 28
    assert len({row["tracker_id"] for row in rows}) == 28
    assert Counter(row["workstream_id"] for row in rows) == {wid: 4 for wid, _, _ in builder.WORKSTREAMS}


def test_parent_and_final_dependency_graph(builder):
    rows = builder.build_rows()
    item_ids = {row["item_id"] for row in rows}
    deps = {row["item_id"]: [dep for dep in row["dependencies"] if dep in item_ids] for row in rows}
    seen = set()
    stack = ["ITEM-W64-348"]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(deps[current])
    assert seen == item_ids
    assert "ITEM-W64-218" in rows[-1]["dependencies"]
    external = set()
    stack = ["ITEM-W64-348"]
    by_id = {row["item_id"]: row for row in rows}
    while stack:
        current = stack.pop()
        for dep in by_id[current]["dependencies"]:
            external.add(dep)
            if dep in item_ids:
                stack.append(dep)
    assert set(builder.PARENT_ITEMS).issubset(external)


def test_rows_are_planning_only_and_core_profile_isolated(builder):
    for row in builder.build_rows():
        assert row["status"] == builder.STATUS
        assert row["runtime_completion_claimed"] is False
        assert row["completion_profile"] == "core_autonomous_runtime"
        assert row["optional_profiles_not_blocking"] == ["independent_real_accuracy", "scale_daz_maturity"]


def test_schemas_are_unique_meta_valid_and_top_level_strict(contracts):
    schemas, _ = contracts
    assert len({schema["$id"] for schema in schemas.values()}) == len(schemas)
    for name, schema in schemas.items():
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        if name != "wave64_maskfactory_bridge_common_v2.schema.json":
            assert schema["additionalProperties"] is False


def test_every_example_validates_against_exact_schema(builder, contracts):
    schemas, registry = contracts
    for name, record in builder.build_examples().items():
        schema = schema_for_record_type(schemas, record["record_type"])
        assert not errors_for(schema, record, registry), name


def test_unknown_top_level_field_is_rejected(builder, contracts):
    schemas, registry = contracts
    record = copy.deepcopy(builder.build_examples()["maskfactory_bridge_request_v2.example.json"])
    record["llm_invented_field"] = "unsafe"
    schema = schemas["maskfactory_bridge_request_v2.schema.json"]
    assert errors_for(schema, record, registry)


def test_wire_vocabularies_are_exact(builder):
    registry = builder.build_registries()["wave64_maskfactory_bridge_authority_crosswalk_v2.json"]
    assert registry["access_modes"] == ["mode_a_package_read", "mode_b_live_predict", "mode_b_live_refine"]
    assert registry["authority_states"] == ["invalid", "hypothesis", "draft", "qa_passed_noncertified", "certified"]
    assert registry["issuer_kinds"] == ["maskfactory_autonomous", "human_anchor_optional", "none"]
    assert "operationally_certified_artifact" in registry["claim_classes"]
    assert registry["operational_claim_firewall"]["legacy_autonomous_certified_gold_alias_allowed"] is False


def test_access_mode_never_implies_authority(builder):
    registry = builder.build_registries()["wave64_maskfactory_bridge_authority_crosswalk_v2.json"]
    assert len(registry["matrix"]) == 15
    assert all(entry["access_mode_implies_authority"] is False for entry in registry["matrix"])
    assert registry["mode_a_unconditionally_promotable"] is False
    assert registry["mode_b_permanently_nonpromotable"] is False


def test_current_mode_b_defaults_to_draft(builder):
    result = builder.build_examples()["maskfactory_bridge_result_v2.example.json"]
    health = builder.build_examples()["maskfactory_health_capability_snapshot_v2.example.json"]
    assert result["access_mode"].startswith("mode_b_")
    assert result["authority"]["authority_state"] == "draft"
    assert "can_satisfy_promotion_gate" not in result
    assert health["current_mode_b_default_authority_state"] == "draft"


def certified_mode_b_pair(builder):
    examples = builder.build_examples()
    result = copy.deepcopy(examples["maskfactory_bridge_result_v2.example.json"])
    certificate = copy.deepcopy(examples["maskfactory_operational_certificate_v2.example.json"])
    certificate["fixture_only"] = False
    certificate["runtime_completion_claimed"] = False
    certificate["certification_context"] = "production_runtime"
    certificate["signature_algorithm"] = "ed25519"
    certificate["raw_producer_certificate_signature_trust"] = builder.fixture_signing_trust(trusted=True, key_id="maskfactory_production_signer_001", signer_role="maskfactory_operational_certificate_signer")
    certificate["signature_trust"] = builder.fixture_signing_trust(trusted=True, key_id="main_normalization_signer_001", signer_role="main_normalization_signer")
    certificate["genuine_runtime_evidence_refs"] = [builder.ref("runtime_evidence", "runtime_certificate_evidence_001", "d")]
    builder.seal_operational_certificate(certificate)
    certificate_ref = builder.immutable_operational_certificate_ref(certificate)
    result["authority"] = builder.fixture_authority("certified", "maskfactory_autonomous", True)
    result["authority"]["certificate_ref"] = certificate_ref
    result["masks"][0]["authority"] = copy.deepcopy(result["authority"])
    result["operational_certificate_ref"] = certificate_ref
    result["fixture_only"] = False
    result["runtime_completion_claimed"] = False
    builder.seal_normalized_result(result)
    return result, certificate


def production_policy(builder):
    policy = copy.deepcopy(builder.build_examples()["maskfactory_promotion_gate_policy_v2.example.json"])
    policy["fixture_only"] = False
    policy["policy_context"] = "production_runtime"
    policy["signature_trust"] = builder.fixture_signing_trust(trusted=True, key_id="main_promotion_policy_signer_001", signer_role="main_promotion_policy_signer")
    policy["genuine_runtime_evidence_refs"] = [builder.ref("runtime_evidence", "policy_runtime_evidence_001", "d")]
    builder.seal_promotion_policy(policy)
    return policy


def certified_authority_decision_bundle(builder):
    result, certificate = certified_mode_b_pair(builder)
    decision = copy.deepcopy(builder.build_examples()["maskfactory_authority_decision_v2.example.json"])
    policy = production_policy(builder)
    certificate["promotion_gate_policy_ref"] = copy.deepcopy(policy["policy_artifact_ref"])
    builder.seal_operational_certificate(certificate)
    certificate_ref = builder.immutable_operational_certificate_ref(certificate)
    result["operational_certificate_ref"] = copy.deepcopy(certificate_ref)
    result["authority"]["certificate_ref"] = copy.deepcopy(certificate_ref)
    result["masks"][0]["authority"]["certificate_ref"] = copy.deepcopy(certificate_ref)
    builder.seal_normalized_result(result)
    decision.update({
        "fixture_only": False,
        "result_ref": builder.ref("maskfactory_bridge_result_v2", result["maskfactory_bridge_result_v2_id"], "6"),
        "observed_authority": copy.deepcopy(result["authority"]),
        "required_authority_state": "certified",
        "required_claim_classes": ["operationally_certified_artifact"],
        "required_certificate_scope": ["mask_target_edit"],
        "intended_use": "promotion_bound",
        "decision": "eligible",
        "eligible_for_intended_use": True,
        "decision_at": "2026-07-17T02:21:00-05:00",
        "certificate_signature_trust": copy.deepcopy(certificate["signature_trust"]),
        "genuine_runtime_evidence_refs": [builder.ref("runtime_evidence", "decision_runtime_evidence_001", "e")],
        "consumer_policy_ref": copy.deepcopy(policy["policy_artifact_ref"]),
        "consumer_policy_sha256": policy["policy_sha256"],
    })
    decision["certificate_temporal_evaluation"] = {
        "certificate_ref": copy.deepcopy(certificate_ref),
        "decision_at": decision["decision_at"],
        "certificate_issued_at": certificate["issued_at"],
        "certificate_expires_at": certificate["expires_at"],
        "revocation_index_ref": builder.ref("revocation_index", "revocation_index_runtime_001", "e"),
        "revocation_index_valid_from": "2026-07-17T02:00:00-05:00",
        "revocation_index_valid_until": "2026-07-18T02:00:00-05:00",
        "revocation_checked_at": decision["decision_at"],
        "issued_not_after_decision": True,
        "decision_before_expiry": True,
        "revocation_index_current_at_decision": True,
        "certificate_not_revoked": True,
        "temporal_decision": "valid",
    }
    return result, certificate, decision, policy


def add_runtime_artifact(builder, runtime_context, record_type, record_id, payload):
    value = {"record_type": record_type, "record_id": record_id, "revision": "r001", "sha256": builder.sha256_bytes(payload)}
    runtime_context["artifact_bytes"][builder.immutable_ref_key(value)] = payload
    return value


def add_runtime_signer(builder, runtime_context, trusted_keys, key_id, signer_role):
    private_key = Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    public_key_base64 = base64.b64encode(public_key_bytes).decode("ascii")
    public_key_sha256 = builder.sha256_bytes(public_key_bytes)
    revocation_ref = add_runtime_artifact(builder, runtime_context, "key_revocation_evidence", f"{key_id}_revocation", f"{key_id}:active-unrevoked".encode())
    entry = {
        "key_id": key_id, "signer_role": signer_role, "status": "active",
        "public_key_base64": public_key_base64, "public_key_sha256": public_key_sha256,
        "valid_from": "2026-07-16T00:00:00-05:00", "valid_until": "2026-07-19T00:00:00-05:00",
        "revocation_checked_at": "2026-07-17T02:20:00-05:00", "revocation_valid_until": "2026-07-18T02:30:00-05:00",
        "revocation_evidence_ref": revocation_ref,
    }
    entry["entry_sha256"] = builder.trusted_key_entry_sha256(entry)
    trusted_keys[key_id] = entry
    runtime_context["private_keys"][key_id] = private_key
    verification_ref = add_runtime_artifact(builder, runtime_context, "signature_verification_evidence", f"{key_id}_verification", f"{key_id}:verified".encode())
    trust = builder.fixture_signing_trust(trusted=True, key_id=key_id, signer_role=signer_role)
    trust.update({
        "embedded_public_key_sha256": public_key_sha256,
        "trusted_key_entry_sha256": entry["entry_sha256"],
        "verified_at": runtime_context["use_time"],
        "verification_evidence_ref": verification_ref,
    })
    return trust


def sign_runtime_payload(runtime_context, domain, payload_sha256, key_id, *, digest_bytes=False):
    digest = bytes.fromhex(payload_sha256)
    message = digest if digest_bytes else domain.encode("utf-8") + b"\0" + digest
    return base64.b64encode(runtime_context["private_keys"][key_id].sign(message)).decode("ascii")


def corrupt_signature(signature_base64):
    signature = bytearray(base64.b64decode(signature_base64, validate=True))
    signature[0] ^= 0x01
    return base64.b64encode(bytes(signature)).decode("ascii")


def _release_component_bindings(raw):
    artifacts = {value["kind"]: value for value in raw["artifacts"]}
    compatibility, semantic, signing, checkpoint = raw["compatibility"], raw["semantic_invariant_profile"], raw["signing_trust"], raw["journal_checkpoint"]
    values = {
        ("api_openapi", raw["openapi"]["version"], raw["openapi"]["sha256"]),
        ("compatibility_manifest", compatibility["bridge_contract"], artifacts["compatibility_manifest"]["sha256"]),
        ("package_format", compatibility["package_format"], artifacts["compatibility_manifest"]["sha256"]),
        ("ontology", compatibility["ontology_version"], artifacts["compatibility_manifest"]["sha256"]),
        ("node_pack", compatibility["node_pack_version"], artifacts["comfyui_node_pack"]["sha256"]),
        ("workflow_inventory", raw["workflow_inventory"]["inventory_id"], raw["workflow_inventory"]["sha256"]),
        ("node_inventory", raw["node_inventory"]["inventory_id"], raw["node_inventory"]["sha256"]),
        ("install_manifest", "sha256", raw["installation"]["install_manifest_sha256"]),
        ("installer", raw["installation"]["installer_id"], raw["installation"]["installer_sha256"]),
        ("installation_verification", raw["installation"]["verification_workflow_id"], raw["installation"]["verification_workflow_sha256"]),
        ("rollback", raw["rollback"]["rollback_id"], raw["rollback"]["rollback_sha256"]),
        ("rollback_verification", raw["rollback"]["target_release_id"], raw["rollback"]["verification_evidence_sha256"]),
        ("semantic_profile", semantic["record_id"], semantic["profile_sha256"]),
        ("semantic_profile_document", "1.0.0", semantic["document_sha256"]),
        ("capability_snapshot_document", raw["capability_snapshot"]["record_id"], raw["capability_snapshot"]["document_sha256"]),
        ("signing_key_set", signing["key_set_version"], signing["key_set_sha256"]),
        ("rotation_policy", signing["rotation_policy_id"], signing["rotation_policy_sha256"]),
        ("revocation_policy", signing["revocation_policy_id"], signing["revocation_policy_sha256"]),
        ("journal_head", checkpoint["stream_id"], checkpoint["head_event_sha256"]),
        ("journal_revocation_state", str(checkpoint["last_sequence"]), checkpoint["revocation_state_sha256"]),
        ("journal_validator", str(checkpoint["event_count"]), checkpoint["validator_sha256"]),
    }
    return [{"component": name, "version": version, "sha256": digest} for name, version, digest in sorted(values)]


def production_release_adoption_bundle(builder):
    examples = builder.build_examples()
    consumer = copy.deepcopy(examples["maskfactory_consumer_requirements_v2.example.json"])
    release = copy.deepcopy(examples["maskfactory_release_snapshot_v2.example.json"])
    adoption = copy.deepcopy(examples["maskfactory_adoption_receipt_v2.example.json"])
    runtime_context = {
        "artifact_bytes": {}, "private_keys": {}, "use_time": "2026-07-17T02:21:30-05:00",
        "last_accepted_use_time": "2026-07-17T02:20:00-05:00", "last_accepted_clock_sequence": 40,
        "producer_wire_schema_bytes": {
            name: (producer_root() / f"src/maskfactory/schemas/{name}.schema.json").read_bytes()
            for name in builder.PRODUCER_SCHEMA_BINDINGS
        },
        "producer_release_revocation_refs": {},
    }
    trusted_keys = {}
    role_keys = {
        "maskfactory_release_signer": "mf-release-runtime-001",
        "maskfactory_receipt_signer": "maskfactory_receipt_signer_001",
        "maskfactory_operational_certificate_signer": "maskfactory_operational_certificate_signer_001",
        "main_normalization_signer": "main_normalization_signer_001",
        "main_adoption_signer": "main_adoption_signer_001",
        "main_journal_checkpoint_signer": "main_journal_checkpoint_signer_001",
        "main_bridge_gate_signer": "main_bridge_gate_signer_001",
        "main_bridge_release_signer": "main_bridge_release_signer_001",
        "main_trusted_clock_signer": "main_trusted_clock_signer_001",
        "main_promotion_policy_signer": "main_promotion_policy_signer_001",
        "main_mask_request_signer": "main_mask_request_signer_001",
    }
    consumer["required_signing_key_ids"] = [role_keys["maskfactory_release_signer"]]
    trusts = {role: add_runtime_signer(builder, runtime_context, trusted_keys, key_id, role) for role, key_id in role_keys.items()}
    runtime_context["trusted_keys"] = trusted_keys

    clock = {
        "source": "main_monotonic_utc_clock", "observed_at": runtime_context["use_time"],
        "clock_sequence": 41, "monotonic_floor_at": runtime_context["last_accepted_use_time"],
    }
    clock_bytes = builder.trusted_clock_payload(clock)
    clock["evidence_ref"] = add_runtime_artifact(builder, runtime_context, "trusted_clock_evidence", "trusted_clock_runtime_001", clock_bytes)
    clock["payload_sha256"] = builder.sha256_bytes(clock_bytes)
    clock["signature_domain"] = "comfy_ui_main.trusted_clock_observation.v1"
    clock["signature_trust"] = copy.deepcopy(trusts["main_trusted_clock_signer"])
    clock["signature"] = sign_runtime_payload(runtime_context, clock["signature_domain"], clock["payload_sha256"], role_keys["main_trusted_clock_signer"])
    runtime_context["trusted_clock"] = clock

    raw_capability = producer_fixture("maskfactory_capability_snapshot")
    raw_capability_bytes = builder.canonical_json(raw_capability)
    capability_ref = add_runtime_artifact(builder, runtime_context, raw_capability["record_type"], raw_capability["snapshot_id"], raw_capability_bytes)
    runtime_context["adopted_capability_snapshot_ref"] = capability_ref

    raw_release = producer_fixture("maskfactory_release_snapshot")
    raw_release.update({"release_status": "published", "evidence_context": "runtime_evidence", "fixture_only": False})
    raw_release["capability_snapshot"]["document_sha256"] = capability_ref["sha256"]
    revocation_state_ref = add_runtime_artifact(builder, runtime_context, "producer_revocation_state", "producer_revocation_state_runtime_001", b"producer-revocation-state:empty")
    raw_release["journal_checkpoint"]["revocation_state_sha256"] = revocation_state_ref["sha256"]
    release_key_id = role_keys["maskfactory_release_signer"]
    release_entry = trusted_keys[release_key_id]
    raw_release["signing_trust"].update({
        "release_signing_key_id": release_key_id,
        "release_signing_public_key_sha256": release_entry["public_key_sha256"],
    })
    raw_release_digest = builder.maskfactory_document_sha256(raw_release, excluded=("release_payload_sha256", "signature"))
    raw_release["release_payload_sha256"] = raw_release_digest
    raw_release["signature"] = {
        "algorithm": "ed25519", "key_id": release_key_id, "public_key_base64": release_entry["public_key_base64"],
        "signed_payload_sha256": raw_release_digest, "signed_payload_format": "sha256_digest_bytes",
        "value_base64": sign_runtime_payload(runtime_context, "maskfactory.sha256_digest_bytes.v1", raw_release_digest, release_key_id, digest_bytes=True),
    }
    raw_release_bytes = builder.canonical_json(raw_release)
    raw_release_ref = add_runtime_artifact(builder, runtime_context, raw_release["record_type"], raw_release["release_id"], raw_release_bytes)
    runtime_context.update({
        "producer_revocation_state_ref": revocation_state_ref,
        "producer_active_revocation_count": raw_release["journal_checkpoint"]["active_revocation_count"],
        "adopted_producer_release_binding": {
            "release_id": raw_release["release_id"], "release_payload_sha256": raw_release_digest,
            "capability_snapshot_id": raw_capability["snapshot_id"], "capability_snapshot_sha256": raw_capability["snapshot_sha256"],
            "capability_snapshot_document_sha256": capability_ref["sha256"], "bridge_contract": raw_release["compatibility"]["bridge_contract"],
            "signing_key_set_id": raw_release["signing_trust"]["key_set_id"], "signing_key_set_version": raw_release["signing_trust"]["key_set_version"],
            "signing_key_set_sha256": raw_release["signing_trust"]["key_set_sha256"], "rotation_policy_sha256": raw_release["signing_trust"]["rotation_policy_sha256"],
            "revocation_policy_sha256": raw_release["signing_trust"]["revocation_policy_sha256"],
        },
    })

    release_evidence = add_runtime_artifact(builder, runtime_context, "runtime_evidence", "release_runtime_evidence_001", b"release-runtime-evidence")
    release.update({
        "fixture_only": False, "release_context": "production_runtime", "release_status": raw_release["release_status"],
        "release_id": raw_release["release_id"], "snapshot_sha256": raw_release_digest, "raw_producer_release_ref": raw_release_ref,
        "published_at": raw_release["published_at"], "genuine_runtime_evidence_refs": [release_evidence],
        "producer_source": {"repository_id": raw_release["producer"]["repository_id"], "commit_sha": raw_release["producer"]["git_commit"], "tag": "maskfactory_frozen_planning_fixture", "source_clean": True},
        "contract_bindings": [{
            "wire_schema_name": value["name"], "schema_id": value["schema_id"], "schema_version": value["version"],
            "schema_sha256": value["sha256"], "schema_source": f"maskfactory_release://contracts/{value['name']}.schema.json",
        } for value in raw_release["wire_schemas"]],
        "component_bindings": _release_component_bindings(raw_release),
        "capability_refs": [builder.ref("maskfactory_capability_snapshot", raw_capability["snapshot_id"], "0")],
        "artifact_refs": [builder.ref("producer_release_artifact", f"release_artifact_{index:03d}", str(index % 10)) for index, _ in enumerate(raw_release["artifacts"])] + [builder.ref("producer_evidence_index", raw_release["evidence_index"]["inventory_id"], "e")],
        "certificate_refs": [builder.ref("producer_certificate_index", "certificate_index", "c"), builder.ref("producer_revocation_index", "revocation_index", "d")],
        "revocation_refs": [],
        "release_signature": raw_release["signature"]["value_base64"],
        "signature_trust": copy.deepcopy(trusts["maskfactory_release_signer"]),
        "normalization_signature_trust": copy.deepcopy(trusts["main_normalization_signer"]),
    })
    release["capability_refs"][0]["sha256"] = raw_release["capability_snapshot"]["payload_sha256"]
    for ref_value, raw_artifact in zip(release["artifact_refs"], raw_release["artifacts"]):
        ref_value["sha256"] = raw_artifact["sha256"]
    release["artifact_refs"][-1]["sha256"] = raw_release["evidence_index"]["sha256"]
    release["certificate_refs"][0]["sha256"] = raw_release["certificate_index"]["sha256"]
    release["certificate_refs"][1]["sha256"] = raw_release["certificate_index"]["revocation_index_sha256"]
    builder.seal_normalized_release(release)
    normalizer_id = role_keys["main_normalization_signer"]
    release["normalization_signature"] = sign_runtime_payload(runtime_context, release["normalization_signature_domain"], release["normalization_payload_sha256"], normalizer_id)
    normalized_release_ref = builder.immutable_release_ref(release)
    runtime_context["artifact_bytes"][builder.immutable_ref_key(normalized_release_ref)] = builder.normalized_release_payload_bytes(release)
    runtime_context["adopted_main_release_ref"] = copy.deepcopy(normalized_release_ref)

    adoption_evidence = add_runtime_artifact(builder, runtime_context, "runtime_evidence", "adoption_runtime_evidence_001", b"adoption-runtime-evidence")
    adoption.update({
        "fixture_only": False, "adoption_context": "production_runtime", "decision": "adopted", "mismatch_codes": [],
        "decided_at": "2026-07-17T02:21:00-05:00", "valid_until": "2026-07-18T02:21:00-05:00", "use_time_recheck_required": True,
        "production_consumption_allowed": True, "active_pin_written": True,
        "release_snapshot_ref": normalized_release_ref, "release_signature_trust": copy.deepcopy(trusts["maskfactory_release_signer"]),
        "adoption_signature_trust": copy.deepcopy(trusts["main_adoption_signer"]), "all_required_signatures_trusted": True,
        "genuine_runtime_evidence_refs": [adoption_evidence],
        "producer_journal_checkpoint_binding": {
            "source_release_ref": raw_release_ref, "release_payload_sha256": raw_release_digest,
            **raw_release["journal_checkpoint"], "producer_and_main_journal_domains_are_separate": True,
        },
    })
    adoption["checks"] = [
        {"check": check_id, "status": "pass", "expected": "exact", "observed": "exact", "evidence_ref": add_runtime_artifact(builder, runtime_context, "compatibility_evidence", f"{check_id}_runtime_evidence", f"{check_id}:pass".encode())}
        for check_id in builder.REQUIRED_ADOPTION_CHECK_IDS
    ]
    main_journal_trust = trusts["main_journal_checkpoint_signer"]
    adoption["journal_pin"] = builder.fixture_journal_pin(trusted=True)
    adoption["journal_pin"].update({
        "stream_id": "main-maskfactory-bridge-journal", "checkpoint_sequence": 7,
        "head_event_sha256": builder.h("9"), "checkpointed_at": "2026-07-17T02:20:30-05:00", "fresh_until": "2026-07-18T02:20:30-05:00",
        "checkpoint_signature_trust": copy.deepcopy(main_journal_trust),
    })
    checkpoint_bytes = builder.journal_checkpoint_payload(adoption["journal_pin"])
    checkpoint_ref = add_runtime_artifact(builder, runtime_context, "main_maskfactory_journal_checkpoint", "checkpoint_runtime_001", checkpoint_bytes)
    adoption["journal_pin"]["checkpoint_ref"] = checkpoint_ref
    adoption["journal_pin"]["checkpoint_payload_sha256"] = checkpoint_ref["sha256"]
    adoption["journal_pin"]["checkpoint_signature"] = sign_runtime_payload(runtime_context, adoption["journal_pin"]["checkpoint_signature_domain"], checkpoint_ref["sha256"], role_keys["main_journal_checkpoint_signer"])
    adoption["capability_snapshot_ref"] = capability_ref
    adoption["capability_snapshot_status"] = "current"
    adoption["capability_observed_at"] = "2026-07-17T02:20:00-05:00"
    adoption["capability_valid_until"] = "2026-07-18T02:20:00-05:00"
    adoption["capability_revocation_checked_at"] = "2026-07-17T02:20:30-05:00"
    adoption["capability_revocation_valid_until"] = "2026-07-18T02:20:30-05:00"
    adoption["capability_status_evidence_ref"] = add_runtime_artifact(builder, runtime_context, "capability_status_evidence", "capability_status_runtime_001", b"capability-current-and-unrevoked")
    adoption["operational_certificate_evaluations"] = [{
        "certificate_ref": add_runtime_artifact(builder, runtime_context, "operational_autonomy_certificate", "bridge_runtime_certificate_001", b"active-bridge-runtime-certificate"),
        "status": "active", "issued_at": "2026-07-17T02:20:00-05:00", "expires_at": "2026-07-18T02:20:00-05:00",
        "revocation_checked_at": "2026-07-17T02:20:30-05:00", "revocation_valid_until": "2026-07-18T02:20:30-05:00",
        "status_evidence_ref": add_runtime_artifact(builder, runtime_context, "certificate_status_evidence", "bridge_runtime_certificate_status_001", b"certificate-active-and-unrevoked"),
    }]
    producer_invalidation_policy = builder.producer_invalidation_policy_document(final_release_binding=True)
    policy_bytes = builder.producer_invalidation_policy_bytes(producer_invalidation_policy)
    policy_ref = builder.producer_invalidation_policy_ref(producer_invalidation_policy)
    runtime_context["artifact_bytes"][builder.immutable_ref_key(policy_ref)] = policy_bytes
    runtime_context.update({"producer_invalidation_policy": producer_invalidation_policy, "producer_invalidation_policy_adopted_from_signed_release": True})
    adoption["producer_invalidation_policy_ref"] = policy_ref
    adoption["producer_invalidation_policy_sha256"] = builder.producer_invalidation_policy_sha256(producer_invalidation_policy)
    builder.seal_adoption_receipt(adoption)
    qualification_bytes = builder.canonical_json({"checks": adoption["checks"]})
    runtime_context["artifact_bytes"][builder.immutable_ref_key(adoption["qualification_bundle_ref"])] = qualification_bytes
    adoption["adoption_signature"] = sign_runtime_payload(runtime_context, adoption["adoption_signature_domain"], adoption["adoption_receipt_sha256"], role_keys["main_adoption_signer"])
    runtime_context["role_keys"] = role_keys
    runtime_context["trusts"] = trusts
    return release, adoption, consumer, trusted_keys, runtime_context


def compiled_runtime_mask_request(builder):
    _, _, _, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    request = producer_fixture("mask_acquisition_request")
    key_id = runtime_context["role_keys"]["main_mask_request_signer"]
    entry = trusted_keys[key_id]
    request["trust_binding"].update({
        "key_role": "consumer_request",
        "signing_key_id": key_id,
        "signing_public_key_sha256": entry["public_key_sha256"],
    })
    digest = builder.maskfactory_document_sha256(request, excluded=("request_payload_sha256", "signature"))
    request["request_payload_sha256"] = digest
    request["signature"] = {
        "algorithm": "ed25519",
        "key_id": key_id,
        "public_key_base64": entry["public_key_base64"],
        "signed_payload_sha256": digest,
        "signed_payload_format": "sha256_digest_bytes",
        "value_base64": sign_runtime_payload(runtime_context, "maskfactory.sha256_digest_bytes.v1", digest, key_id, digest_bytes=True),
    }
    return request, trusted_keys, runtime_context


def reseal_trusted_clock(builder, runtime_context, *, record_id):
    clock = runtime_context["trusted_clock"]
    payload = builder.trusted_clock_payload(clock)
    clock["evidence_ref"] = add_runtime_artifact(builder, runtime_context, "trusted_clock_evidence", record_id, payload)
    clock["payload_sha256"] = builder.sha256_bytes(payload)
    clock["signature"] = sign_runtime_payload(
        runtime_context,
        clock["signature_domain"],
        clock["payload_sha256"],
        runtime_context["role_keys"]["main_trusted_clock_signer"],
    )


def exact_raw_receipt_certificate_projection_bundle(builder):
    raw_receipt = producer_fixture("mask_acquisition_receipt")
    raw_certificate = producer_fixture("operational_autonomy_certificate")
    raw_capability = producer_fixture("maskfactory_capability_snapshot")
    capability_bytes = builder.canonical_json(raw_capability)
    capability_ref = {
        "record_type": raw_capability["record_type"], "record_id": raw_capability["snapshot_id"],
        "revision": "r001", "sha256": builder.sha256_bytes(capability_bytes),
    }
    main_release_ref = builder.ref("maskfactory_release_snapshot_v2", "projection_release_001", "1")
    release_binding = raw_certificate["release_binding"]
    context = {
        "artifact_bytes": {builder.immutable_ref_key(capability_ref): capability_bytes},
        "producer_wire_schema_bytes": {
            name: (producer_root() / f"src/maskfactory/schemas/{name}.schema.json").read_bytes()
            for name in builder.PRODUCER_SCHEMA_BINDINGS
        },
        "adopted_capability_snapshot_ref": capability_ref,
        "adopted_main_release_ref": main_release_ref,
        "adopted_producer_release_binding": {
            "release_id": release_binding["release_id"],
            "release_payload_sha256": release_binding["release_payload_sha256"],
            "capability_snapshot_id": release_binding["capability_snapshot_id"],
            "capability_snapshot_sha256": release_binding["capability_snapshot_sha256"],
            "capability_snapshot_document_sha256": capability_ref["sha256"],
            "bridge_contract": release_binding["bridge_contract"],
            "signing_key_set_id": release_binding["signing_key_set_id"],
            "signing_key_set_version": release_binding["signing_key_set_version"],
            "signing_key_set_sha256": release_binding["signing_key_set_sha256"],
            "rotation_policy_sha256": release_binding["rotation_policy_sha256"],
            "revocation_policy_sha256": release_binding["revocation_policy_sha256"],
        },
        "raw_to_main_certificate_refs": {},
    }
    source = raw_certificate["source_binding"]
    subject = raw_certificate["subject_binding"]
    coordinate = raw_certificate["coordinate_binding"]
    execution = raw_certificate["execution_binding"]
    main_source = {
        "artifact_ref": {"record_type": "image_artifact", "record_id": source["artifact_id"], "revision": "r001", "sha256": source["encoded_sha256"]},
        "sha256": source["encoded_sha256"], "width": source["width"], "height": source["height"],
        "color_space": "srgb", "coordinate_space": "source_pixels",
    }
    main_media = {
        "media_kind": "still_image", "source_media_ref": copy.deepcopy(main_source["artifact_ref"]),
        "source_media_sha256": source["encoded_sha256"], "frame_index": None, "pts_ticks": None,
        "timebase_numerator": None, "timebase_denominator": None, "span_start_frame": None,
        "span_end_frame": None, "neighbor_frame_refs": [], "temporal_evidence_refs": [], "exact_frame_scope_only": True,
    }
    owner = {
        "character_instance_id": subject["scene_instance_id"], "provider_person_index": subject["provider_person_index"],
        "owner_role": "target",
        "assignment_evidence_refs": [{"record_type": "owner_assignment", "record_id": "projection_owner_assignment_001", "revision": "r001", "sha256": subject["assignment_evidence_sha256"]}],
    }
    main_transform = {
        "chain_id": coordinate["transform_chain_id"], "chain_sha256": coordinate["transform_chain_sha256"],
        "canonical_hash_profile": "main_sorted_utf8_json_v2_excluding_self_hash",
        "source": {"coordinate_space": "source_pixels", "width": coordinate["source_width"], "height": coordinate["source_height"]},
        "output": {"coordinate_space": "frame_pixels", "width": coordinate["output_width"], "height": coordinate["output_height"]},
        "steps": [
            {
                "sequence": index, "operation": "identity",
                "input": {"coordinate_space": "source_pixels", "width": coordinate["source_width"], "height": coordinate["source_height"]},
                "output": {"coordinate_space": "frame_pixels", "width": coordinate["output_width"], "height": coordinate["output_height"]},
                "parameters": {"parameter_type": "identity"}, "inverse_strategy": "exact_inverse", "step_sha256": digest,
            }
            for index, digest in enumerate(coordinate["executed_step_sha256s"])
        ],
        "roundtrip_policy": {"required": True, "maximum_error_pixels": coordinate["maximum_roundtrip_error_px"], "reject_noninvertible": True},
        "roundtrip_evidence_refs": [builder.ref("transform_roundtrip_evidence", "projection_roundtrip_001", "e")],
    }
    runtime_manifest = {
        "runtime_kind": execution["runtime_kind"], "runtime_id": execution["runtime_id"], "runtime_version": execution["runtime_version"],
        "operating_system": "Windows", "architecture": "x86_64", "python_version": "3.12",
        "environment_lock_sha256": execution["environment_lock_sha256"],
        "interpreter_build_sha256": execution["interpreter_build_sha256"],
        "venv_manifest_sha256": execution["venv_manifest_sha256"], "container_sha256": execution["container_sha256"],
    }
    runtime_manifest_ref = add_runtime_artifact(builder, context, "runtime_manifest", "projection_runtime_manifest_001", builder.canonical_json(runtime_manifest))
    qa = raw_certificate["qa_evidence"]
    qa_pairs = [
        ("deterministic_report", qa["deterministic_report_sha256"]),
        ("critic_report", qa["critic_report_sha256"]),
        ("ownership_report", qa["ownership_report_sha256"]),
        ("protected_region_report", qa["protected_region_report_sha256"]),
        *[(f"producer_gate:{value['gate_id']}", value["evidence_sha256"]) for value in qa["gate_results"]],
    ]
    critic = qa["critic_binding"]
    critic_hashes = [
        critic["critic_stack_sha256"], critic["workflow_sha256"], critic["execution_fingerprint_sha256"],
        critic["qualification_scope_sha256"], critic["qualification_certificate_sha256"],
        *[value["sha256"] for value in critic["model_artifacts"]],
    ]
    certificate = copy.deepcopy(builder.build_examples()["maskfactory_operational_certificate_v2.example.json"])
    certificate.update({
        "maskfactory_operational_certificate_v2_id": raw_certificate["certificate_id"],
        "fixture_only": raw_certificate["fixture_only"], "certification_context": "fixture_validation",
        "status": raw_certificate["status"], "issued_at": raw_certificate["issued_at"], "expires_at": raw_certificate["expires_at"],
        "access_mode": raw_certificate["access_mode"], "issuer_kind": raw_certificate["issuer_kind"],
        "release_snapshot_ref": main_release_ref, "execution_stack_ref": {"record_type": "execution_stack", "record_id": execution["provider_stack_id"], "revision": "r001", "sha256": execution["provider_stack_sha256"]},
        "source_artifact": main_source, "media_scope": main_media, "owner_bindings": [owner], "transform_chain": main_transform,
        "serving_route_id": "route-fixture", "capability_id": "mask.live.predict",
        "output_refs": [{"record_type": "mask_artifact", "record_id": value["artifact_id"], "revision": "r001", "sha256": value["encoded_sha256"]} for value in raw_certificate["bound_artifacts"]],
        "certificate_scope": builder.exact_certificate_scope_projection(raw_certificate),
        "qa_bindings": [{"gate_id": gate_id, "qa_record_ref": {"record_type": "mask_qa_record", "record_id": f"projection_{index:03d}", "revision": "r001", "sha256": digest}, "result": "pass"} for index, (gate_id, digest) in enumerate(qa_pairs)],
        "evidence_manifest_refs": [{"record_type": "certificate_evidence", "record_id": f"critic_evidence_{index:03d}", "revision": "r001", "sha256": digest} for index, digest in enumerate(critic_hashes)],
        "revocation_manifest_refs": [{"record_type": "revocation_index", "record_id": "projection_revocation_index_001", "revision": "r001", "sha256": raw_certificate["revocation"]["revocation_index_sha256"]}],
        "revocation_ref": None,
        "runtime_provenance": {"runtime_kind": "windows_native_venv", "operating_system": "Windows", "architecture": "x86_64", "python_version": "3.12", "environment_lock_sha256": execution["environment_lock_sha256"], "container_image_digest": execution["container_sha256"], "runtime_manifest_ref": runtime_manifest_ref},
        "raw_producer_certificate_ref": {"record_type": raw_certificate["record_type"], "record_id": raw_certificate["certificate_id"], "revision": "r001", "sha256": raw_certificate["certificate_payload_sha256"]},
        "raw_producer_certificate_payload_sha256": raw_certificate["certificate_payload_sha256"],
        "raw_producer_certificate_signature": raw_certificate["signature"]["value_base64"],
    })
    builder.seal_operational_certificate(certificate)
    certificate_ref = builder.immutable_operational_certificate_ref(certificate)
    context["raw_to_main_certificate_refs"][raw_certificate["certificate_payload_sha256"]] = copy.deepcopy(certificate_ref)

    receipt_subject = raw_receipt["subject_binding"]
    receipt_transform = raw_receipt["transform_validation"]
    authority = {
        "authority_state": raw_receipt["authority"]["authority_state"], "issuer_kind": raw_receipt["authority"]["issuer_kind"],
        "claim_class": "operationally_certified_artifact", "certificate_ref": certificate_ref,
        "certificate_scope": builder.exact_certificate_scope_projection(raw_certificate),
        "verified_at": raw_receipt["completed_at"], "revocation_checked_at": raw_receipt["authority"]["revocation_checked_at"],
    }
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    result.update({
        "maskfactory_bridge_result_v2_id": "projection_result_001", "request_ref": {"record_type": "maskfactory_bridge_request_v2", "record_id": raw_receipt["request_id"], "revision": "r001", "sha256": raw_receipt["request_payload_sha256"]},
        "release_snapshot_ref": main_release_ref, "status": "succeeded", "access_mode": raw_receipt["access_mode"],
        "source_artifact": main_source, "media_scope": main_media,
        "execution_stack_ref": {"record_type": "execution_stack", "record_id": raw_receipt["provider_binding"]["stack_id"], "revision": "r001", "sha256": raw_receipt["provider_binding"]["stack_sha256"]},
        "route_id": raw_receipt["execution_observation"]["route_selection"]["selected_route_id"], "owner_bindings": [owner],
        "transform_chain": main_transform, "roundtrip_max_error_pixels": receipt_transform["maximum_roundtrip_error_px"],
        "authority": authority, "operational_certificate_ref": certificate_ref,
        "qa_record_refs": [{"record_type": "mask_qa_record", "record_id": "projection_receipt_qa_001", "revision": "r001", "sha256": raw_receipt["qa"]["report_sha256"]}],
        "masks": [],
        "input_region_lineage": {
            "target_region_refs": [{"record_type": "input_region", "record_id": value["region_id"], "revision": "r001", "sha256": value["artifact_identity_sha256"]} for value in raw_receipt["lineage"]["input_target_regions"]],
            "protected_region_refs": [{"record_type": "input_region", "record_id": value["region_id"], "revision": "r001", "sha256": value["artifact_identity_sha256"]} for value in raw_receipt["lineage"]["input_protected_regions"]],
            "request_transform_chain_sha256": receipt_transform["transform_chain_sha256"], "input_roi_hashes_are_output_artifact_hashes": False, "mode_a_exact_selector_exception_applied": False,
        },
        "execution_observation": {
            **result["execution_observation"],
            "execution_scope": {"project_id": raw_receipt["project_id"], "run_id": raw_receipt["run_id"], "scene_id": receipt_subject["scene_id"], "shot_id": receipt_subject["shot_id"], "take_id": receipt_subject["take_id"], "job_id": raw_receipt["job_id"], "pass_id": raw_receipt["pass_id"], "attempt_id": raw_receipt["attempt_id"]},
            "attempt_number": raw_receipt["attempt_number"], "hypothesis": {"hypothesis_id": raw_receipt["hypothesis_id"], "hypothesis_class": "initial", "retry_kind": "initial", "material_change_sha256": None},
            "queue_ms": raw_receipt["execution_observation"]["queue_ms"], "runtime_ms": raw_receipt["execution_observation"]["runtime_ms"],
            "peak_vram_mb": raw_receipt["execution_observation"]["resources"]["peak_vram_mb"], "peak_ram_mb": raw_receipt["execution_observation"]["resources"]["peak_ram_mb"],
            "output_bytes": raw_receipt["execution_observation"]["resources"]["output_bytes"], "deadline_met": raw_receipt["execution_observation"]["deadline_met"],
            "selected_route_id": raw_receipt["execution_observation"]["route_selection"]["selected_route_id"],
        },
        "raw_producer_receipt_ref": {"record_type": raw_receipt["record_type"], "record_id": raw_receipt["receipt_id"], "revision": "r001", "sha256": raw_receipt["receipt_payload_sha256"]},
        "raw_producer_receipt_payload_sha256": raw_receipt["receipt_payload_sha256"], "raw_producer_receipt_signature": raw_receipt["signature"]["value_base64"],
    })
    for artifact in raw_receipt["artifacts"]:
        result["masks"].append({
            "mask_ref": {"record_type": "mask_artifact", "record_id": artifact["artifact_id"], "revision": "r001", "sha256": artifact["encoded_sha256"]},
            "mask_sha256": artifact["decoded_mask_sha256"], "label": artifact["label"], "mask_type": "binary",
            "width": artifact["width"], "height": artifact["height"], "coordinate_space": "frame_pixels",
            "owner": copy.deepcopy(owner), "authority": copy.deepcopy(authority), "lineage_kind": "original", "derivation_operation": "none", "parents": [],
        })
    builder.seal_normalized_result(result)
    return raw_receipt, raw_certificate, result, certificate, context


def exact_raw_invalidation_projection(builder):
    raw = producer_fixture("mask_authority_invalidation_event")
    event = copy.deepcopy(builder.build_examples()["maskfactory_invalidation_event_v2.example.json"])
    event.update({
        "fixture_only": raw["fixture_only"], "event_id": raw["event_id"], "stream_id": raw["stream_id"],
        "sequence": raw["sequence"], "causation_id": raw["causation_id"], "idempotency_key": raw["idempotency_key"],
        "created_at": raw["occurred_at"], "effective_at": raw["effective_at"], "reason": raw["reason"],
        "severity": "blocking", "producer_identity": raw["producer"].casefold(), "producer_evidence_sha256": raw["evidence_sha256"],
        "target_transitions": [], "required_actions": copy.deepcopy(raw["required_actions"]),
        "superseding_binding": copy.deepcopy(raw["superseding_binding"]), "rollback_binding": copy.deepcopy(raw["rollback_binding"]),
    })
    for value in raw["target_transitions"]:
        transition = copy.deepcopy(value)
        transition["main_target_ref"] = {"record_type": "maskfactory_operational_certificate_v2", "record_id": value["target_id"], "revision": "r001", "sha256": value["target_sha256"]}
        transition["unrelated_scope_preserved"] = True
        event["target_transitions"].append(transition)
    event["affected_refs"] = [copy.deepcopy(value["main_target_ref"]) for value in event["target_transitions"]]
    builder.seal_invalidation_event(event)
    return raw, event


def production_bridge_release(builder, release, adoption, runtime_context):
    bridge_release = copy.deepcopy(builder.build_examples()["maskfactory_bridge_release_certificate_v2.example.json"])
    bridge_release.update({
        "fixture_only": False, "runtime_completion_claimed": True, "release_context": "production_runtime",
        "status": "released", "release_snapshot_ref": builder.immutable_release_ref(release),
        "adoption_receipt_ref": builder.immutable_adoption_ref(adoption), "row218_runtime_passed": True,
        "rows321_347_runtime_passed": True, "trusted_signing_identity_checks_passed": True,
        "journal_checkpoint_checks_passed": True, "release_allowed": True,
        "genuine_runtime_evidence_refs": [add_runtime_artifact(builder, runtime_context, "runtime_evidence", "row348_runtime_evidence_001", b"row348-runtime-evidence")],
        "release_signature_trust": copy.deepcopy(runtime_context["trusts"]["main_bridge_release_signer"]),
    })
    bridge_release["journal_pin"] = copy.deepcopy(adoption["journal_pin"])
    bridge_release["checks"] = [builder.fixture_release_gate_report(gate_id, passed=True, trusted=True, runtime=True) for gate_id in builder.REQUIRED_BRIDGE_RELEASE_GATE_IDS]
    for check in bridge_release["checks"]:
        check["signature_trust"] = copy.deepcopy(runtime_context["trusts"]["main_bridge_gate_signer"])
        check["evaluator_manifest_ref"] = add_runtime_artifact(builder, runtime_context, "gate_evaluator_manifest", f"{check['gate_id']}_evaluator", f"{check['gate_id']}:evaluator".encode("utf-8"))
        check["evidence_refs"] = [add_runtime_artifact(builder, runtime_context, "gate_evidence", f"{check['gate_id']}_evidence", f"{check['gate_id']}:evidence".encode("utf-8"))]
        check["genuine_runtime_evidence_refs"] = [add_runtime_artifact(builder, runtime_context, "runtime_gate_evidence", f"{check['gate_id']}_runtime_evidence", f"{check['gate_id']}:runtime".encode("utf-8"))]
        builder.seal_release_gate_report(check)
        check["gate_report_signature"] = sign_runtime_payload(
            runtime_context,
            check["signature_domain"],
            check["gate_report_sha256"],
            runtime_context["role_keys"]["main_bridge_gate_signer"],
        )
    builder.seal_bridge_release_certificate(bridge_release)
    bridge_release["release_signature"] = sign_runtime_payload(
        runtime_context,
        bridge_release["release_signature_domain"],
        bridge_release["release_certificate_sha256"],
        runtime_context["role_keys"]["main_bridge_release_signer"],
    )
    return bridge_release


def production_readiness_bundle(builder):
    release, adoption, consumer, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    bridge_release = production_bridge_release(builder, release, adoption, runtime_context)
    readiness = copy.deepcopy(builder.build_examples()["maskfactory_bridge_readiness_projection_v2.example.json"])
    readiness.update({
        "fixture_only": False,
        "runtime_completion_claimed": True,
        "runtime_readiness_claimed": True,
        "release_snapshot_ref": builder.immutable_release_ref(release),
        "adoption_receipt_ref": builder.immutable_adoption_ref(adoption),
        "bridge_release_certificate_ref": builder.immutable_bridge_release_ref(bridge_release),
        "active_pin_status": "active",
        "row218_status": "passed",
        "rows321_347_status": "passed",
        "row348_release_status": "released",
        "signing_trust_status": "trusted",
        "journal_integrity_status": "trusted_current",
        "core_blockers": [],
        "optional_profile_blockers": [],
        "blockers": [],
    })
    for profile in readiness["profile_readiness"]:
        if profile["completion_profile"] == "core_autonomous_runtime":
            profile["status"] = "ready"
            profile["evidence_refs"] = [builder.immutable_bridge_release_ref(bridge_release)]
    checks = {check["gate_id"]: check for check in bridge_release["checks"]}
    for page in readiness["page_readiness"]:
        page["status"] = "ready"
        page["blocker_codes"] = []
        page["evidence_refs"] = [
            builder.immutable_bridge_release_ref(bridge_release),
            *[copy.deepcopy(checks[gate_id]["gate_report_ref"]) for gate_id in builder.APP_PAGE_GATE_IDS[page["page_id"]]],
        ]
    runtime_refs = [
        *release["genuine_runtime_evidence_refs"], *adoption["genuine_runtime_evidence_refs"],
        *bridge_release["genuine_runtime_evidence_refs"],
        *[value for check in bridge_release["checks"] for value in check["genuine_runtime_evidence_refs"]],
    ]
    readiness["genuine_runtime_evidence_refs"] = list({builder.immutable_ref_key(value): value for value in runtime_refs}.values())
    readiness["journal_pin"] = copy.deepcopy(adoption["journal_pin"])
    readiness["event_cursor"] = {"stream_id": readiness["journal_pin"]["stream_id"], "last_sequence": readiness["journal_pin"]["checkpoint_sequence"], "last_event_sha256": readiness["journal_pin"]["head_event_sha256"]}
    return readiness, release, adoption, bridge_release, consumer, trusted_keys, runtime_context


def validate_production_readiness(builder, bundle):
    readiness, release, adoption, bridge_release, consumer, trusted_keys, runtime_context = bundle
    builder.validate_readiness_projection(
        readiness, release_snapshot=release, adoption=adoption, bridge_release=bridge_release,
        consumer=consumer, trusted_keys=trusted_keys, runtime_verification_context=runtime_context, use_time=runtime_context["use_time"],
    )


def test_mode_b_can_be_certified_only_with_exact_operational_certificate(builder, contracts):
    schemas, registry = contracts
    result, certificate = certified_mode_b_pair(builder)
    assert not errors_for(schemas["maskfactory_bridge_result_v2.schema.json"], result, registry)
    builder.validate_result_certificate_pair(result, certificate)


def test_mode_b_certified_without_certificate_is_rejected(builder, contracts):
    schemas, registry = contracts
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    result["authority"] = builder.fixture_authority("certified", "maskfactory_autonomous", True)
    result["operational_certificate_ref"] = None
    assert errors_for(schemas["maskfactory_bridge_result_v2.schema.json"], result, registry)


def test_operational_certificate_output_mismatch_fails(builder):
    result, certificate = certified_mode_b_pair(builder)
    certificate["output_refs"][0]["sha256"] = builder.h("9")
    with pytest.raises(ValueError, match="output mismatch|canonical hash"):
        builder.validate_result_certificate_pair(result, certificate)


def test_operational_certificate_binds_required_manifests(builder):
    certificate = builder.build_examples()["maskfactory_operational_certificate_v2.example.json"]
    required = {"certification_context", "claim_class", "release_snapshot_ref", "capability_id", "serving_route_id", "access_mode", "execution_stack_ref", "runtime_provenance", "source_artifact", "media_scope", "output_refs", "owner_bindings", "transform_chain", "qa_bindings", "promotion_gate_policy_ref", "evidence_manifest_refs", "genuine_runtime_evidence_refs", "revocation_manifest_refs", "signature", "signature_trust"}
    assert required.issubset(certificate)


def test_mode_a_draft_does_not_auto_promote(builder, contracts):
    schemas, registry = contracts
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    result["access_mode"] = "mode_a_package_read"
    result["authority"] = builder.fixture_authority("draft")
    assert not errors_for(schemas["maskfactory_bridge_result_v2.schema.json"], result, registry)


def test_normalized_result_cannot_self_declare_policy_eligibility(builder, contracts):
    schemas, registry = contracts
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    result["can_satisfy_promotion_gate"] = True
    assert errors_for(schemas["maskfactory_bridge_result_v2.schema.json"], result, registry)


def test_policy_scoped_authority_decision_allows_draft_preview(builder):
    decision = copy.deepcopy(builder.build_examples()["maskfactory_authority_decision_v2.example.json"])
    policy = production_policy(builder)
    decision["fixture_only"] = False
    decision["decision"] = "eligible"
    decision["eligible_for_intended_use"] = True
    decision["genuine_runtime_evidence_refs"] = [builder.ref("runtime_evidence", "preview_decision_runtime_evidence_001", "d")]
    decision["consumer_policy_ref"] = copy.deepcopy(policy["policy_artifact_ref"])
    decision["consumer_policy_sha256"] = policy["policy_sha256"]
    assert decision["intended_use"] == "preview"
    assert decision["required_authority_state"] == "draft"
    assert decision["eligible_for_intended_use"] is True
    builder.validate_authority_decision_record(decision, trusted_keys={"maskfactory_production_signer_001": builder.h("d")}, policy=policy)


def test_policy_scoped_decision_rejects_insufficient_authority(builder):
    decision = copy.deepcopy(builder.build_examples()["maskfactory_authority_decision_v2.example.json"])
    decision["intended_use"] = "promotion_bound"
    decision["required_authority_state"] = "certified"
    decision["decision"] = "eligible"
    decision["eligible_for_intended_use"] = True
    with pytest.raises(ValueError, match="fixture authority decision"):
        builder.validate_authority_decision_record(decision)


def test_structured_promotion_policy_supersedes_live_dial_and_strings(builder):
    policy = builder.build_examples()["maskfactory_promotion_gate_policy_v2.example.json"]
    assert policy["policy_version"] == "2.0.0"
    assert policy["live_qa_strictness_control_authoritative"] is False
    assert policy["runtime_policy_mutable_from_app"] is False
    assert policy["legacy_string_gate_authoritative"] is False
    assert policy["optional_independent_accuracy_can_mutate_core_decision"] is False
    for criterion in policy["criteria"]:
        assert {"criterion_id", "dimension", "comparator", "threshold", "evidence_type", "analyzer_manifest_ref", "blocking"}.issubset(criterion)


def test_legacy_migration_crosswalk_is_fail_closed(builder):
    migration = builder.build_registries()["wave64_maskfactory_bridge_legacy_migration_crosswalk_v2.json"]
    assert {entry["legacy_surface"] for entry in migration["migrations"]} == {
        "Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md#qa_strictness_live_control",
        "Plan/08_SCHEMAS/mask_factory_contract.schema.json#promotion_gates_string_array",
        "Plan/Tracker/README.md#wave70_manual_gold_blocker",
        "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md#gold_mask_dependency",
        "Plan/Items/Reports/ITEM-W64-012_image_mask_control.json",
    }
    assert all(entry["validator_required"] for entry in migration["migrations"])
    assert migration["legacy_string_gate_can_authorize_promotion"] is False
    assert migration["live_qa_dial_can_mutate_core_decision"] is False
    historical = next(entry for entry in migration["migrations"] if entry["legacy_surface"].endswith("ITEM-W64-012_image_mask_control.json"))
    assert historical["historical_evidence_mutable"] is False
    assert "cannot block core" in historical["migration_rule"]


def test_consumer_binds_schema_source_version_hash_and_certificate_scope(builder):
    consumer = builder.build_examples()["maskfactory_consumer_requirements_v2.example.json"]
    for binding in consumer["required_contract_bindings"]:
        assert {"wire_schema_name", "schema_source", "schema_id", "schema_version", "schema_sha256"}.issubset(binding)
    assert consumer["allowed_issuer_kinds"] == ["maskfactory_autonomous", "human_anchor_optional"]
    assert consumer["required_certificate_scope"]
    assert {binding["wire_schema_name"] for binding in consumer["required_contract_bindings"]} == {"mask_acquisition_request", "mask_acquisition_receipt", "operational_autonomy_certificate"}
    assert all(binding["schema_source"].startswith("maskfactory_release://") for binding in consumer["required_contract_bindings"])


def test_contract_catalog_distinguishes_producer_wire_from_main_internal(builder):
    catalog = builder.build_registries()["wave64_maskfactory_bridge_contract_catalog_v2.json"]
    assert all(entry["owner"] == "main_controller" for entry in catalog["contracts"])
    assert all(entry["producer_wire_authority"] is False for entry in catalog["contracts"])
    assert all(entry["schema_owner"] == "maskfactory" and entry["surface"] == "producer_wire_v1" for entry in catalog["producer_wire_contracts"])
    assert catalog["unknown_or_missing_producer_mapping_fails_closed"] is True
    assert catalog["producer_planning_provenance"] == {
        "repository": "KevinSGarrett/MaskingUltimate", "branch": "codex/mask-autonomy-bridge-plan",
        "commit": "938b469", "pull_request": "https://github.com/KevinSGarrett/MaskingUltimate/pull/2",
        "planning_preservation_manifest_sha256": "13fda3eab823e4a544f171c5570ceed99e77cd246ccbc13e686879616682bde2",
        "planning_manifest_entries": 113, "wire_schema_count": 12,
        "immutable_producer_packet_commit": "938b46949e277d92f26d9411fd5710005c506677",
        "integration_head": "e6d6c6bdf00a0702d274455fbf07ded2b3a838b3",
        "current_pr_validation_head": "6361df208e01d183083ee6c113e016467a486706",
        "integration_base_commit": "85d4c19b7974c1b64f48176d91211defbaba35a0",
        "integration_strategy": "non_rewriting_merge_commit",
        "integration_reconciliation_manifest": "Plan/Instructions/11_AUTONOMOUS_CORE_BRIDGE_INTEGRATION_RECONCILIATION_MANIFEST.json",
        "integration_reconciliation_manifest_sha256": "c948da1595f6c29ead2aeda950ac778717c6557f2ed5f6c4b0664e5052f3eb52",
        "base_owned_supersession_count": 6, "integration_protocol_update_count": 2,
        "unaccounted_integration_drift_count": 0, "wire_schemas_unchanged_after_integration": True,
        "planning_bindings_finalized": True,
        "runtime_release_state": "unpublished_unadopted", "runtime_release_is_required_before_production_adoption": True,
    }
    deferral = catalog["model_library_dependency_deferral"]
    assert deferral["current_state"] == "deferred_waiting_for_complete_model_download"
    assert deferral["all_7282_record_dry_run_ingestion_deferred"] is True
    assert deferral["bridge_cannot_clear_or_bypass_deferral"] is True


def test_every_producer_wire_contract_has_exact_main_mapping(builder):
    schemas = builder.build_schemas()
    registries = builder.build_registries(schemas)
    catalog_names = {entry["contract_name"] for entry in registries["wave64_maskfactory_bridge_contract_catalog_v2.json"]["producer_wire_contracts"]}
    mapping = registries["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"]
    mapped_names = {entry["producer_contract_name"] for entry in mapping["mappings"]}
    assert mapped_names == catalog_names
    assert mapping["unknown_or_missing_mapping_action"] == "block_dependent_pass"
    assert all(entry["exact_producer_binding_required"] for entry in mapping["mappings"])


def test_executable_mapping_is_schema_valid_hash_bound_and_field_complete(builder, contracts):
    schemas, registry = contracts
    mapping = builder.build_registries(schemas)["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"]
    schema = schemas["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json"]
    assert not errors_for(schema, mapping, registry)
    assert mapping["mapping_schema_binding"]["schema_sha256"] == hashlib.sha256(builder.canonical_json(schema)).hexdigest()
    builder.validate_mapping_registry(mapping, schemas)
    for entry in mapping["mappings"]:
        producer_paths = {f"$.{name}" for name in builder.PRODUCER_SCHEMA_BINDINGS[entry["producer_contract_name"]]["properties"]}
        producer_required_paths = {f"$.{name}" for name in builder.PRODUCER_SCHEMA_BINDINGS[entry["producer_contract_name"]].get("required", builder.PRODUCER_SCHEMA_BINDINGS[entry["producer_contract_name"]]["properties"])}
        assert set(entry["covered_producer_top_level_paths"]) == producer_paths
        assert set(entry["producer_required_paths"]) == producer_required_paths
        assert entry["unknown_source_field_action"] == "reject"
        assert entry["unknown_target_field_action"] == "reject"
        assert entry["unmapped_required_field_action"] == "block_dependent_pass"
        assert any(rule["disposition"] == "reject" for rule in entry["field_rules"])
        assert all({"source_path", "target_path", "source_required", "target_required", "disposition", "transform", "authority"}.issubset(rule) for rule in entry["field_rules"])
        assert all(rule["transform"]["unmapped_enum_action"] == "reject" for rule in entry["field_rules"])
        assert all(rule["authority"]["may_elevate_authority"] is False for rule in entry["field_rules"])


def _schema_literal_values(fragment):
    values = set(fragment.get("enum", []))
    if "const" in fragment:
        values.add(fragment["const"])
    if fragment.get("type") == "boolean":
        values.update({True, False})
    if isinstance(fragment.get("items"), dict):
        values.update(_schema_literal_values(fragment["items"]))
    for key in ("oneOf", "anyOf", "allOf"):
        for branch in fragment.get(key, []):
            values.update(_schema_literal_values(branch))
    return values


def _nested_schema_enum_sets(fragment):
    sets = []
    direct_fragment = {key: value for key, value in fragment.items() if key not in {"properties", "items", "oneOf", "anyOf", "allOf"}}
    direct = _schema_literal_values(direct_fragment)
    if direct:
        sets.append({str(value).lower() if isinstance(value, bool) else value for value in direct})
    if isinstance(fragment.get("properties"), dict):
        for child in fragment["properties"].values():
            sets.extend(_nested_schema_enum_sets(child))
    if isinstance(fragment.get("items"), dict):
        sets.extend(_nested_schema_enum_sets(fragment["items"]))
    for key in ("oneOf", "anyOf", "allOf"):
        for child in fragment.get(key, []):
            sets.extend(_nested_schema_enum_sets(child))
    return sets


def _resolve_local_schema_ref(schema, fragment):
    while isinstance(fragment, dict) and isinstance(fragment.get("$ref"), str) and fragment["$ref"].startswith("#/"):
        resolved = schema
        for token in fragment["$ref"][2:].split("/"):
            resolved = resolved[token.replace("~1", "/").replace("~0", "~")]
        fragment = resolved
    return fragment


def test_every_named_enum_map_covers_its_exact_source_enum(builder):
    mapping = builder.build_registries()["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"]
    main_schemas = builder.build_schemas()
    for entry in mapping["mappings"]:
        if entry["direction"] == "maskfactory_to_main":
            source_schema = json.loads((producer_root() / f"src/maskfactory/schemas/{entry['producer_contract_name']}.schema.json").read_text(encoding="utf-8"))
        else:
            source_schema = next(
                schema for schema in main_schemas.values()
                if schema.get("$id") == entry["main_binding"]["schema_id"]
            )
        source_contract = source_schema
        if entry["direction"] == "main_to_maskfactory" and "#" in entry["main_binding"]["schema_source"]:
            fragment = "#" + entry["main_binding"]["schema_source"].split("#", 1)[1]
            source_contract = _resolve_local_schema_ref(source_schema, {"$ref": fragment})
        for rule in entry["field_rules"]:
            transform = rule["transform"]
            if transform["operation"] != "enum_map" or not rule["source_path"].startswith("$."):
                continue
            property_name = rule["source_path"][2:]
            assert "." not in property_name
            source_fragment = _resolve_local_schema_ref(source_schema, source_contract["properties"][property_name])
            allowed = _schema_literal_values(source_fragment)
            expected_keys = {str(value).lower() if isinstance(value, bool) else value for value in allowed}
            if expected_keys:
                assert set(transform["enum_conversion"]) == expected_keys, rule["field_rule_id"]
            else:
                nested_sets = _nested_schema_enum_sets(source_fragment)
                if nested_sets:
                    assert set(transform["enum_conversion"]) in nested_sets, rule["field_rule_id"]
                else:
                    assert transform["enum_conversion"] and transform["unmapped_enum_action"] == "reject"


def test_coordinate_space_projection_covers_every_frozen_producer_enum(builder):
    expected = {
        "source_pixel": "source_pixels",
        "crop_pixel": "working_pixels",
        "output_pixel": "frame_pixels",
        "normalized_0_1": "normalized_0_1",
    }
    assert builder.PRODUCER_TO_MAIN_COORDINATE_SPACE == expected
    observed = set()
    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if "coordinate_space" in key and isinstance(child, dict):
                    observed.update(child.get("enum", []))
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for contract_name in builder.PRODUCER_SCHEMA_BINDINGS:
        visit(json.loads((producer_root() / f"src/maskfactory/schemas/{contract_name}.schema.json").read_text(encoding="utf-8")))
    assert observed == set(expected)
    common = builder.build_schemas()["wave64_maskfactory_bridge_common_v2.schema.json"]
    assert set(common["$defs"]["coordinate_state"]["properties"]["coordinate_space"]["enum"]) == set(expected.values())


def test_producer_use_eligibility_is_dropped_and_recomputed_by_main(builder):
    mapping = builder.build_registries()["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"]
    policy = mapping["producer_use_eligibility_policy"]
    assert policy["source_path"] == "$.use_eligibility"
    assert policy["producer_value_authoritative_for_main_use"] is False
    assert policy["normalization_action"] == "drop_after_validation"
    assert policy["main_recompute_contract_binding"]["contract_name"] == "maskfactory_authority_decision_v2"
    assert policy["main_target_path"] == "$.eligible_for_intended_use"
    receipt_mapping = next(entry for entry in mapping["mappings"] if entry["producer_contract_name"] == "mask_acquisition_receipt")
    use_rule = next(rule for rule in receipt_mapping["field_rules"] if rule["source_path"] == "$.use_eligibility")
    assert use_rule["disposition"] == "drop"
    assert use_rule["target_path"] is None


def test_derived_lineage_without_parent_is_schema_rejected(builder, contracts):
    schemas, registry = contracts
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    result["masks"][0]["lineage_kind"] = "derived"
    result["masks"][0]["derivation_operation"] = "refine"
    result["masks"][0]["parents"] = []
    assert errors_for(schemas["maskfactory_bridge_result_v2.schema.json"], result, registry)


def test_original_lineage_with_parent_is_schema_rejected(builder, contracts):
    schemas, registry = contracts
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    parent_authority = builder.fixture_authority()
    result["masks"][0]["parents"] = [{"parent_mask_ref": builder.ref("mask_artifact", "parent_mask_fixture_001", "e"), "parent_authority": parent_authority, "parent_operational_certificate_ref": None}]
    assert errors_for(schemas["maskfactory_bridge_result_v2.schema.json"], result, registry)


def test_derived_child_authority_cannot_exceed_any_parent(builder):
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    child_authority = builder.fixture_authority("certified", "maskfactory_autonomous", True)
    parent_authority = builder.fixture_authority("draft")
    result["authority"] = copy.deepcopy(child_authority)
    result["masks"][0]["authority"] = child_authority
    result["masks"][0]["lineage_kind"] = "derived"
    result["masks"][0]["derivation_operation"] = "refine"
    result["masks"][0]["parents"] = [{"parent_mask_ref": builder.ref("mask_artifact", "parent_mask_fixture_001", "e"), "parent_authority": parent_authority, "parent_operational_certificate_ref": None}]
    with pytest.raises(ValueError, match="exceeds parent authority"):
        builder.validate_mask_lineage(result)


def test_parent_certificate_reference_must_match_parent_authority(builder):
    result = copy.deepcopy(builder.build_examples()["maskfactory_bridge_result_v2.example.json"])
    parent_authority = builder.fixture_authority("draft")
    result["masks"][0]["lineage_kind"] = "derived"
    result["masks"][0]["derivation_operation"] = "refine"
    result["masks"][0]["parents"] = [{"parent_mask_ref": builder.ref("mask_artifact", "parent_mask_fixture_001", "e"), "parent_authority": parent_authority, "parent_operational_certificate_ref": builder.ref("maskfactory_operational_certificate_v2", "wrong_parent_certificate", "f")}]
    with pytest.raises(ValueError, match="does not match parent authority"):
        builder.validate_mask_lineage(result)


def test_cross_character_protected_region_is_preserved_with_explicit_roster(builder):
    request = copy.deepcopy(builder.build_examples()["maskfactory_bridge_request_v2.example.json"])
    protected = request["protected_region_bindings"][0]
    assert protected["relationship_to_target"] == "other_character"
    assert protected["owner_entity_id"] != request["scene_owner_roster"]["target_character_instance_id"]
    builder.validate_request_ownership(request)


def test_ambiguous_or_unrostered_protected_owner_fails_closed(builder):
    request = copy.deepcopy(builder.build_examples()["maskfactory_bridge_request_v2.example.json"])
    request["protected_region_bindings"][0]["owner_entity_id"] = "character_instance_not_in_roster"
    with pytest.raises(ValueError, match="absent from the scene roster"):
        builder.validate_request_ownership(request)
    request = copy.deepcopy(builder.build_examples()["maskfactory_bridge_request_v2.example.json"])
    request["protected_region_bindings"][0]["owner_entity_id"] = request["scene_owner_roster"]["target_character_instance_id"]
    with pytest.raises(ValueError, match="ambiguously aliases the target"):
        builder.validate_request_ownership(request)


def test_input_roi_hash_cannot_be_reused_as_generated_output_hash(builder):
    examples = builder.build_examples()
    request = copy.deepcopy(examples["maskfactory_bridge_request_v2.example.json"])
    result = copy.deepcopy(examples["maskfactory_bridge_result_v2.example.json"])
    result["masks"][0]["mask_sha256"] = request["target_region_bindings"][0]["region_sha256"]
    result["masks"][0]["mask_ref"]["sha256"] = result["masks"][0]["mask_sha256"]
    result["input_region_lineage"]["input_roi_hashes_are_output_artifact_hashes"] = True
    with pytest.raises(ValueError, match="cannot be conflated"):
        builder.validate_request_result_pair(request, result)


def test_mode_a_exact_package_selector_is_the_only_input_output_hash_exception(builder):
    examples = builder.build_examples()
    request = copy.deepcopy(examples["maskfactory_bridge_request_v2.example.json"])
    result = copy.deepcopy(examples["maskfactory_bridge_result_v2.example.json"])
    request["access_mode"] = "mode_a_package_read"
    result["access_mode"] = "mode_a_package_read"
    request["target_region_bindings"][0]["selector_kind"] = "mode_a_exact_package_artifact"
    result["masks"][0]["mask_sha256"] = request["target_region_bindings"][0]["region_sha256"]
    result["masks"][0]["mask_ref"]["sha256"] = result["masks"][0]["mask_sha256"]
    result["input_region_lineage"]["input_roi_hashes_are_output_artifact_hashes"] = True
    result["input_region_lineage"]["mode_a_exact_selector_exception_applied"] = True
    builder.validate_request_result_pair(request, result)


def test_transform_chain_requires_typed_executable_continuity_and_roundtrip(builder):
    chain = copy.deepcopy(builder.fixture_transform())
    chain["steps"][0]["parameters"] = {"parameter_type": "crop", "x": 0, "y": 0, "width": 1024, "height": 1024}
    with pytest.raises(ValueError, match="typed parameters"):
        builder.validate_transform_chain(chain)
    chain = copy.deepcopy(builder.fixture_transform())
    chain["steps"][0]["input"]["width"] = 512
    with pytest.raises(ValueError, match="continuity"):
        builder.validate_transform_chain(chain)
    chain = copy.deepcopy(builder.fixture_transform())
    chain["roundtrip_policy"]["reject_noninvertible"] = False
    with pytest.raises(ValueError, match="roundtrip"):
        builder.validate_transform_chain(chain)
    chain = copy.deepcopy(builder.fixture_transform())
    chain["steps"][0]["step_sha256"] = builder.h("0")
    with pytest.raises(ValueError, match="step canonical hash"):
        builder.validate_transform_chain(chain)
    chain = copy.deepcopy(builder.fixture_transform())
    chain["chain_sha256"] = builder.h("0")
    with pytest.raises(ValueError, match="chain canonical hash"):
        builder.validate_transform_chain(chain)
    chain = copy.deepcopy(builder.fixture_transform())
    chain["roundtrip_evidence_refs"] = []
    with pytest.raises(ValueError, match="roundtrip evidence"):
        builder.validate_transform_chain(chain)


@pytest.mark.parametrize("mutation", ["source_hash", "chain_hash", "step_sequence", "coordinate_dimensions"])
def test_input_regions_are_exactly_bound_to_source_and_transform(builder, mutation):
    request = copy.deepcopy(builder.build_examples()["maskfactory_bridge_request_v2.example.json"])
    region = request["target_region_bindings"][0]
    if mutation == "source_hash":
        region["source_artifact_sha256"] = builder.h("0")
    elif mutation == "chain_hash":
        region["transform_chain_sha256"] = builder.h("0")
    elif mutation == "step_sequence":
        region["transform_step_sequence"] = 99
    else:
        region["width"] = 512
    with pytest.raises(ValueError):
        builder.validate_request_ownership(request)


def test_execution_observation_enforces_deadline_resource_and_route_facts(builder):
    examples = builder.build_examples()
    request = copy.deepcopy(examples["maskfactory_bridge_request_v2.example.json"])
    result = copy.deepcopy(examples["maskfactory_bridge_result_v2.example.json"])
    result["execution_observation"]["runtime_ms"] = request["resource_envelope"]["maximum_runtime_ms"] + 1
    with pytest.raises(ValueError, match="deadline or resource envelope"):
        builder.validate_request_result_pair(request, result)
    result = copy.deepcopy(examples["maskfactory_bridge_result_v2.example.json"])
    result["execution_observation"]["selected_route_id"] = "different_route"
    with pytest.raises(ValueError, match="selected route"):
        builder.validate_request_result_pair(request, result)


def test_native_runtime_never_requires_fake_container_digest(builder):
    certificate = copy.deepcopy(builder.build_examples()["maskfactory_operational_certificate_v2.example.json"])
    builder.validate_operational_certificate_record(certificate)
    certificate["runtime_provenance"]["container_image_digest"] = "sha256:" + builder.h("a")
    builder.seal_operational_certificate(certificate)
    with pytest.raises(ValueError, match="must not fabricate"):
        builder.validate_operational_certificate_record(certificate)
    certificate["runtime_provenance"]["runtime_kind"] = "container"
    certificate["runtime_provenance"]["container_image_digest"] = None
    builder.seal_operational_certificate(certificate)
    with pytest.raises(ValueError, match="requires an exact image digest"):
        builder.validate_operational_certificate_record(certificate)


def test_media_scope_cannot_cross_frames_or_drop_temporal_evidence(builder):
    result, certificate = certified_mode_b_pair(builder)
    result["media_scope"] = {
        "media_kind": "video_frame", "source_media_ref": builder.ref("video_artifact", "video_fixture_001", "a"), "source_media_sha256": builder.h("a"),
        "frame_index": 10, "pts_ticks": 1000, "timebase_numerator": 1, "timebase_denominator": 1000, "span_start_frame": None, "span_end_frame": None,
        "neighbor_frame_refs": [builder.ref("video_frame", "video_frame_009", "b")], "temporal_evidence_refs": [builder.ref("temporal_evidence", "temporal_evidence_010", "c")], "exact_frame_scope_only": True,
    }
    certificate["media_scope"] = copy.deepcopy(result["media_scope"])
    builder.seal_operational_certificate(certificate)
    certificate_ref = builder.immutable_operational_certificate_ref(certificate)
    result["operational_certificate_ref"] = copy.deepcopy(certificate_ref)
    result["authority"]["certificate_ref"] = copy.deepcopy(certificate_ref)
    result["masks"][0]["authority"]["certificate_ref"] = copy.deepcopy(certificate_ref)
    builder.seal_normalized_result(result)
    builder.validate_result_certificate_pair(result, certificate)
    certificate["media_scope"]["frame_index"] = 11
    builder.seal_operational_certificate(certificate)
    with pytest.raises(ValueError, match="media/frame scope mismatch"):
        builder.validate_result_certificate_pair(result, certificate)


def test_media_scope_rejects_hash_drift_reversed_spans_and_missing_temporal_evidence(builder):
    scope = builder.fixture_media_scope()
    scope["source_media_sha256"] = builder.h("0")
    with pytest.raises(ValueError, match="source hash"):
        builder.validate_media_scope(scope)
    span = {
        "media_kind": "frame_span", "source_media_ref": builder.ref("video_artifact", "video_fixture_001", "a"), "source_media_sha256": builder.h("a"),
        "frame_index": None, "pts_ticks": None, "timebase_numerator": 1, "timebase_denominator": 1000,
        "span_start_frame": 20, "span_end_frame": 10, "neighbor_frame_refs": [],
        "temporal_evidence_refs": [builder.ref("temporal_evidence", "temporal_span_fixture_001", "b")], "exact_frame_scope_only": True,
    }
    with pytest.raises(ValueError, match="empty or reversed"):
        builder.validate_media_scope(span)
    span["span_start_frame"] = 10
    span["span_end_frame"] = 20
    span["temporal_evidence_refs"] = []
    with pytest.raises(ValueError, match="temporal evidence"):
        builder.validate_media_scope(span)


def test_signed_event_journal_rejects_fork_reorder_deletion_and_reseal(builder):
    event = copy.deepcopy(builder.build_examples()["maskfactory_bridge_event_v2.example.json"])
    trust = builder.fixture_signing_trust(trusted=True, key_id="maskfactory_production_signer_001")
    event["fixture_only"] = False
    event["signature_trust"] = copy.deepcopy(trust)
    event["event_sha256"] = builder.bridge_event_sha256(event)
    pin = copy.deepcopy(event["journal_pin"])
    pin["head_event_sha256"] = event["event_sha256"]
    pin["checkpoint_signature_trust"] = copy.deepcopy(trust)
    builder.validate_event_journal([event], pin, {})
    tampered = copy.deepcopy(event)
    tampered["payload_ref"]["sha256"] = builder.h("0")
    with pytest.raises(ValueError, match="canonical payload hash"):
        builder.validate_event_journal([tampered], pin, {})
    forked = copy.deepcopy(event)
    forked["sequence"] = 2
    forked["previous_event_sha256"] = builder.h("f")
    pin2 = copy.deepcopy(pin)
    pin2["checkpoint_sequence"] = 2
    pin2["head_event_sha256"] = forked["event_sha256"]
    with pytest.raises(ValueError, match="fork, deletion, or reorder"):
        builder.validate_event_journal([event, forked], pin2, {})
    resealed = copy.deepcopy(pin)
    resealed["checkpoint_signature_trust"]["embedded_public_key_is_trust_anchor"] = True
    with pytest.raises(ValueError, match="embedded or producer-supplied key"):
        builder.validate_event_journal([event], resealed, {})


def test_fixture_certificate_validates_as_fixture_but_cannot_certify_production(builder, contracts):
    schemas, registry = contracts
    fixture_certificate = copy.deepcopy(builder.build_examples()["maskfactory_operational_certificate_v2.example.json"])
    assert not errors_for(schemas["maskfactory_operational_certificate_v2.schema.json"], fixture_certificate, registry)
    builder.validate_operational_certificate_record(fixture_certificate)
    result, _ = certified_mode_b_pair(builder)
    with pytest.raises(ValueError, match="fixture certificate cannot satisfy production"):
        builder.validate_result_certificate_pair(result, fixture_certificate)


def test_production_certificate_requires_genuine_runtime_evidence(builder, contracts):
    schemas, registry = contracts
    certificate = copy.deepcopy(builder.build_examples()["maskfactory_operational_certificate_v2.example.json"])
    certificate["fixture_only"] = False
    certificate["runtime_completion_claimed"] = False
    certificate["certification_context"] = "production_runtime"
    certificate["signature_algorithm"] = "ed25519"
    certificate["signature_trust"] = builder.fixture_signing_trust(trusted=True, key_id="main_normalization_signer_001", signer_role="main_normalization_signer")
    certificate["genuine_runtime_evidence_refs"] = []
    builder.seal_operational_certificate(certificate)
    assert errors_for(schemas["maskfactory_operational_certificate_v2.schema.json"], certificate, registry)
    with pytest.raises(ValueError, match="requires non-fixture genuine runtime evidence"):
        builder.validate_operational_certificate_record(certificate)


def test_substituted_self_signed_key_is_rejected_even_when_signature_verifies(builder):
    key_id = "maskfactory_production_signer_001"
    trust = builder.fixture_signing_trust(trusted=True, key_id=key_id, signer_role="maskfactory_release_signer")
    trust["embedded_public_key_sha256"] = builder.h("f")
    entry = {
        "key_id": key_id, "signer_role": "maskfactory_release_signer", "status": "active",
        "public_key_base64": base64.b64encode(b"d" * 32).decode("ascii"), "public_key_sha256": builder.h("d"),
        "valid_from": "2026-07-16T00:00:00-05:00", "valid_until": "2026-07-18T00:00:00-05:00",
        "revocation_checked_at": "2026-07-16T00:00:00-05:00", "revocation_valid_until": "2026-07-18T00:00:00-05:00",
        "revocation_evidence_ref": builder.ref("revocation_evidence", "release_key_revocation_001", "d"),
    }
    entry["entry_sha256"] = builder.trusted_key_entry_sha256(entry)
    with pytest.raises(ValueError, match="substituted self-signed key"):
        builder.validate_signature_trust_record(trust, {key_id: entry}, production_required=True, expected_signer_role="maskfactory_release_signer")


def test_compiled_mask_request_validates_exact_frozen_schema_hash_and_dedicated_signature(builder):
    request, trusted_keys, runtime_context = compiled_runtime_mask_request(builder)
    builder.validate_outbound_maskfactory_signed_document(
        request,
        "mask_acquisition_request",
        "request_payload_sha256",
        "consumer_request",
        "main_mask_request_signer",
        runtime_context["trusts"]["main_mask_request_signer"],
        trusted_keys,
        runtime_context,
        use_time=runtime_context["use_time"],
    )
    tampered = copy.deepcopy(request)
    tampered["mask_intents"][0]["label"] = "torso"
    with pytest.raises(ValueError, match="hash, signature, or key-role binding"):
        builder.validate_outbound_maskfactory_signed_document(
            tampered,
            "mask_acquisition_request",
            "request_payload_sha256",
            "consumer_request",
            "main_mask_request_signer",
            runtime_context["trusts"]["main_mask_request_signer"],
            trusted_keys,
            runtime_context,
            use_time=runtime_context["use_time"],
        )


def test_request_signer_cross_role_substitution_and_expired_key_fail_closed(builder):
    request, trusted_keys, runtime_context = compiled_runtime_mask_request(builder)
    with pytest.raises(ValueError, match="signer role|authority domain|key-role binding"):
        builder.validate_outbound_maskfactory_signed_document(
            request,
            "mask_acquisition_request",
            "request_payload_sha256",
            "consumer_request",
            "main_mask_request_signer",
            runtime_context["trusts"]["main_adoption_signer"],
            trusted_keys,
            runtime_context,
            use_time=runtime_context["use_time"],
        )
    key_id = runtime_context["role_keys"]["main_mask_request_signer"]
    trusted_keys[key_id]["valid_until"] = "2026-07-17T02:21:00-05:00"
    trusted_keys[key_id]["entry_sha256"] = builder.trusted_key_entry_sha256(trusted_keys[key_id])
    runtime_context["trusts"]["main_mask_request_signer"]["trusted_key_entry_sha256"] = trusted_keys[key_id]["entry_sha256"]
    with pytest.raises(ValueError, match="expired|validity"):
        builder.validate_outbound_maskfactory_signed_document(
            request,
            "mask_acquisition_request",
            "request_payload_sha256",
            "consumer_request",
            "main_mask_request_signer",
            runtime_context["trusts"]["main_mask_request_signer"],
            trusted_keys,
            runtime_context,
            use_time=runtime_context["use_time"],
        )


@pytest.mark.parametrize("mutation", ["missing_continuity", "sequence_replay", "backdated_floor", "tampered_signature"])
def test_signed_trusted_clock_rejects_omission_backdating_and_replay(builder, mutation):
    _, _, _, _, runtime_context = production_release_adoption_bundle(builder)
    if mutation == "missing_continuity":
        runtime_context.pop("last_accepted_use_time")
    elif mutation == "sequence_replay":
        runtime_context["trusted_clock"]["clock_sequence"] = runtime_context["last_accepted_clock_sequence"]
        reseal_trusted_clock(builder, runtime_context, record_id="trusted_clock_replay_001")
    elif mutation == "backdated_floor":
        runtime_context["trusted_clock"]["monotonic_floor_at"] = "2026-07-17T02:19:59-05:00"
        reseal_trusted_clock(builder, runtime_context, record_id="trusted_clock_backdated_001")
    else:
        runtime_context["trusted_clock"]["signature"] = corrupt_signature(runtime_context["trusted_clock"]["signature"])
    with pytest.raises(ValueError, match="continuity|backdated|replayed|non-increasing|signature"):
        builder.resolve_trusted_use_time(runtime_context["use_time"], runtime_context)


def test_production_adoption_binds_out_of_band_trust_and_signed_journal(builder):
    release, adoption, consumer, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    builder.validate_adoption_trust(adoption, consumer, release, trusted_keys, runtime_context, use_time=runtime_context["use_time"])
    release["signature_trust"]["embedded_public_key_sha256"] = builder.h("f")
    adoption["release_signature_trust"] = copy.deepcopy(release["signature_trust"])
    builder.seal_adoption_receipt(adoption)
    with pytest.raises(ValueError, match="normalized release canonical seal mismatch|substituted self-signed key"):
        builder.validate_adoption_trust(adoption, consumer, release, trusted_keys, runtime_context, use_time=runtime_context["use_time"])


@pytest.mark.parametrize("mutation", ["fixture_release", "fixture_adoption", "mismatched_release_ref", "missing_release_evidence", "missing_adoption_evidence", "active_pin_without_production"])
def test_production_adoption_fixture_and_reference_firewall_fails_closed(builder, contracts, mutation):
    schemas, registry = contracts
    release, adoption, consumer, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    if mutation == "fixture_release":
        release.update({"fixture_only": True, "release_context": "fixture_validation", "genuine_runtime_evidence_refs": []})
        adoption["release_snapshot_ref"] = builder.immutable_release_ref(release)
    elif mutation == "fixture_adoption":
        adoption.update({"fixture_only": True, "adoption_context": "fixture_validation"})
    elif mutation == "mismatched_release_ref":
        adoption["release_snapshot_ref"]["sha256"] = builder.h("f")
    elif mutation == "missing_release_evidence":
        release["genuine_runtime_evidence_refs"] = []
    elif mutation == "missing_adoption_evidence":
        adoption["genuine_runtime_evidence_refs"] = []
    else:
        adoption.update({"production_consumption_allowed": False, "active_pin_written": True, "adoption_context": "fixture_validation"})
    builder.seal_adoption_receipt(adoption)
    release_errors = errors_for(schemas["maskfactory_release_snapshot_v2.schema.json"], release, registry)
    adoption_errors = errors_for(schemas["maskfactory_adoption_receipt_v2.schema.json"], adoption, registry)
    semantic_error = None
    try:
        builder.validate_adoption_trust(adoption, consumer, release, trusted_keys, runtime_context, use_time=runtime_context["use_time"])
    except ValueError as exc:
        semantic_error = exc
    assert release_errors or adoption_errors or semantic_error, mutation


def test_adoption_revalidation_policy_covers_every_invalidation_class(builder):
    adoption = builder.build_examples()["maskfactory_adoption_receipt_v2.example.json"]
    builder.validate_revalidation_policy(adoption)
    reasons = {rule["producer_reason_code"] for rule in adoption["revalidation_rules"]}
    assert reasons == set(builder.PRODUCER_INVALIDATION_REASONS)
    for mutation in ("missing_trigger", "wrong_action", "duplicate_trigger"):
        candidate = copy.deepcopy(adoption)
        if mutation == "missing_trigger":
            candidate["revalidation_triggers"].pop()
            candidate["revalidation_rules"].pop()
        elif mutation == "wrong_action":
            candidate["revalidation_rules"][0]["main_enforcement_actions"] = ["demote_and_repair"]
        else:
            candidate["revalidation_rules"][-1] = copy.deepcopy(candidate["revalidation_rules"][0])
        with pytest.raises(ValueError, match="revalidation"):
            builder.validate_revalidation_policy(candidate)


def test_certified_authority_decision_rechecks_time_revocation_and_trust(builder):
    _, certificate, decision, policy = certified_authority_decision_bundle(builder)
    builder.validate_authority_decision_record(decision, certificate, {"maskfactory_production_signer_001": builder.h("d")}, policy)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("future_issued", "future-issued"),
        ("expired", "future-issued"),
        ("stale_revocation", "future-issued"),
        ("revoked", "future-issued"),
    ],
)
def test_certified_authority_decision_rejects_temporal_or_revocation_contradictions(builder, mutation, expected):
    _, certificate, decision, policy = certified_authority_decision_bundle(builder)
    temporal = decision["certificate_temporal_evaluation"]
    if mutation == "future_issued":
        certificate["issued_at"] = "2026-07-17T03:00:00-05:00"
        temporal["certificate_issued_at"] = certificate["issued_at"]
    elif mutation == "expired":
        certificate["expires_at"] = "2026-07-17T02:20:30-05:00"
        temporal["certificate_expires_at"] = certificate["expires_at"]
    elif mutation == "stale_revocation":
        temporal["revocation_index_valid_until"] = "2026-07-17T02:20:30-05:00"
    else:
        certificate["status"] = "revoked"
        certificate["revocation_ref"] = builder.ref("revocation_event", "certificate_revocation_001", "f")
    with pytest.raises(ValueError, match=expected):
        builder.validate_authority_decision_record(decision, certificate, {"maskfactory_production_signer_001": builder.h("d")}, policy)


def test_fixture_authority_decision_cannot_be_eligible_or_promotion_bound(builder, contracts):
    schemas, registry = contracts
    decision = copy.deepcopy(builder.build_examples()["maskfactory_authority_decision_v2.example.json"])
    decision.update({"decision": "eligible", "eligible_for_intended_use": True, "intended_use": "promotion_bound"})
    decision["genuine_runtime_evidence_refs"] = [builder.ref("runtime_evidence", "forbidden_fixture_evidence_001", "f")]
    assert errors_for(schemas["maskfactory_authority_decision_v2.schema.json"], decision, registry)
    with pytest.raises(ValueError, match="fixture authority decision"):
        builder.validate_authority_decision_record(decision)


def test_operational_claim_cannot_be_reclassified_as_accuracy_or_training_gold(builder):
    _, certificate, decision, policy = certified_authority_decision_bundle(builder)
    decision["required_claim_classes"] = ["training_gold"]
    with pytest.raises(ValueError, match="claim class"):
        builder.validate_authority_decision_record(decision, certificate, {"maskfactory_production_signer_001": builder.h("d")}, policy)
    crosswalk = builder.build_registries()["wave64_maskfactory_bridge_authority_crosswalk_v2.json"]
    assert crosswalk["operational_claim_firewall"]["counts_as_independent_real_accuracy"] is False
    assert crosswalk["operational_claim_firewall"]["counts_as_training_gold"] is False


def test_signed_policy_criteria_cannot_be_omitted_duplicated_or_self_declared(builder):
    _, certificate, decision, policy = certified_authority_decision_bundle(builder)
    decision["criterion_evaluations"] = decision["criterion_evaluations"][:-1]
    with pytest.raises(ValueError, match="omitted or invented"):
        builder.validate_authority_decision_record(decision, certificate, {"maskfactory_production_signer_001": builder.h("d")}, policy)
    _, certificate, decision, policy = certified_authority_decision_bundle(builder)
    decision["criterion_evaluations"].append(copy.deepcopy(decision["criterion_evaluations"][0]))
    with pytest.raises(ValueError, match="duplicate criterion"):
        builder.validate_authority_decision_record(decision, certificate, {"maskfactory_production_signer_001": builder.h("d")}, policy)
    _, certificate, decision, policy = certified_authority_decision_bundle(builder)
    decision["criterion_evaluations"][0]["observed"] = 9.0
    with pytest.raises(ValueError, match="self-declared"):
        builder.validate_authority_decision_record(decision, certificate, {"maskfactory_production_signer_001": builder.h("d")}, policy)


def test_promotion_policy_projection_is_cryptographically_bound(builder):
    _, _, _, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    policy = production_policy(builder)
    policy["signature_trust"] = copy.deepcopy(runtime_context["trusts"]["main_promotion_policy_signer"])
    policy["genuine_runtime_evidence_refs"] = [
        add_runtime_artifact(builder, runtime_context, "runtime_evidence", "policy_runtime_evidence_001", b"policy-runtime-evidence")
    ]
    policy["evidence_manifest_refs"] = [
        add_runtime_artifact(builder, runtime_context, "policy_evidence_manifest", "policy_evidence_manifest_001", b"policy-evidence-manifest")
    ]
    policy["revocation_manifest_refs"] = [
        add_runtime_artifact(builder, runtime_context, "policy_revocation_manifest", "policy_revocation_manifest_001", b"policy-revocation-manifest")
    ]
    builder.seal_promotion_policy(policy)
    runtime_context["artifact_bytes"][builder.immutable_ref_key(policy["policy_artifact_ref"])] = builder.promotion_policy_payload_bytes(policy)
    policy["signature"] = sign_runtime_payload(
        runtime_context,
        policy["signature_domain"],
        policy["policy_sha256"],
        runtime_context["role_keys"]["main_promotion_policy_signer"],
    )
    builder.validate_promotion_policy_record(
        policy,
        trusted_keys,
        production_required=True,
        runtime_verification_context=runtime_context,
        use_time=runtime_context["use_time"],
    )
    corrupted_signature = copy.deepcopy(policy)
    corrupted_signature["signature"] = corrupt_signature(corrupted_signature["signature"])
    with pytest.raises(ValueError, match="signature"):
        builder.validate_promotion_policy_record(
            corrupted_signature,
            trusted_keys,
            production_required=True,
            runtime_verification_context=runtime_context,
            use_time=runtime_context["use_time"],
        )
    policy["criteria"][0]["threshold"] = 999
    with pytest.raises(ValueError, match="immutable binding hash mismatch"):
        builder.validate_promotion_policy_record(
            policy,
            trusted_keys,
            production_required=True,
            runtime_verification_context=runtime_context,
            use_time=runtime_context["use_time"],
        )


def test_fixture_or_evidenceless_record_cannot_release_row348(builder, contracts):
    schemas, registry = contracts
    schema = schemas["maskfactory_bridge_release_certificate_v2.schema.json"]
    fixture_release = copy.deepcopy(builder.build_examples()["maskfactory_bridge_release_certificate_v2.example.json"])
    fixture_release.update({"status": "released", "release_allowed": True, "row218_runtime_passed": True, "rows321_347_runtime_passed": True})
    fixture_release["checks"][0]["status"] = "pass"
    assert errors_for(schema, fixture_release, registry)

    release, adoption, consumer, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    production_release = production_bridge_release(builder, release, adoption, runtime_context)
    production_release["genuine_runtime_evidence_refs"] = []
    assert errors_for(schema, production_release, registry)
    with pytest.raises(ValueError, match="requires non-fixture genuine runtime evidence"):
        builder.validate_bridge_release_certificate_record(production_release)

    production_release["genuine_runtime_evidence_refs"] = [add_runtime_artifact(builder, runtime_context, "runtime_evidence", "row348_runtime_evidence_restored_001", b"row348-runtime-evidence-restored")]
    builder.seal_bridge_release_certificate(production_release)
    assert not errors_for(schema, production_release, registry)
    production_release["release_signature"] = sign_runtime_payload(
        runtime_context,
        production_release["release_signature_domain"],
        production_release["release_certificate_sha256"],
        runtime_context["role_keys"]["main_bridge_release_signer"],
    )
    builder.validate_bridge_release_certificate_record(production_release, release_snapshot=release, adoption=adoption, consumer=consumer, trusted_keys=trusted_keys, runtime_verification_context=runtime_context, use_time=runtime_context["use_time"])


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_runtime_resolver",
        "tampered_row348_evidence_bytes",
        "tampered_gate_evaluator_bytes",
        "tampered_gate_evidence_bytes",
        "tampered_gate_signature",
        "tampered_adoption_qualification_bytes",
        "tampered_adoption_check_evidence_bytes",
        "tampered_journal_checkpoint_bytes",
        "tampered_journal_checkpoint_signature",
        "tampered_row348_signature",
        "tampered_release_signature",
        "tampered_adoption_signature",
        "tampered_normalization_signature",
    ],
)
def test_production_authority_requires_resolved_bytes_and_valid_ed25519_signatures(builder, mutation):
    release, adoption, consumer, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    bridge_release = production_bridge_release(builder, release, adoption, runtime_context)
    context = runtime_context
    if mutation == "missing_runtime_resolver":
        context = None
    elif mutation == "tampered_row348_evidence_bytes":
        ref_value = bridge_release["genuine_runtime_evidence_refs"][0]
        runtime_context["artifact_bytes"][builder.immutable_ref_key(ref_value)] = b"tampered-row348-evidence"
    elif mutation == "tampered_gate_evaluator_bytes":
        ref_value = bridge_release["checks"][0]["evaluator_manifest_ref"]
        runtime_context["artifact_bytes"][builder.immutable_ref_key(ref_value)] = b"tampered-gate-evaluator"
    elif mutation == "tampered_gate_evidence_bytes":
        ref_value = bridge_release["checks"][0]["evidence_refs"][0]
        runtime_context["artifact_bytes"][builder.immutable_ref_key(ref_value)] = b"tampered-gate-evidence"
    elif mutation == "tampered_gate_signature":
        bridge_release["checks"][0]["gate_report_signature"] = corrupt_signature(bridge_release["checks"][0]["gate_report_signature"])
    elif mutation == "tampered_adoption_qualification_bytes":
        ref_value = adoption["qualification_bundle_ref"]
        runtime_context["artifact_bytes"][builder.immutable_ref_key(ref_value)] = b"tampered-qualification-bundle"
    elif mutation == "tampered_adoption_check_evidence_bytes":
        ref_value = adoption["checks"][0]["evidence_ref"]
        runtime_context["artifact_bytes"][builder.immutable_ref_key(ref_value)] = b"tampered-adoption-check"
    elif mutation == "tampered_journal_checkpoint_bytes":
        ref_value = adoption["journal_pin"]["checkpoint_ref"]
        runtime_context["artifact_bytes"][builder.immutable_ref_key(ref_value)] = b"tampered-journal-checkpoint"
    elif mutation == "tampered_journal_checkpoint_signature":
        adoption["journal_pin"]["checkpoint_signature"] = corrupt_signature(adoption["journal_pin"]["checkpoint_signature"])
        bridge_release["journal_pin"] = copy.deepcopy(adoption["journal_pin"])
    elif mutation == "tampered_row348_signature":
        bridge_release["release_signature"] = corrupt_signature(bridge_release["release_signature"])
    elif mutation == "tampered_release_signature":
        release["release_signature"] = corrupt_signature(release["release_signature"])
    elif mutation == "tampered_adoption_signature":
        adoption["adoption_signature"] = corrupt_signature(adoption["adoption_signature"])
    else:
        release["normalization_signature"] = corrupt_signature(release["normalization_signature"])
    with pytest.raises(ValueError):
        builder.validate_bridge_release_certificate_record(
            bridge_release,
            release_snapshot=release,
            adoption=adoption,
            consumer=consumer,
            trusted_keys=trusted_keys,
            runtime_verification_context=context,
            use_time=runtime_context["use_time"],
        )


@pytest.mark.parametrize("mutation", ["missing_gate", "duplicate_gate", "wrong_gate_hash", "self_declared_pass", "aggregate_boolean", "untrusted_gate", "missing_gate_runtime_evidence"])
def test_row348_closed_gate_set_and_derived_release_fails_closed(builder, contracts, mutation):
    schemas, registry = contracts
    release, adoption, consumer, trusted_keys, runtime_context = production_release_adoption_bundle(builder)
    bridge_release = production_bridge_release(builder, release, adoption, runtime_context)
    if mutation == "missing_gate":
        bridge_release["checks"].pop()
    elif mutation == "duplicate_gate":
        bridge_release["checks"][-1] = copy.deepcopy(bridge_release["checks"][0])
    elif mutation == "wrong_gate_hash":
        bridge_release["checks"][3]["gate_report_sha256"] = builder.h("f")
    elif mutation == "self_declared_pass":
        bridge_release["checks"][3]["derived_pass"] = False
    elif mutation == "aggregate_boolean":
        bridge_release["rows321_347_runtime_passed"] = False
    elif mutation == "untrusted_gate":
        bridge_release["checks"][3]["signature_trust"] = builder.fixture_signing_trust()
        builder.seal_release_gate_report(bridge_release["checks"][3])
    else:
        bridge_release["checks"][3]["genuine_runtime_evidence_refs"] = []
        builder.seal_release_gate_report(bridge_release["checks"][3])
    builder.seal_bridge_release_certificate(bridge_release)
    schema_errors = errors_for(schemas["maskfactory_bridge_release_certificate_v2.schema.json"], bridge_release, registry)
    semantic_error = None
    try:
        builder.validate_bridge_release_certificate_record(bridge_release, release_snapshot=release, adoption=adoption, consumer=consumer, trusted_keys=trusted_keys, runtime_verification_context=runtime_context, use_time=runtime_context["use_time"])
    except ValueError as exc:
        semantic_error = exc
    assert schema_errors or semantic_error, mutation


def test_app_page_mapping_and_readiness_projection_are_explicit(builder, contracts):
    schemas, registry = contracts
    expected_pages = {"home_readiness", "projects_revisions", "scene_builder_pose_masks", "runs_dag", "queue_workers", "recovery", "qa"}
    app = builder.build_registries(schemas)["wave64_maskfactory_bridge_app_read_model_mapping_v2.json"]
    assert {page["page_id"] for page in app["pages"]} == expected_pages
    assert all(page["read_models"] and page["field_paths"] for page in app["pages"])
    pages = {page["page_id"]: page for page in app["pages"]}
    assert {"$.signing_trust_status", "$.journal_integrity_status", "$.core_blockers", "$.optional_profile_blockers"}.issubset(pages["home_readiness"]["field_paths"])
    assert {"$.scene_owner_roster", "$.target_region_bindings", "$.protected_region_bindings", "$.input_region_lineage", "$.media_scope"}.issubset(pages["scene_builder_pose_masks"]["field_paths"])
    assert {"$.attempt_number", "$.hypothesis", "$.execution_observation", "$.media_scope"}.issubset(pages["runs_dag"]["field_paths"])
    assert {"$.resource_envelope", "$.deadline_at", "$.execution_observation.resource_envelope_met"}.issubset(pages["queue_workers"]["field_paths"])
    assert {"$.signature_trust", "$.journal_pin", "$.previous_event_sha256"}.issubset(pages["recovery"]["field_paths"])
    assert {"$.authority.claim_class", "$.certificate_temporal_evaluation", "$.certificate_signature_trust", "$.policy_sha256"}.issubset(pages["qa"]["field_paths"])
    assert app["all_pages_read_only"] is True
    assert app["app_can_mutate_producer_truth"] is False
    assert app["app_can_commit_promotion"] is False
    assert app["app_or_conversation_summary_can_establish_project_truth"] is False
    assert app["llm_vlm_can_bypass_schema_validator_or_signed_policy"] is False
    readiness = copy.deepcopy(builder.build_examples()["maskfactory_bridge_readiness_projection_v2.example.json"])
    schema = schemas["maskfactory_bridge_readiness_projection_v2.schema.json"]
    assert not errors_for(schema, readiness, registry)
    assert {page["page_id"] for page in readiness["page_readiness"]} == expected_pages
    readiness["runtime_readiness_claimed"] = True
    readiness["row218_status"] = "passed"
    readiness["rows321_347_status"] = "passed"
    readiness["row348_release_status"] = "released"
    assert errors_for(schema, readiness, registry)


def test_canonical_auth_replay_and_safe_import_policies_fail_closed(builder):
    registries = builder.build_registries()
    builder.validate_policy_registries(registries)
    policy = registries["wave64_maskfactory_bridge_compatibility_policy_v2.json"]
    assert policy["canonical_payload_security_policy"]["signature_domain_separation_required"] is True
    assert policy["request_authentication_and_replay_policy"]["nonce_reuse_action"] == "reject_and_audit"
    assert policy["safe_release_import_policy"]["symlink_hardlink_reparse_escape"] == "reject"
    for mutation in ["canonical", "nonce", "archive"]:
        candidate = copy.deepcopy(registries)
        if mutation == "canonical":
            candidate["wave64_maskfactory_bridge_compatibility_policy_v2.json"]["canonical_payload_security_policy"]["duplicate_object_keys"] = "allow"
        elif mutation == "nonce":
            candidate["wave64_maskfactory_bridge_compatibility_policy_v2.json"]["request_authentication_and_replay_policy"]["nonce_reuse_action"] = "allow"
        else:
            candidate["wave64_maskfactory_bridge_compatibility_policy_v2.json"]["safe_release_import_policy"]["symlink_hardlink_reparse_escape"] = "allow"
        with pytest.raises(ValueError):
            builder.validate_policy_registries(candidate)

    strict_json_cases = [
        (b'{"duplicate":1,"duplicate":2}', "duplicate JSON object key"),
        (b'{"\\u00e9":1,"e\\u0301":2}', "Unicode NFC-colliding JSON object key"),
        (b'{"value":NaN}', "non-finite JSON number"),
        (b'{"value":Infinity}', "non-finite JSON number"),
    ]
    for raw, expected_error in strict_json_cases:
        with pytest.raises(ValueError, match=expected_error):
            builder.strict_json_loads(raw)


def test_execution_lifecycle_requires_reconciled_outcome_unknown(builder):
    registries = builder.build_registries()
    lifecycle = registries["wave64_maskfactory_bridge_arbitration_cache_recovery_policy_v2.json"]["execution_lifecycle"]
    assert lifecycle["outcome_unknown_is_terminal"] is False
    assert lifecycle["resubmit_from_outcome_unknown_allowed"] is False
    assert {tuple(value) for value in lifecycle["allowed_transitions"]}.issuperset({
        ("outcome_unknown", "running"),
        ("outcome_unknown", "completed_pending_receipt"),
        ("outcome_unknown", "failed"),
        ("outcome_unknown", "reconciled_not_found"),
        ("reconciled_not_found", "submitted"),
    })
    assert lifecycle["reconciliation_outcomes"] == ["found_running", "found_completed_pending_receipt", "found_failed", "not_found_safe_to_submit"]
    assert lifecycle["not_found_safe_to_submit_authorizes_exactly_one_resubmission"] is True
    candidate = copy.deepcopy(registries)
    candidate["wave64_maskfactory_bridge_arbitration_cache_recovery_policy_v2.json"]["execution_lifecycle"]["allowed_transitions"].append(["succeeded", "running"])
    with pytest.raises(ValueError, match="terminal-state"):
        builder.validate_policy_registries(candidate)


def test_llm_vlm_conversation_and_memory_are_never_project_authority(builder):
    registries = builder.build_registries()
    authority = registries["wave64_maskfactory_bridge_contract_catalog_v2.json"]["autonomous_intelligence_authority_policy"]
    assert authority["conversation_or_compaction_summary_is_durable_project_truth"] is False
    assert authority["llm_vlm_observation_is_promotion_authority"] is False
    assert authority["llm_can_self_promote_or_mutate_producer_truth"] is False
    assert authority["tool_gateway_is_only_execution_surface"] is True
    assert authority["memory_write_requires_schema_validation_provenance_and_event_journal_admission"] is True
    candidate = copy.deepcopy(registries)
    candidate["wave64_maskfactory_bridge_contract_catalog_v2.json"]["autonomous_intelligence_authority_policy"]["conversation_or_compaction_summary_is_durable_project_truth"] = True
    with pytest.raises(ValueError, match="authority boundary"):
        builder.validate_policy_registries(candidate)


def test_runtime_readiness_requires_every_core_release_fact(builder, contracts):
    schemas, registry = contracts
    schema = schemas["maskfactory_bridge_readiness_projection_v2.schema.json"]
    bundle = production_readiness_bundle(builder)
    readiness = bundle[0]
    assert not errors_for(schema, readiness, registry)
    validate_production_readiness(builder, bundle)


@pytest.mark.parametrize(
    "mutation",
    ["fixture", "core_profile_blocked", "duplicate_profile", "duplicate_page", "missing_pin", "missing_release", "missing_adoption", "missing_journal", "journal_head_mismatch", "core_blocker", "missing_runtime_evidence"],
)
def test_runtime_readiness_contradictions_fail_closed(builder, contracts, mutation):
    schemas, registry = contracts
    schema = schemas["maskfactory_bridge_readiness_projection_v2.schema.json"]
    bundle = production_readiness_bundle(builder)
    readiness = bundle[0]
    if mutation == "fixture":
        readiness["fixture_only"] = True
    elif mutation == "core_profile_blocked":
        next(item for item in readiness["profile_readiness"] if item["completion_profile"] == "core_autonomous_runtime")["status"] = "blocked"
    elif mutation == "duplicate_profile":
        readiness["profile_readiness"][2] = copy.deepcopy(readiness["profile_readiness"][0])
    elif mutation == "duplicate_page":
        readiness["page_readiness"][6] = copy.deepcopy(readiness["page_readiness"][0])
    elif mutation == "missing_pin":
        readiness["active_pin_status"] = "missing"
    elif mutation == "missing_release":
        readiness["release_snapshot_ref"] = None
    elif mutation == "missing_adoption":
        readiness["adoption_receipt_ref"] = None
    elif mutation == "missing_journal":
        readiness["journal_pin"] = None
    elif mutation == "journal_head_mismatch":
        readiness["event_cursor"]["last_event_sha256"] = builder.h("f")
    elif mutation == "missing_runtime_evidence":
        readiness["genuine_runtime_evidence_refs"] = []
    else:
        blocker = {"code": "MFB_RUNTIME_EVIDENCE_MISSING", "category": "policy", "message": "core blocker", "retryable": False, "blocks_scope": "required_release_path", "completion_profile": "core_autonomous_runtime", "core_impact": "blocking", "evidence_refs": [builder.ref("evidence", "core_blocker_evidence_001", "f")]}
        readiness["core_blockers"] = [blocker]
        readiness["blockers"] = [copy.deepcopy(blocker)]
    schema_errors = errors_for(schema, readiness, registry)
    semantic_error = None
    try:
        validate_production_readiness(builder, bundle)
    except ValueError as exc:
        semantic_error = exc
    assert schema_errors or semantic_error, mutation


@pytest.mark.parametrize("mutation", ["release_ref", "adoption_ref", "bridge_release_ref", "page_gate_evidence", "runtime_evidence_projection", "adoption_journal", "stale_gate_report"])
def test_readiness_is_cross_document_derived_not_self_declared(builder, mutation):
    bundle = list(production_readiness_bundle(builder))
    readiness, release, adoption, bridge_release, consumer, trusted_keys, runtime_context = bundle
    if mutation == "release_ref":
        readiness["release_snapshot_ref"]["sha256"] = builder.h("f")
    elif mutation == "adoption_ref":
        readiness["adoption_receipt_ref"]["sha256"] = builder.h("f")
    elif mutation == "bridge_release_ref":
        readiness["bridge_release_certificate_ref"]["sha256"] = builder.h("f")
    elif mutation == "page_gate_evidence":
        readiness["page_readiness"][0]["evidence_refs"].pop()
    elif mutation == "runtime_evidence_projection":
        readiness["genuine_runtime_evidence_refs"].pop()
    elif mutation == "adoption_journal":
        adoption["journal_pin"]["head_event_sha256"] = builder.h("f")
        builder.seal_adoption_receipt(adoption)
    else:
        bridge_release["checks"][5]["status"] = "blocked"
        bridge_release["checks"][5]["derived_pass"] = False
        builder.seal_release_gate_report(bridge_release["checks"][5])
        bridge_release["rows321_347_runtime_passed"] = False
        bridge_release["status"] = "blocked"
        bridge_release["release_allowed"] = False
        bridge_release["runtime_completion_claimed"] = False
        builder.seal_bridge_release_certificate(bridge_release)
    with pytest.raises(ValueError):
        builder.validate_readiness_projection(
            readiness, release_snapshot=release, adoption=adoption, bridge_release=bridge_release,
            consumer=consumer, trusted_keys=trusted_keys, runtime_verification_context=runtime_context, use_time=runtime_context["use_time"],
        )


def test_optional_profile_blocker_cannot_turn_core_readiness_red(builder, contracts):
    schemas, registry = contracts
    bundle = production_readiness_bundle(builder)
    readiness = bundle[0]
    optional = {"code": "MFB_INDEPENDENT_ACCURACY_DATASET_PENDING", "category": "quality", "message": "optional profile remains pending", "retryable": False, "blocks_scope": "dependent_pass", "completion_profile": "independent_real_accuracy", "core_impact": "non_blocking", "evidence_refs": [builder.ref("evidence", "optional_accuracy_evidence_001", "e")]}
    readiness["optional_profile_blockers"] = [optional]
    readiness["blockers"] = [copy.deepcopy(optional)]
    next(item for item in readiness["profile_readiness"] if item["completion_profile"] == "independent_real_accuracy")["status"] = "blocked"
    assert not errors_for(schemas["maskfactory_bridge_readiness_projection_v2.schema.json"], readiness, registry)
    validate_production_readiness(builder, bundle)


def test_row346_requires_all_app_surfaces_and_readiness_contract(builder):
    row = next(row for row in builder.build_rows() if row["row_number"] == 346)
    for phrase in ["Home/readiness", "Projects/revisions", "Scene Builder Pose & Masks", "Runs/DAG", "Queue/Workers", "Recovery", "QA", "readiness-projection v2"]:
        assert phrase in row["implementation_action"]
    assert "infer runtime readiness from fixtures" in row["acceptance"]


def test_optional_profiles_do_not_block_core(builder):
    consumer = builder.build_examples()["maskfactory_consumer_requirements_v2.example.json"]
    integration = builder.build_examples()["maskfactory_bridge_release_certificate_v2.example.json"]
    profiles = builder.build_registries()["wave64_maskfactory_bridge_completion_profile_registry_v2.json"]
    assert consumer["human_anchor_required_for_core"] is False
    assert consumer["scale_daz_required_for_core"] is False
    assert integration["independent_real_accuracy_required"] is False
    assert integration["scale_daz_maturity_required"] is False
    assert profiles["optional_profile_absence_blocks_core"] is False


def test_feedback_cannot_mutate_gold_or_authority(builder):
    feedback = builder.build_examples()["maskfactory_feedback_repair_request_v2.example.json"]
    assert feedback["direct_gold_mutation_requested"] is False
    assert feedback["authority_change_requested"] is False
    assert feedback["response_expected_via_release_or_event"] is True


def test_release_rejects_dirty_mutable_source(builder):
    release = builder.build_examples()["maskfactory_release_snapshot_v2.example.json"]
    assert release["producer_source"]["source_clean"] is True
    assert release["mutable_worktree_consumption_allowed"] is False


def test_adoption_cannot_allow_production_with_mismatch(builder, contracts):
    schemas, registry = contracts
    adoption = copy.deepcopy(builder.build_examples()["maskfactory_adoption_receipt_v2.example.json"])
    adoption["production_consumption_allowed"] = True
    adoption["active_pin_written"] = True
    assert errors_for(schemas["maskfactory_adoption_receipt_v2.schema.json"], adoption, registry)


def test_invalidation_is_dependent_pass_scoped_by_default(builder):
    event = builder.build_examples()["maskfactory_invalidation_event_v2.example.json"]
    assert event["dependent_pass_only_by_default"] is True
    assert {value["action"] for value in event["required_actions"]} == {"block_dependent_pass", "revalidate_adoption"}
    assert event["main_enforcement_actions"] == ["block_and_revalidate"]
    builder.validate_invalidation_event_record(event)


def test_exact_frozen_receipt_and_certificate_project_losslessly(builder):
    raw_receipt, raw_certificate, result, certificate, context = exact_raw_receipt_certificate_projection_bundle(builder)
    builder.validate_raw_certificate_projection(raw_certificate, certificate, context)
    builder.validate_raw_receipt_projection(raw_receipt, result, context)


@pytest.mark.parametrize("mutation", ["route", "scope", "runtime", "qa", "output", "release"])
def test_raw_certificate_projection_rejects_every_authority_bearing_tamper(builder, mutation):
    _, raw_certificate, _, certificate, context = exact_raw_receipt_certificate_projection_bundle(builder)
    if mutation == "route":
        certificate["serving_route_id"] = "wrong-route"
    elif mutation == "scope":
        certificate["certificate_scope"].pop()
    elif mutation == "runtime":
        certificate["runtime_provenance"]["operating_system"] = "Linux"
    elif mutation == "qa":
        certificate["qa_bindings"].pop()
    elif mutation == "output":
        certificate["output_refs"][0]["sha256"] = builder.h("f")
    else:
        certificate["release_snapshot_ref"] = builder.ref("maskfactory_release_snapshot_v2", "wrong_release", "f")
    with pytest.raises(ValueError):
        builder.validate_raw_certificate_projection(raw_certificate, certificate, context)


@pytest.mark.parametrize("mutation", ["request", "owner", "artifact", "target_region", "certificate_mapping", "execution"])
def test_raw_receipt_projection_rejects_every_identity_or_lineage_tamper(builder, mutation):
    raw_receipt, _, result, _, context = exact_raw_receipt_certificate_projection_bundle(builder)
    if mutation == "request":
        result["request_ref"]["sha256"] = builder.h("f")
    elif mutation == "owner":
        result["owner_bindings"][0]["provider_person_index"] += 1
    elif mutation == "artifact":
        result["masks"][0]["mask_ref"]["sha256"] = builder.h("f")
    elif mutation == "target_region":
        result["input_region_lineage"]["target_region_refs"][0]["sha256"] = builder.h("f")
    elif mutation == "certificate_mapping":
        context["raw_to_main_certificate_refs"] = {}
    else:
        result["execution_observation"]["runtime_ms"] += 1
    with pytest.raises(ValueError):
        builder.validate_raw_receipt_projection(raw_receipt, result, context)


@pytest.mark.parametrize("mutation", ["release_status", "wire_contract", "component_binding"])
def test_raw_release_projection_rejects_signed_fact_tamper(builder, mutation):
    release, _, _, _, context = production_release_adoption_bundle(builder)
    raw = builder.strict_json_loads(builder.resolve_verified_artifact_bytes(release["raw_producer_release_ref"], context))
    builder.validate_raw_release_projection(raw, release, context)
    if mutation == "release_status":
        release["release_status"] = "revoked"
    elif mutation == "wire_contract":
        release["contract_bindings"][0]["schema_sha256"] = builder.h("f")
    else:
        release["component_bindings"][0]["sha256"] = builder.h("f")
    with pytest.raises(ValueError):
        builder.validate_raw_release_projection(raw, release, context)


@pytest.mark.parametrize("mutation", ["warning_severity", "superseding_binding", "rollback_binding"])
def test_raw_invalidation_projection_preserves_severity_supersession_and_rollback(builder, mutation):
    raw, event = exact_raw_invalidation_projection(builder)
    builder.validate_raw_invalidation_projection(raw, event)
    if mutation == "warning_severity":
        raw["severity"] = "warning"
        event["severity"] = "warning"
    elif mutation == "superseding_binding":
        event["superseding_binding"] = {"release_id": "mfr_wrong", "release_payload_sha256": builder.h("f")}
    else:
        event["rollback_binding"] = {"rollback_id": "rollback_wrong", "rollback_sha256": builder.h("f")}
    with pytest.raises(ValueError):
        builder.validate_raw_invalidation_projection(raw, event)


def heterogeneous_invalidation(builder):
    event = copy.deepcopy(builder.build_examples()["maskfactory_invalidation_event_v2.example.json"])
    second = copy.deepcopy(event["target_transitions"][0])
    second.update({
        "transition_id": "transition_fixture_002", "target_id": "certificate_fixture_002", "target_sha256": builder.h("7"),
        "previous_authority_state": "qa_passed_noncertified", "new_authority_state": "invalid",
        "previous_certificate_status": "expired", "new_certificate_status": "revoked",
        "main_target_ref": builder.ref("maskfactory_operational_certificate_v2", "certificate_fixture_002", "7"),
    })
    event["target_transitions"].append(second)
    event["affected_refs"] = [copy.deepcopy(value["main_target_ref"]) for value in event["target_transitions"]]
    for action in event["required_actions"]:
        action["transition_ids"].append(second["transition_id"])
    event["required_actions"].append({
        "action_id": "action_revalidate_binding_fixture_002", "transition_ids": [second["transition_id"]],
        "action": "revalidate_binding", "deadline_at": event["effective_at"], "verification_evidence_required": True,
        "verification_policy_sha256": builder.h("7"),
    })
    builder.seal_invalidation_event(event)
    return event


def test_invalidation_preserves_heterogeneous_per_target_transitions(builder, contracts):
    schemas, registry = contracts
    event = heterogeneous_invalidation(builder)
    assert not errors_for(schemas["maskfactory_invalidation_event_v2.schema.json"], event, registry)
    builder.validate_invalidation_event_record(event)
    assert {value["transition_id"] for value in event["target_transitions"]} == {"transition_fixture_001", "transition_fixture_002"}
    assert {value["action"] for value in event["required_actions"]} == {"block_dependent_pass", "revalidate_adoption", "revalidate_binding"}


@pytest.mark.parametrize("mutation", ["duplicate_target", "affected_union", "action_union", "unrelated_scope", "producer_payload_ref", "no_state_change"])
def test_invalidation_lossless_projection_rejects_corruption(builder, contracts, mutation):
    schemas, registry = contracts
    event = heterogeneous_invalidation(builder)
    if mutation == "duplicate_target":
        for key in ("target_kind", "target_id", "target_sha256", "main_target_ref"):
            event["target_transitions"][1][key] = copy.deepcopy(event["target_transitions"][0][key])
    elif mutation == "affected_union":
        event["affected_refs"].pop()
    elif mutation == "action_union":
        event["required_actions"] = [
            action for action in event["required_actions"]
            if action["action"] != "block_dependent_pass"
        ]
    elif mutation == "unrelated_scope":
        event["target_transitions"][1]["unrelated_scope_preserved"] = False
    elif mutation == "producer_payload_ref":
        event["producer_payload_ref"] = builder.ref("mask_authority_invalidation_event", "wrong_payload", "f")
    else:
        event["target_transitions"][1]["new_authority_state"] = event["target_transitions"][1]["previous_authority_state"]
    builder.seal_invalidation_event(event)
    schema_errors = errors_for(schemas["maskfactory_invalidation_event_v2.schema.json"], event, registry)
    semantic_error = None
    try:
        builder.validate_invalidation_event_record(event)
    except ValueError as exc:
        semantic_error = exc
    assert schema_errors or semantic_error, mutation


def test_invalidation_stream_binds_supersession_and_idempotency(builder):
    first = copy.deepcopy(builder.build_examples()["maskfactory_invalidation_event_v2.example.json"])
    second = copy.deepcopy(first)
    second.update({
        "maskfactory_invalidation_event_v2_id": "maskfactory_invalidation_event_v2_fixture_002", "event_id": "invalidation_event_fixture_002",
        "sequence": 2, "correlation_id": first["correlation_id"], "causation_id": first["event_id"],
        "idempotency_key": "invalidation_idempotency_fixture_002",
        "producer_payload_ref": builder.ref("mask_authority_invalidation_event", "producer_invalidation_fixture_002", "7"),
        "producer_payload_sha256": builder.h("7"), "tombstone_sha256": builder.h("7"),
        "supersedes_invalidation_ref": {
            "record_type": first["record_type"], "record_id": first["maskfactory_invalidation_event_v2_id"],
            "revision": first["revision"], "sha256": first["invalidation_event_sha256"],
        },
    })
    builder.seal_invalidation_event(second)
    builder.validate_invalidation_stream([first, second])

    wrong_supersession = copy.deepcopy(second)
    wrong_supersession["supersedes_invalidation_ref"]["sha256"] = builder.h("f")
    builder.seal_invalidation_event(wrong_supersession)
    with pytest.raises(ValueError, match="supersession"):
        builder.validate_invalidation_stream([first, wrong_supersession])

    reused_idempotency = copy.deepcopy(second)
    reused_idempotency["idempotency_key"] = first["idempotency_key"]
    builder.seal_invalidation_event(reused_idempotency)
    with pytest.raises(ValueError, match="idempotency"):
        builder.validate_invalidation_stream([first, reused_idempotency])


def test_items_and_tracker_sidecars_match():
    item_req = ROOT / "Plan/Items/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_REQUIREMENTS.json"
    tracker_req = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_REQUIREMENTS.json"
    assert item_req.read_bytes() == tracker_req.read_bytes()
    with (ROOT / "Plan/Items/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ITEM_ROWS.csv").open(encoding="utf-8", newline="") as handle:
        items = list(csv.DictReader(handle))
    with (ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_TRACKER_ROWS.csv").open(encoding="utf-8", newline="") as handle:
        trackers = list(csv.DictReader(handle))
    assert len(items) == len(trackers) == 28
    assert [row["item_id"] for row in items] == [row["item_id"] for row in trackers]
    assert all(row["tracker_state"] == "planned_not_started" for row in trackers)


def test_coverage_is_mirrored_and_truthful():
    left = ROOT / "Plan/Instructions/QA/Evidence/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PLANNING_COVERAGE.json"
    right = ROOT / "Plan/Tracker/Evidence/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PLANNING_COVERAGE.json"
    assert left.read_bytes() == right.read_bytes()
    payload = json.loads(left.read_text(encoding="utf-8"))
    assert payload["rows"] == 28 and payload["workstreams"] == 7
    assert payload["row348_directly_depends_on_row218"] is True
    for field in [
        "out_of_band_signer_trust_and_decision_time_revocation_present",
        "input_roi_output_artifact_identity_firewall_present",
        "multi_entity_scene_roster_present",
        "typed_executable_transform_chain_present",
        "exact_still_frame_span_scope_present",
        "conditional_runtime_provenance_and_execution_observation_present",
        "signed_checkpointed_fork_intolerant_journal_present",
        "outcome_unknown_reconciliation_state_present",
        "canonical_auth_nonce_replay_and_safe_import_policy_present",
        "llm_vlm_tool_memory_non_authority_boundary_present",
        "operational_claim_class_firewall_present",
        "fixture_release_and_adoption_firewall_present",
        "closed_row218_and_rows321_347_gate_set_present",
        "row348_aggregates_derived_from_hashed_signed_gate_reports",
        "cross_document_readiness_derivation_present",
        "lossless_per_target_invalidation_transition_and_supersession_present",
        "complete_invalidation_to_adoption_revalidation_trigger_path_present",
    ]:
        assert payload[field] is True
    assert payload["producer_planning_bindings_finalized"] is True
    assert payload["producer_planning_commit"] == "938b469"
    assert payload["producer_runtime_release_adoption_pending"] is True
    assert payload["runtime_completion_claimed"] is False
    assert payload["runtime_adapter_implemented"] is False


def test_preservation_manifest_hashes_every_entry():
    path = ROOT / "Plan/Instructions/Hydration_Rehydration/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PRESERVATION_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["runtime_completion_claimed"] is False
    assert len({entry["path"] for entry in manifest["entries"]}) == len(manifest["entries"])
    for entry in manifest["entries"]:
        content = (ROOT / entry["path"]).read_bytes()
        assert len(content) == entry["bytes"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]


def test_master_and_handoff_preserve_decisions():
    master = (ROOT / "Plan/00_PROJECT_CONTROL/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_AND_RELEASE_HANDSHAKE_MASTER_PLAN.md").read_text(encoding="utf-8")
    handoff = (ROOT / "Plan/Instructions/Hydration_Rehydration/MASKFACTORY_AUTONOMOUS_BRIDGE_MAIN_SESSION_HANDOFF.md").read_text(encoding="utf-8")
    for phrase in ["runtime/data bridge", "Project/session coordination bridge", "access_mode", "core_autonomous_runtime", "No planning file"]:
        assert phrase in master
    assert "019f422f-88b1-7382-872b-21de2089e983" in handoff
    assert "019f4cfc-60c3-7500-8626-261dcf70db5d" in handoff
    assert "Do not delete" in handoff
    assert "planning-contract coverage only" in handoff


def test_wave64_and_global_indexes_include_additive_range():
    expectations = {
        "Plan/Items/Waves/Wave64/README.md": ["Rows321-348", "WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ITEM_ROWS.csv"],
        "Plan/Tracker/Waves/Wave64/README.md": ["Rows321-348", "WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_TRACKER_ROWS.csv"],
        "Plan/Items/README.md": ["Wave64 MaskFactory Autonomous Bridge Sidecar", "core_autonomous_runtime"],
        "Plan/Tracker/README.md": ["Wave64 MaskFactory Autonomous Bridge Sidecar", "Row348 directly depends on Row218", "active, unrevoked", "Blocked_Independent_Anchor_Dependency_Missing"],
        "Plan/Instructions/WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md": ["Rows321-348", "Independent Anchor Mask Dependency Rule", "not a global dependency"],
        "Plan/Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md": ["not a dependency for", "maskfactory_autonomous", "Blocked_Independent_Anchor_Dependency_Missing", "must not hard-code human issuance"],
        "Plan/Instructions/COMPLETION_DEFINITION_AND_DONE_GATE.md": ["For `core_autonomous_runtime`", "maskfactory_autonomous", "Legacy `Blocked_Gold_Mask_Dependency_Missing` statuses migrate"],
        "Plan/Instructions/Hydration_Rehydration/BLOCKERS.md": ["Current Mask Authority Supersession - 2026-07-17", "Re-evaluate any active legacy blocker"],
        "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md": ["Current Mask Authority Supersession - 2026-07-17", "Do not interpret historical manual body-gold language"],
        "Plan/Instructions/Hydration_Rehydration/RECENT_DECISIONS.md": ["Current Mask Authority Supersession - 2026-07-17", "supersedes the operational interpretation"],
        "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md": ["Current Mask Authority Supersession - 2026-07-17", "not current global"],
        "Plan/Instructions/Hydration_Rehydration/KNOWN_ISSUES.md": ["Current Mask Authority Supersession - 2026-07-17", "pending v2 re-evaluation"],
        "Plan/README.md": ["Autonomous core and independent-anchor mask boundary", "not a global or `core_autonomous_runtime` dependency"],
        "Plan/03_IMAGE_SYSTEM/MASK_FACTORY_SPEC.md": ["For core, the issuer may be `maskfactory_autonomous`", "human-anchor masks are optional"],
        "Plan/03_IMAGE_SYSTEM/IMAGE_PIPELINE_BLUEPRINT.md": ["Core authority may come from", "manual/human anchors are optional"],
        "Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_FACTORY_PROMOTION_GATES.md": ["Blocked_Independent_Anchor_Dependency_Missing", "maskfactory_autonomous"],
        "Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md": ["independent_real_accuracy", "must not block", "maskfactory_autonomous"],
        "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md": ["optional dependency", "not a blocker", "maskfactory_autonomous"],
        "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md": ["optional", "exact-output `maskfactory_autonomous`", "Waves71+ remain separately deferred"],
        "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md": ["authority-qualified exact mask", "human/manual annotation", "maskfactory_autonomous"],
    }
    for relative, phrases in expectations.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, (relative, phrase)


def test_latest_current_goal_supersedes_historical_manual_core_mask_blockers():
    text = (ROOT / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md").read_text(encoding="utf-8")
    marker = "## Current Mask Authority and Bridge Supersession - 2026-07-17"
    assert marker in text
    assert text.rfind(marker) > text.rfind("manual body gold masks remain unavailable")
    latest = text[text.rfind(marker):]
    for phrase in [
        "not a dependency for `core_autonomous_runtime`",
        "No human anchor is required for this core path",
        "Rows321-348 remain planned autonomous implementation work",
        "do not delete it as dirty or unrelated work",
    ]:
        assert phrase in latest


def test_app_live_qa_dial_is_non_authoritative():
    text = (ROOT / "Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md").read_text(encoding="utf-8")
    assert "display/proposal only" in text
    assert "maskfactory_promotion_gate_policy_v2" in text
    assert "App values cannot mutate that policy" in text


def test_project_manifest_uses_profile_scoped_anchor_blocker():
    manifest = json.loads((ROOT / "Plan/PROJECT_MANIFEST.json").read_text(encoding="utf-8"))
    maskfactory = manifest["wave70_ultimate_mask_factory_extension"]
    assert maskfactory["blocked_status_code"] == "Blocked_Independent_Anchor_Dependency_Missing"
    assert "maskfactory_autonomous" in maskfactory["non_mask_work_rule"]


def test_active_manual_gold_language_is_profile_scoped_and_historical_report_is_unchanged(builder):
    stale_sentences = {
        "Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md": "Manual gold masks remain a dependency boundary.",
        "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md": "the manual body/body-part dependency remains active and unchanged",
        "Plan/Tracker/README.md": "For Wave 70 rows that require manual gold-standard masks, use `Blocked_Gold_Mask_Dependency_Missing`",
        "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md": "Manual body gold masks are not ready. Do not promote candidate masks",
    }
    for relative, sentence in stale_sentences.items():
        assert sentence not in (ROOT / relative).read_text(encoding="utf-8")
    for relative in stale_sentences:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "independent_real_accuracy" in text
        assert "maskfactory_autonomous" in text
    foley = (ROOT / "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md").read_text(encoding="utf-8")
    assert "authority-qualified exact mask" in foley
    assert "human/manual annotation" in foley
    historical = ROOT / "Plan/Items/Reports/ITEM-W64-012_image_mask_control.json"
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == "d743e5c38fa591ed22a4b7926b02a71d7305574ebb9c8eb77f9a569259571995"
    migration = builder.build_registries()["wave64_maskfactory_bridge_legacy_migration_crosswalk_v2.json"]
    historical_rule = next(item for item in migration["migrations"] if item["legacy_surface"].endswith(historical.name))
    assert historical_rule["historical_evidence_mutable"] is False
    assert "cannot block core" in historical_rule["migration_rule"]
