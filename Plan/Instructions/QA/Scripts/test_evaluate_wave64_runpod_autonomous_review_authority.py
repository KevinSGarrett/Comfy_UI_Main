from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
EVALUATOR_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_review_authority.py"


def load_evaluator():
    spec = importlib.util.spec_from_file_location("w64_aqa_review_authority", EVALUATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(*, production: bool = False, width: int = 1024) -> dict:
    roles = ["W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-ROLE-PRIMARY-VISUAL", "W64-AQA-ROLE-INDEPENDENT-JUROR"] if production else ["W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-ROLE-STRICT-VISUAL"]
    return {
        "schema_version": "wave64.aqa.job_contract.v1", "contract_id": "a" * 64,
        "job_id": "W64-AQA-JOB-test", "modality": "image",
        "preflight_disposition": "READY_FOR_LEASE",
        "promotion_disposition": "PRODUCTION_ELIGIBLE_IF_ALL_GATES_PASS" if production else "EVIDENCE_ONLY",
        "image_spec": {"width": width, "height": 1024},
        "quality_profile": {
            "required_approval_roles": roles,
            "review_roles": [
                {"role_id": role, "can_approve": True, "required": True, "authority": "deterministic" if role.endswith("DETERMINISTIC") else "strict"}
                for role in roles
            ] + [{"role_id": "W64-AQA-ROLE-FAST-TRIAGE", "can_approve": False, "required": False, "authority": "triage"}],
        },
    }


def certificate(module, role: str, *, width: int = 2048, expires: str = "2026-08-21T00:00:00Z") -> dict:
    value = {
        "schema_version": "wave64.aqa.role_qualification_certificate.v1",
        "certificate_id": "0" * 64, "report_sha256": "1" * 64,
        "role_id": role, "model_id": f"model-{role.lower()}",
        "checkpoint_sha256": "2" * 64, "runtime_digest": "3" * 64,
        "prompt_sha256": "4" * 64, "corpus_sha256": "5" * 64,
        "issued_at": "2026-07-21T00:00:00Z", "expires_at": expires,
        "scope": {"modalities": ["image"], "max_width": width, "max_height": 2048, "max_duration_seconds": 0, "quantization": "test", "gpu_profile": "test"},
        "thresholds": {},
        "metrics": {"fixture_count": 9, "run_count": 18, "false_accept_rate": 0, "false_reject_rate": 0, "invalid_schema_rate": 0, "repeatability_rate": 1, "refusal_correctness_rate": 1},
        "coverage_categories": ["known_good"],
        "qualification_disposition": "QUALIFIED_FOR_DECLARED_SCOPE",
        "operational_authority_granted": True,
        "reason_codes": ["EXACT_SCOPE_CAPACITY_QUALITY_AND_RELIABILITY_QUALIFIED"],
    }
    value["certificate_id"] = module.hashlib.sha256(module.canonical_bytes(value)).hexdigest()
    return value


def observation(module, cert: dict, *, decision: str = "PASS", claim: bool = True) -> dict:
    value = {
        "schema_version": "wave64.aqa.reviewer_observation.v1", "observation_id": "0" * 64,
        "job_id": "W64-AQA-JOB-test", "contract_id": "a" * 64,
        "role_id": cert["role_id"], "model_id": cert["model_id"],
        "checkpoint_sha256": cert["checkpoint_sha256"], "runtime_digest": cert["runtime_digest"],
        "prompt_sha256": cert["prompt_sha256"], "qualification_certificate_id": cert["certificate_id"],
        "decision": decision, "structured_response_valid": True,
        "product_authority_claimed": claim, "defects": [], "evidence_sha256": ["6" * 64],
    }
    value["observation_id"] = module.hashlib.sha256(module.canonical_bytes(value)).hexdigest()
    return value


def evidence(module, spec: dict) -> tuple[list[dict], list[dict]]:
    certificates = [certificate(module, role) for role in spec["quality_profile"]["required_approval_roles"]]
    return [observation(module, cert) for cert in certificates], certificates


def test_shadow_strict_lane_passes_as_evidence_only_without_promotion() -> None:
    module = load_evaluator()
    spec = contract()
    observations, certificates = evidence(module, spec)
    first = module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    second = module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    assert first == second
    assert first["review_disposition"] == "PASS_REQUIRED_AUTHORITIES"
    assert first["evidence_only"] is True
    assert first["promotion_authorized"] is False


def test_production_requires_deterministic_primary_and_independent_juror() -> None:
    module = load_evaluator()
    spec = contract(production=True)
    observations, certificates = evidence(module, spec)
    result = module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    assert result["review_disposition"] == "PASS_REQUIRED_AUTHORITIES"
    missing = observations[:-1]
    result = module.evaluate_authority(spec, missing, certificates, "2026-07-22T00:00:00Z")
    assert result["review_disposition"] == "BLOCKED_REQUIRED_AUTHORITY"


def test_qualified_required_failure_rejects_review_pass() -> None:
    module = load_evaluator()
    spec = contract()
    observations, certificates = evidence(module, spec)
    observations[1] = observation(module, certificates[1], decision="FAIL")
    result = module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    assert result["review_disposition"] == "FAIL_REQUIRED_AUTHORITY"


def test_triage_never_counts_and_authority_claim_blocks() -> None:
    module = load_evaluator()
    spec = contract()
    observations, certificates = evidence(module, spec)
    triage_cert = certificate(module, "W64-AQA-ROLE-FAST-TRIAGE")
    certificates.append(triage_cert)
    observations.append(observation(module, triage_cert, claim=False))
    result = module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    assert result["review_disposition"] == "PASS_REQUIRED_AUTHORITIES"
    observations[-1] = observation(module, triage_cert, claim=True)
    result = module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    assert result["review_disposition"] == "BLOCKED_REQUIRED_AUTHORITY"
    assert result["promotion_authorized"] is False


def test_expired_scope_limited_and_fingerprint_mismatched_certificates_block() -> None:
    module = load_evaluator()
    spec = contract()
    observations, certificates = evidence(module, spec)
    certificates[1] = certificate(module, "W64-AQA-ROLE-STRICT-VISUAL", expires="2026-07-21T12:00:00Z")
    observations[1] = observation(module, certificates[1])
    assert module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")["review_disposition"] == "BLOCKED_REQUIRED_AUTHORITY"
    certificates[1] = certificate(module, "W64-AQA-ROLE-STRICT-VISUAL", width=512)
    observations[1] = observation(module, certificates[1])
    assert module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")["review_disposition"] == "BLOCKED_REQUIRED_AUTHORITY"
    certificates[1] = certificate(module, "W64-AQA-ROLE-STRICT-VISUAL")
    observations[1] = observation(module, certificates[1])
    observations[1]["runtime_digest"] = "f" * 64
    observations[1]["observation_id"] = "0" * 64
    observations[1]["observation_id"] = module.hashlib.sha256(module.canonical_bytes(observations[1])).hexdigest()
    assert module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")["review_disposition"] == "BLOCKED_REQUIRED_AUTHORITY"


def test_tampered_certificate_duplicate_observation_and_triage_required_fail_closed() -> None:
    module = load_evaluator()
    spec = contract()
    observations, certificates = evidence(module, spec)
    certificates[0]["model_id"] = "tampered"
    with pytest.raises(module.ReviewAuthorityError, match="content hash"):
        module.evaluate_authority(spec, observations, certificates, "2026-07-22T00:00:00Z")
    observations, certificates = evidence(module, spec)
    with pytest.raises(module.ReviewAuthorityError, match="duplicate observation"):
        module.evaluate_authority(spec, observations + [observations[0]], certificates, "2026-07-22T00:00:00Z")
    spec["quality_profile"]["required_approval_roles"] = ["W64-AQA-ROLE-FAST-TRIAGE"]
    spec["quality_profile"]["review_roles"][-1]["can_approve"] = True
    spec["quality_profile"]["review_roles"][-1]["required"] = True
    with pytest.raises(module.ReviewAuthorityError, match="triage"):
        module.evaluate_authority(spec, [], [], "2026-07-22T00:00:00Z")
