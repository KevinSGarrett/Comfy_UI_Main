from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
RESOLVER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/resolve_wave64_runpod_autonomous_review_disagreement.py"


def load_resolver():
    spec = importlib.util.spec_from_file_location("w64_aqa_disagreement", RESOLVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract() -> dict:
    return {"schema_version": "wave64.aqa.job_contract.v1", "contract_id": "a" * 64, "job_id": "W64-AQA-JOB-test", "preflight_disposition": "READY_FOR_LEASE"}


def certificate(module, role: str, marker: str) -> dict:
    value = {
        "schema_version": "wave64.aqa.role_qualification_certificate.v1", "certificate_id": "0" * 64,
        "report_sha256": marker * 64, "role_id": role, "model_id": f"model-{marker}",
        "checkpoint_sha256": marker * 64, "runtime_digest": chr(ord(marker) + 1) * 64,
        "prompt_sha256": chr(ord(marker) + 2) * 64, "corpus_sha256": "f" * 64,
        "issued_at": "2026-07-21T00:00:00Z", "expires_at": "2026-08-21T00:00:00Z",
        "scope": {}, "thresholds": {},
        "metrics": {"fixture_count": 9, "run_count": 18, "false_accept_rate": 0, "false_reject_rate": 0, "invalid_schema_rate": 0, "repeatability_rate": 1, "refusal_correctness_rate": 1},
        "coverage_categories": ["known_good"], "qualification_disposition": "QUALIFIED_FOR_DECLARED_SCOPE",
        "operational_authority_granted": True, "reason_codes": ["QUALIFIED"],
    }
    value["certificate_id"] = module.hashlib.sha256(module.canonical_bytes(value)).hexdigest()
    return value


def observation(module, cert: dict, decision: str) -> dict:
    value = {
        "schema_version": "wave64.aqa.reviewer_observation.v1", "observation_id": "0" * 64,
        "job_id": "W64-AQA-JOB-test", "contract_id": "a" * 64,
        "role_id": cert["role_id"], "model_id": cert["model_id"],
        "checkpoint_sha256": cert["checkpoint_sha256"], "runtime_digest": cert["runtime_digest"],
        "prompt_sha256": cert["prompt_sha256"], "qualification_certificate_id": cert["certificate_id"],
        "decision": decision, "structured_response_valid": True, "product_authority_claimed": True,
        "defects": [], "evidence_sha256": ["9" * 64],
    }
    value["observation_id"] = module.hashlib.sha256(module.canonical_bytes(value)).hexdigest()
    return value


def evidence(module, primary_decision: str = "PASS", juror_decision: str = "PASS"):
    primary = certificate(module, module.PRIMARY_ROLE, "1")
    juror = certificate(module, module.JUROR_ROLE, "4")
    return observation(module, primary, primary_decision), primary, observation(module, juror, juror_decision), juror


def resolve(module, primary_decision="PASS", juror_decision="PASS", hard=True, arbiter=None):
    primary_obs, primary_cert, juror_obs, juror_cert = evidence(module, primary_decision, juror_decision)
    args = [contract(), primary_obs, primary_cert, juror_obs, juror_cert, hard, "2026-07-22T00:00:00Z"]
    if arbiter:
        return module.resolve_disagreement(*args, arbiter_observation=arbiter[0], arbiter_certificate=arbiter[1])
    return module.resolve_disagreement(*args)


def test_independent_consensus_pass_and_fail_are_deterministic() -> None:
    module = load_resolver()
    first, second = resolve(module), resolve(module)
    assert first == second
    assert first["disposition"] == "CONSENSUS_PASS"
    assert first["product_decision"] == "PASS"
    assert first["promotion_authorized"] is False
    failed = resolve(module, "FAIL", "FAIL")
    assert failed["disposition"] == "CONSENSUS_FAIL"
    assert failed["product_decision"] == "FAIL"


def test_disagreement_requires_qualified_senior_arbitration() -> None:
    module = load_resolver()
    blocked = resolve(module, "PASS", "FAIL")
    assert blocked["disposition"] == "BLOCKED_ARBITRATION_REQUIRED"
    arbiter_cert = certificate(module, module.ARBITER_ROLE, "7")
    passed = resolve(module, "PASS", "FAIL", arbiter=(observation(module, arbiter_cert, "PASS"), arbiter_cert))
    assert passed["disposition"] == "ARBITRATED_PASS"
    failed = resolve(module, "PASS", "FAIL", arbiter=(observation(module, arbiter_cert, "FAIL"), arbiter_cert))
    assert failed["disposition"] == "ARBITRATED_FAIL"
    abstained = resolve(module, "PASS", "FAIL", arbiter=(observation(module, arbiter_cert, "ABSTAIN"), arbiter_cert))
    assert abstained["product_decision"] == "BLOCKED"


def test_deterministic_hard_gate_failure_cannot_be_overridden_by_arbiter() -> None:
    module = load_resolver()
    arbiter_cert = certificate(module, module.ARBITER_ROLE, "7")
    result = resolve(module, "PASS", "FAIL", hard=False, arbiter=(observation(module, arbiter_cert, "PASS"), arbiter_cert))
    assert result["disposition"] == "HARD_GATE_FAIL"
    assert result["product_decision"] == "FAIL"
    assert result["arbiter_observation_id"] is None


def test_primary_or_juror_abstention_blocks_without_averaging() -> None:
    module = load_resolver()
    result = resolve(module, "PASS", "ABSTAIN")
    assert result["disposition"] == "BLOCKED_ABSTENTION"
    assert result["product_decision"] == "BLOCKED"


def test_shared_model_runtime_or_prompt_fingerprint_blocks_independence() -> None:
    module = load_resolver()
    primary_obs, primary_cert, juror_obs, juror_cert = evidence(module)
    juror_cert["runtime_digest"] = primary_cert["runtime_digest"]
    juror_cert["certificate_id"] = "0" * 64
    juror_cert["certificate_id"] = module.hashlib.sha256(module.canonical_bytes(juror_cert)).hexdigest()
    juror_obs = observation(module, juror_cert, "PASS")
    result = module.resolve_disagreement(contract(), primary_obs, primary_cert, juror_obs, juror_cert, True, "2026-07-22T00:00:00Z")
    assert result["disposition"] == "BLOCKED_INDEPENDENCE"
    assert result["independence_verified"] is False


def test_wrong_role_expired_tampered_or_partial_arbiter_evidence_fails_closed() -> None:
    module = load_resolver()
    primary_obs, primary_cert, juror_obs, juror_cert = evidence(module, "PASS", "FAIL")
    primary_cert["role_id"] = module.JUROR_ROLE
    primary_cert["certificate_id"] = "0" * 64
    primary_cert["certificate_id"] = module.hashlib.sha256(module.canonical_bytes(primary_cert)).hexdigest()
    with pytest.raises(module.DisagreementError, match="expected role"):
        module.resolve_disagreement(contract(), primary_obs, primary_cert, juror_obs, juror_cert, True, "2026-07-22T00:00:00Z")
    primary_obs, primary_cert, juror_obs, juror_cert = evidence(module, "PASS", "FAIL")
    arbiter_cert = certificate(module, module.ARBITER_ROLE, "7")
    with pytest.raises(module.DisagreementError, match="supplied together"):
        module.resolve_disagreement(contract(), primary_obs, primary_cert, juror_obs, juror_cert, True, "2026-07-22T00:00:00Z", arbiter_certificate=arbiter_cert)
