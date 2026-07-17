from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_maskfactory_bridge_request.py"


@pytest.fixture(scope="module")
def compiler():
    spec = importlib.util.spec_from_file_location("compile_wave64_maskfactory_bridge_request_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("compiler module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _materialize_refs(compiler, value, root: Path):
    records: dict[tuple[str, str, str], dict] = {}

    def visit(current):
        if isinstance(current, dict):
            if set(current) == {"record_type", "record_id", "revision", "sha256"}:
                identity = (current["record_type"], current["record_id"], current["revision"])
                if identity not in records:
                    payload = compiler.canonical_json(
                        {
                            "record_type": current["record_type"],
                            "record_id": current["record_id"],
                            "revision": current["revision"],
                        }
                    )
                    digest = compiler.sha256_bytes(payload)
                    path = root / f"immutable_{len(records):02d}.json"
                    path.write_bytes(payload)
                    records[identity] = {
                        "ref": {
                            "record_type": current["record_type"],
                            "record_id": current["record_id"],
                            "revision": current["revision"],
                            "sha256": digest,
                        },
                        "path": path.name,
                    }
                current["sha256"] = records[identity]["ref"]["sha256"]
            for child in current.values():
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return list(records.values())


def make_packet(compiler, tmp_path: Path, *, fixture_only: bool = True):
    request = copy.deepcopy(compiler.CORE.build_examples()["maskfactory_bridge_request_v2.example.json"])
    request["created_at"] = "2026-07-17T02:00:00-05:00"
    request["deadline_at"] = "2026-07-17T03:00:00-05:00"
    request["fixture_only"] = fixture_only
    authorization = {
        "principal_id": "main_controller_fixture_001",
        "principal_role": "maskfactory_bridge_submitter",
        "nonce": "nonce_fixture_001",
        "issued_at": "2026-07-17T01:55:00-05:00",
        "expires_at": "2026-07-17T03:05:00-05:00",
        "allowed_access_modes": [request["access_mode"]],
        "allowed_intended_uses": [request["intended_use"]],
        "authorization_ref": {
            "record_type": "main_authenticated_request_principal_nonce_record",
            "record_id": "authorization_fixture_001",
            "revision": "r001",
            "sha256": "0" * 64,
        },
    }
    record_root = tmp_path / "records"
    record_root.mkdir(parents=True)
    immutable_records = _materialize_refs(compiler, {"request": request, "authorization": authorization}, record_root)

    source_sha = request["source_artifact"]["artifact_ref"]["sha256"]
    request["source_artifact"]["sha256"] = source_sha
    request["media_scope"]["source_media_sha256"] = source_sha
    request["media_scope"]["source_media_ref"]["sha256"] = source_sha
    step = request["transform_chain"]["steps"][0]
    step["step_sha256"] = compiler.CORE.sha256_bytes(
        compiler.CORE.canonical_json({key: value for key, value in step.items() if key != "step_sha256"})
    )
    request["transform_chain"]["chain_sha256"] = compiler.CORE.sha256_bytes(
        compiler.CORE.canonical_json(
            {key: value for key, value in request["transform_chain"].items() if key != "chain_sha256"}
        )
    )
    for region in request["target_region_bindings"] + request["protected_region_bindings"]:
        region["region_sha256"] = region["region_ref"]["sha256"]
        region["source_artifact_sha256"] = source_sha
        region["transform_chain_sha256"] = request["transform_chain"]["chain_sha256"]

    body = {key: value for key, value in request.items() if key not in compiler.OWNED_REQUEST_FIELDS}
    packet = {
        "schema_version": "1.0.0",
        "record_type": compiler.INPUT_RECORD_TYPE,
        "request_revision": request["revision"],
        "created_at": request["created_at"],
        "fixture_only": fixture_only,
        "request_body": body,
        "authorization_context": authorization,
        "immutable_records": immutable_records,
        "known_output_artifact_sha256s": [],
    }
    active_pin = {
        "schema_version": "1.0.0",
        "record_type": "maskfactory_active_release_pin",
        "release_ref": copy.deepcopy(request["release_snapshot_ref"]),
        "adoption_ref": {
            "record_type": "maskfactory_adoption_receipt_v2",
            "record_id": "adoption_fixture_001",
            "revision": "r001",
            "sha256": "f" * 64,
        },
        "decided_at": "2026-07-17T01:50:00-05:00",
        "valid_until": "2026-07-17T04:00:00-05:00",
        "previous_pin_sha256": None,
        "rollback_candidate_present": False,
        "rollback_requires_fresh_revocation_revalidation": False,
        "production_consumption_allowed": True,
        "fixture_only": False,
    }
    return packet, record_root, active_pin


def compile_fixture(compiler, packet, record_root, tmp_path, *, active_pin=None, allow_fixture=True):
    return compiler.compile_request(
        packet,
        record_root=record_root,
        nonce_state_root=tmp_path / "nonces",
        active_pin=active_pin,
        allow_fixture=allow_fixture,
    )


def test_valid_fixture_compiles_stable_request_without_runtime_claim(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    request, receipt = compile_fixture(compiler, packet, record_root, tmp_path)
    compiler.VERIFY.validate_schema(request, compiler.REQUEST_SCHEMA)
    assert request["maskfactory_bridge_request_v2_id"].startswith("mfb_request_")
    assert request["idempotency_key"].startswith("mfb_idempotency_")
    assert receipt["result"] == "PASS_STATIC_REQUEST_COMPILATION_ONLY"
    assert receipt["runtime_completion_claimed"] is False
    assert receipt["production_submission_authorized"] is False
    assert receipt["fixture_only"] is True
    assert receipt["resolved_immutable_reference_count"] == len(packet["immutable_records"])


def test_compiler_derives_same_request_identity_for_same_logical_effect(compiler, tmp_path):
    first_packet, first_root, _ = make_packet(compiler, tmp_path / "first")
    second_packet, second_root, _ = make_packet(compiler, tmp_path / "second")
    second_packet["authorization_context"]["nonce"] = "nonce_fixture_002"
    first, _ = compile_fixture(compiler, first_packet, first_root, tmp_path / "first")
    second, _ = compile_fixture(compiler, second_packet, second_root, tmp_path / "second")
    assert first["maskfactory_bridge_request_v2_id"] == second["maskfactory_bridge_request_v2_id"]
    assert first["idempotency_key"] == second["idempotency_key"]


def test_closed_compile_input_and_request_body_reject_unknown_fields(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    packet["invented"] = True
    with pytest.raises(ValueError, match="closed contract"):
        compile_fixture(compiler, packet, record_root, tmp_path)
    packet.pop("invented")
    packet["request_body"]["invented"] = True
    with pytest.raises(ValueError, match="request_body fields"):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_fixture_mode_requires_explicit_authorization(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    with pytest.raises(ValueError, match="explicit allow_fixture"):
        compile_fixture(compiler, packet, record_root, tmp_path, allow_fixture=False)


def test_nonce_replay_fails_closed(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    compile_fixture(compiler, packet, record_root, tmp_path)
    with pytest.raises(ValueError, match="nonce replay"):
        compile_fixture(compiler, packet, record_root, tmp_path)


@pytest.mark.parametrize("mutation", ["missing", "unused", "hash"])
def test_immutable_reference_catalog_must_exactly_match_verified_bytes(compiler, tmp_path, mutation):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    if mutation == "missing":
        packet["immutable_records"].pop()
    elif mutation == "unused":
        payload = b"unused"
        path = record_root / "unused.bin"
        path.write_bytes(payload)
        packet["immutable_records"].append(
            {
                "ref": {
                    "record_type": "unused_record",
                    "record_id": "unused_record_001",
                    "revision": "r001",
                    "sha256": compiler.sha256_bytes(payload),
                },
                "path": path.name,
            }
        )
    else:
        path = record_root / packet["immutable_records"][0]["path"]
        path.write_bytes(b"mutated")
    with pytest.raises(ValueError, match="catalog|hash mismatch"):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_invented_reference_is_rejected(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    ref = packet["request_body"]["target_region_bindings"][0]["assignment_evidence_refs"][0]
    ref["record_id"] = "invented_assignment_reference"
    with pytest.raises(ValueError, match="catalog does not exactly cover"):
        compile_fixture(compiler, packet, record_root, tmp_path)


@pytest.mark.parametrize("mutation", ["duplicate_region", "unrostered_owner", "wrong_target"])
def test_target_and_protected_ownership_ambiguity_fails_closed(compiler, tmp_path, mutation):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    body = packet["request_body"]
    if mutation == "duplicate_region":
        body["protected_region_bindings"][0]["region_id"] = body["target_region_bindings"][0]["region_id"]
    elif mutation == "unrostered_owner":
        body["protected_region_bindings"][0]["owner_entity_id"] = "character_not_in_roster"
    else:
        body["owner_bindings"][0]["character_instance_id"] = "wrong_target_character"
    with pytest.raises(ValueError):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_target_and_protected_region_hashes_must_be_distinct(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    target = packet["request_body"]["target_region_bindings"][0]
    protected = packet["request_body"]["protected_region_bindings"][0]
    protected["region_sha256"] = target["region_sha256"]
    protected["region_ref"] = copy.deepcopy(target["region_ref"])
    with pytest.raises(ValueError, match="ambiguous hash identity"):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_known_output_collision_requires_exact_mode_a_selector(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    region = packet["request_body"]["target_region_bindings"][0]
    packet["known_output_artifact_sha256s"] = [region["region_sha256"]]
    with pytest.raises(ValueError, match="MFB_INPUT_OUTPUT_IDENTITY_COLLISION"):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_mode_a_exact_package_selector_is_only_output_collision_exception(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    body = packet["request_body"]
    body["access_mode"] = "mode_a_package_read"
    packet["authorization_context"]["allowed_access_modes"] = ["mode_a_package_read"]
    region = body["target_region_bindings"][0]
    region["selector_kind"] = "mode_a_exact_package_artifact"
    packet["known_output_artifact_sha256s"] = [region["region_sha256"]]
    request, _ = compile_fixture(compiler, packet, record_root, tmp_path)
    assert request["access_mode"] == "mode_a_package_read"


@pytest.mark.parametrize("mutation", ["missing", "mismatch", "expired"])
def test_production_request_requires_exact_current_active_pin(compiler, tmp_path, mutation):
    packet, record_root, active_pin = make_packet(compiler, tmp_path, fixture_only=False)
    selected_pin = active_pin
    if mutation == "missing":
        selected_pin = None
    elif mutation == "mismatch":
        active_pin["release_ref"]["record_id"] = "different_release"
    else:
        active_pin["valid_until"] = "2026-07-17T01:59:59-05:00"
    with pytest.raises(ValueError, match="active .*release pin|expired"):
        compile_fixture(
            compiler,
            packet,
            record_root,
            tmp_path,
            active_pin=selected_pin,
            allow_fixture=False,
        )


def test_valid_production_pin_allows_static_compilation_only(compiler, tmp_path):
    packet, record_root, active_pin = make_packet(compiler, tmp_path, fixture_only=False)
    _, receipt = compile_fixture(
        compiler,
        packet,
        record_root,
        tmp_path,
        active_pin=active_pin,
        allow_fixture=False,
    )
    assert receipt["active_release_pin_required"] is True
    assert receipt["active_release_pin_matched"] is True
    assert receipt["production_submission_authorized"] is False


@pytest.mark.parametrize("mutation", ["mode", "use", "expired"])
def test_authorization_must_cover_exact_mode_use_and_deadline(compiler, tmp_path, mutation):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    auth = packet["authorization_context"]
    if mutation == "mode":
        auth["allowed_access_modes"] = ["mode_a_package_read"]
    elif mutation == "use":
        auth["allowed_intended_uses"] = ["diagnostic"]
    else:
        auth["expires_at"] = "2026-07-17T02:30:00-05:00"
    with pytest.raises(ValueError, match="authorization"):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_contract_binding_drift_or_omission_fails_closed(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    packet["request_body"]["expected_contract_bindings"][0]["schema_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="not frozen"):
        compile_fixture(compiler, packet, record_root, tmp_path)
    packet, record_root, _ = make_packet(compiler, tmp_path / "missing")
    packet["request_body"]["expected_contract_bindings"] = packet["request_body"]["expected_contract_bindings"][:1]
    with pytest.raises(ValueError, match="omit required"):
        compile_fixture(compiler, packet, record_root, tmp_path / "missing")


def test_transform_hash_drift_fails_semantic_validation(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    packet["request_body"]["transform_chain"]["chain_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="transform chain"):
        compile_fixture(compiler, packet, record_root, tmp_path)


def test_fixture_cannot_request_promotion_and_production_policy_is_complete(compiler, tmp_path):
    packet, record_root, _ = make_packet(compiler, tmp_path)
    body = packet["request_body"]
    body["intended_use"] = "promotion_bound"
    body["production_promotion_requested"] = True
    packet["authorization_context"]["allowed_intended_uses"] = ["promotion_bound"]
    with pytest.raises(ValueError, match="fixture requests"):
        compile_fixture(compiler, packet, record_root, tmp_path)
