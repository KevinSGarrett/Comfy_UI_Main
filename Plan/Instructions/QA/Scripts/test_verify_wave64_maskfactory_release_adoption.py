from __future__ import annotations

import copy
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/verify_wave64_maskfactory_release_adoption.py"
REGISTRY = ROOT / "Plan/10_REGISTRIES/wave64_maskfactory_release_adoption_verifier_registry.json"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_maskfactory_release_adoption_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verifier():
    return load_module()


def write_fixture_bundle(verifier, root: Path) -> None:
    examples = verifier.CORE.build_examples()
    names = {
        "release.json": "maskfactory_release_snapshot_v2.example.json",
        "adoption.json": "maskfactory_adoption_receipt_v2.example.json",
        "consumer.json": "maskfactory_consumer_requirements_v2.example.json",
    }
    for output, source in names.items():
        (root / output).write_bytes(verifier.canonical_json(examples[source]))


def test_fixture_bundle_validates_without_active_pin(verifier, tmp_path):
    write_fixture_bundle(verifier, tmp_path)
    result = verifier.verify_bundle_root(tmp_path, allow_fixture=True, state_root=None)
    assert result["status"] == "PASS"
    assert result["classification"] == "MASKFACTORY_FIXTURE_CONTRACT_VERIFIED_NOT_ADOPTED"
    assert result["production_consumption_allowed"] is False
    assert result["active_pin_write_allowed"] is False
    assert result["runtime_completion_claimed"] is False
    assert "pin" not in result


def test_fixture_bundle_fails_when_fixture_mode_is_not_explicit(verifier, tmp_path):
    write_fixture_bundle(verifier, tmp_path)
    with pytest.raises(ValueError, match="fixture-only release"):
        verifier.verify_bundle_root(tmp_path, allow_fixture=False, state_root=None)


def test_duplicate_json_keys_fail_closed(verifier, tmp_path):
    write_fixture_bundle(verifier, tmp_path)
    (tmp_path / "release.json").write_text('{"record_type":"a","record_type":"b"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        verifier.verify_bundle_root(tmp_path, allow_fixture=True, state_root=None)


@pytest.mark.parametrize("member", ["../escape.json", "/absolute.json", "C:/drive.json"])
def test_zip_path_escape_fails_closed(verifier, tmp_path, member):
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(member, "{}")
    with pytest.raises(ValueError, match="unsafe archive member path"):
        verifier.safe_extract_zip(archive, tmp_path / "out")


def test_windows_separator_is_rejected_before_path_resolution(verifier):
    with pytest.raises(ValueError, match="unsafe archive member path"):
        verifier._safe_member_path("a\\b.json")


def test_zip_case_collision_fails_closed(verifier, tmp_path):
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("Release.json", "{}")
        bundle.writestr("release.json", "{}")
    with pytest.raises(ValueError, match="case-colliding"):
        verifier.safe_extract_zip(archive, tmp_path / "out")


def test_context_artifact_hash_and_path_are_verified(verifier, tmp_path):
    payload = b"hash-bound artifact"
    artifact = tmp_path / "artifacts" / "one.bin"
    artifact.parent.mkdir()
    artifact.write_bytes(payload)
    ref = {"record_type": "runtime_evidence", "record_id": "one", "revision": "r1", "sha256": verifier.sha256_bytes(payload)}
    context_path = tmp_path / "verification_context.json"
    context_path.write_text(json.dumps({
        "schema_version": "1.0.0",
        "artifact_files": [{"ref": ref, "path": "artifacts/one.bin"}],
        "producer_wire_schema_files": {},
    }), encoding="utf-8")
    context = verifier.load_runtime_context(tmp_path, context_path)
    assert context["artifact_bytes"][verifier._ref_key(ref)] == payload
    ref["sha256"] = "f" * 64
    context_path.write_text(json.dumps({
        "schema_version": "1.0.0",
        "artifact_files": [{"ref": ref, "path": "artifacts/one.bin"}],
        "producer_wire_schema_files": {},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verifier.load_runtime_context(tmp_path, context_path)


def test_atomic_pin_is_idempotent_and_preserves_previous(verifier, tmp_path):
    examples = verifier.CORE.build_examples()
    release = copy.deepcopy(examples["maskfactory_release_snapshot_v2.example.json"])
    adoption = copy.deepcopy(examples["maskfactory_adoption_receipt_v2.example.json"])
    adoption.update({
        "production_consumption_allowed": True,
        "active_pin_written": True,
        "fixture_only": False,
        "adoption_context": "production_runtime",
    })
    verification = {"active_pin_write_allowed": True}
    first = verifier.write_active_pin(tmp_path, release, adoption, verification)
    second = verifier.write_active_pin(tmp_path, release, adoption, verification)
    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert first["active_pin_sha256"] == second["active_pin_sha256"]

    release["maskfactory_release_snapshot_v2_id"] = "release_fixture_002"
    release["release_id"] = "maskfactory_release_fixture_002"
    adoption["maskfactory_adoption_receipt_v2_id"] = "adoption_fixture_002"
    third = verifier.write_active_pin(tmp_path, release, adoption, verification)
    assert third["idempotent"] is False
    assert third["active_pin"]["previous_pin_sha256"] == first["active_pin_sha256"]
    assert (tmp_path / "history" / f"{first['active_pin_sha256']}.json").is_file()


def test_fixture_cannot_write_active_pin(verifier, tmp_path):
    examples = verifier.CORE.build_examples()
    with pytest.raises(ValueError, match="forbidden"):
        verifier.write_active_pin(
            tmp_path,
            examples["maskfactory_release_snapshot_v2.example.json"],
            examples["maskfactory_adoption_receipt_v2.example.json"],
            {"active_pin_write_allowed": False},
        )


def test_unpublished_record_is_exact_and_fail_closed(verifier):
    record = verifier.unpublished_record()
    assert record["status"] == "BLOCKED"
    assert record["classification"] == verifier.UNPUBLISHED_BLOCKER
    assert record["runtime_release_published"] is False
    assert record["production_consumption_allowed"] is False
    assert record["runtime_completion_claimed"] is False
    assert set(record["row_states"]) == {"ITEM-W64-321", "ITEM-W64-322", "ITEM-W64-323", "ITEM-W64-324"}


def test_registry_binds_final_design_pins_without_runtime_promotion():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    pins = registry["adopted_design_pins"]
    assert pins["main_pr_133_head"] == "a54a7ed2bad472f77168e190b9881b4f7e7cc589"
    assert pins["maskfactory_pr_2_validation_head"] == "6361df208e01d183083ee6c113e016467a486706"
    assert pins["integration_reconciliation_seal"] == "c948da1595f6c29ead2aeda950ac778717c6557f2ed5f6c4b0664e5052f3eb52"
    assert pins["frozen_wire_contract_count"] == 12
    assert pins["pins_are_design_time_not_runtime_authority"] is True
    assert registry["production_consumption_allowed"] is False
    assert registry["runtime_completion_claimed"] is False
