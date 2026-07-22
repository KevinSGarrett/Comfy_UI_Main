from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/control_wave64_audio_runtime_cache_cost.py"
SPEC = importlib.util.spec_from_file_location("control_wave64_audio_runtime_cache_cost", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def policy():
    return MOD.load_json(ROOT / MOD.POLICY_PATH)


def identity(label="base"):
    return {field: MOD.stable_hash(f"{label}:{field}") for field in MOD.HASH_FIELDS}


def lease(now):
    return {"lease_id": "lease-test", "project": "comfyui_main", "profile": "comfyui_model_qualification", "expires_at": (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"), "valid": True, "lease_mode": "exclusive"}


def items(count=2):
    return [{"item_id": f"item-{index}", "input_sha256": MOD.stable_hash(f"input:{index}"), "estimated_peak_vram_gib": 4.0, "estimated_cost_usd": 0.02} for index in range(count)]


def test_cache_key_is_deterministic_and_every_identity_hash_invalidates():
    baseline = MOD.compute_cache_key(identity())
    assert baseline == MOD.compute_cache_key(identity())
    for field in MOD.HASH_FIELDS:
        changed = identity()
        changed[field] = MOD.stable_hash(f"changed:{field}")
        assert MOD.compute_cache_key(changed) != baseline


def test_cache_identity_missing_or_invalid_hash_rejected():
    missing = identity()
    missing.pop("decoder_sha256")
    with pytest.raises(MOD.AudioRuntimeControlError, match="cache_identity_fields_mismatch"):
        MOD.compute_cache_key(missing)
    bad = identity()
    bad["model_sha256"] = "x" * 64
    with pytest.raises(MOD.AudioRuntimeControlError, match="cache_identity_hash_invalid"):
        MOD.compute_cache_key(bad)


def test_batch_budget_and_vram_are_bounded():
    batch = MOD.plan_batch(items(), maximum_usd=0.10, policy=policy())
    assert batch["budget"]["estimated_usd"] == pytest.approx(0.04)
    excessive = items()
    excessive[0]["estimated_peak_vram_gib"] = 47.0
    with pytest.raises(MOD.AudioRuntimeControlError, match="batch_peak_vram_exceeded"):
        MOD.plan_batch(excessive, maximum_usd=1.0, policy=policy())
    with pytest.raises(MOD.AudioRuntimeControlError, match="estimated_cost_budget_exceeded"):
        MOD.plan_batch(items(), maximum_usd=0.01, policy=policy())


def test_duplicate_and_oversized_batches_rejected():
    duplicate = items()
    duplicate[1]["item_id"] = duplicate[0]["item_id"]
    with pytest.raises(MOD.AudioRuntimeControlError, match="duplicate_batch_item"):
        MOD.plan_batch(duplicate, maximum_usd=1.0, policy=policy())
    with pytest.raises(MOD.AudioRuntimeControlError, match="batch_item_count_invalid"):
        MOD.plan_batch(items(17), maximum_usd=2.0, policy=policy())


def test_resume_reuses_passed_item_and_preserves_pending():
    batch = MOD.plan_batch(items(), maximum_usd=0.10, policy=policy())
    prior = {"item-0": {**batch["items"][0], "state": "passed", "attempts": 1, "output_sha256": MOD.stable_hash("out")}}
    resumed = MOD.resume_batch(batch, prior)
    assert resumed["items"][0]["state"] == "reused"
    assert resumed["items"][1]["state"] == "pending"


def test_resume_rejects_changed_identity_or_missing_output():
    batch = MOD.plan_batch(items(), maximum_usd=0.10, policy=policy())
    changed = {"item-0": {**batch["items"][0], "input_sha256": MOD.stable_hash("wrong"), "state": "passed", "output_sha256": MOD.stable_hash("out")}}
    with pytest.raises(MOD.AudioRuntimeControlError, match="retained_item_identity_changed"):
        MOD.resume_batch(batch, changed)
    missing = {"item-0": {**batch["items"][0], "state": "passed", "output_sha256": None}}
    with pytest.raises(MOD.AudioRuntimeControlError, match="retained_output_hash_absent"):
        MOD.resume_batch(batch, missing)


def test_exact_sanitized_lease_required():
    now = datetime.now(timezone.utc)
    assert MOD.validate_lease(lease(now), now=now)["validated"] is True
    tokenized = lease(now)
    tokenized["lease_token"] = "secret"
    with pytest.raises(MOD.AudioRuntimeControlError, match="lease_secret_material_forbidden"):
        MOD.validate_lease(tokenized, now=now)
    expired = lease(now)
    expired["expires_at"] = (now - timedelta(seconds=1)).isoformat()
    with pytest.raises(MOD.AudioRuntimeControlError, match="lease_expired"):
        MOD.validate_lease(expired, now=now)


def test_foreign_lease_rejected():
    now = datetime.now(timezone.utc)
    foreign = lease(now)
    foreign["project"] = "maskfactory"
    with pytest.raises(MOD.AudioRuntimeControlError, match="lease_authority_invalid"):
        MOD.validate_lease(foreign, now=now)


def test_transfer_manifest_rejects_duplicate_or_invalid_entries():
    entry = {"source_sha256": MOD.stable_hash("transfer"), "bytes": 1, "destination": "/workspace/x", "verified": True}
    MOD.validate_transfer_manifest([entry])
    with pytest.raises(MOD.AudioRuntimeControlError, match="duplicate_transfer_destination"):
        MOD.validate_transfer_manifest([entry, deepcopy(entry)])


def test_fixture_receipt_is_schema_valid_but_never_runtime_authority():
    receipt = MOD.build_receipt(ROOT, synthetic=True)
    assert receipt["provider"] == "runpod"
    assert receipt["pod_id"] == "1q4ji0gg1fkhvt"
    assert receipt["decision"]["runtime_allowed"] is False
    assert receipt["decision"]["row108_acceptance"] == "fixture_only"
    assert receipt["items"][0]["state"] == "reused"


def test_live_receipt_holds_without_lease_ttl_and_release():
    receipt = MOD.build_receipt(ROOT, synthetic=False)
    assert receipt["decision"]["status"] == "blocked"
    assert {"EXACT_COORDINATOR_LEASE_ABSENT", "TTL_WATCHDOG_RECEIPT_ABSENT", "FINAL_LEASE_RELEASE_RECEIPT_ABSENT"} <= set(receipt["decision"]["blocker_codes"])


def test_tampered_cache_key_and_receipt_rejected():
    receipt = MOD.build_receipt(ROOT, synthetic=True)
    cache_tampered = deepcopy(receipt)
    cache_tampered["cache_entries"][0]["cache_key"] = "a" * 64
    cache_tampered["receipt_sha256"] = MOD.hashlib.sha256(MOD.canonical_bytes({k: v for k, v in cache_tampered.items() if k != "receipt_sha256"})).hexdigest()
    with pytest.raises(MOD.AudioRuntimeControlError, match="cache_key_recompute_mismatch"):
        MOD.validate_receipt(ROOT, cache_tampered)
    receipt["budget"]["maximum_usd"] = 99
    with pytest.raises(MOD.AudioRuntimeControlError, match="receipt_sha256_mismatch"):
        MOD.validate_receipt(ROOT, receipt)


def test_runtime_completion_requires_actual_cost_watchdog_and_release():
    receipt = MOD.build_receipt(ROOT, synthetic=True)
    receipt["decision"]["runtime_completion"] = True
    receipt["receipt_sha256"] = MOD.hashlib.sha256(MOD.canonical_bytes({k: v for k, v in receipt.items() if k != "receipt_sha256"})).hexdigest()
    with pytest.raises(MOD.AudioRuntimeControlError, match="runtime_completion_proof_incomplete"):
        MOD.validate_receipt(ROOT, receipt)


def test_dependency_evidence_binds_absent_row101_fail_closed():
    admissions = MOD.dependency_admissions(ROOT)
    assert admissions["TRK-W64-069"]["dependency_satisfied"] is True
    assert admissions["TRK-W64-101"]["status"] == "ABSENT"
    assert admissions["TRK-W64-101"]["sha256"] == "0" * 64


def test_evidence_truthfully_holds_runtime():
    evidence = MOD.build_evidence(ROOT)
    assert evidence["row_complete"] is False
    assert evidence["runtime_completion_claimed"] is False
    assert evidence["sole_current_runtime"]["pod_id"] == "1q4ji0gg1fkhvt"
    assert "ROW108_DEPENDENCIES_NOT_ACCEPTED" in evidence["decision"]["blocker_codes"]
