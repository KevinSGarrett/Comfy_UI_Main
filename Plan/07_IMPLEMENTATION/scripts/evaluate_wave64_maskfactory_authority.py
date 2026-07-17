from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
VERIFIER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/verify_wave64_maskfactory_release_adoption.py"
AUTHORITY_CROSSWALK_PATH = ROOT / "Plan/10_REGISTRIES/wave64_maskfactory_bridge_authority_crosswalk_v2.json"
LEGACY_CROSSWALK_PATH = ROOT / "Plan/10_REGISTRIES/wave64_maskfactory_bridge_legacy_migration_crosswalk_v2.json"
RESULT_SCHEMA = "maskfactory_bridge_result_v2.schema.json"
REQUEST_SCHEMA = "maskfactory_bridge_request_v2.schema.json"
POLICY_SCHEMA = "maskfactory_promotion_gate_policy_v2.schema.json"
CERTIFICATE_SCHEMA = "maskfactory_operational_certificate_v2.schema.json"
DECISION_SCHEMA = "maskfactory_authority_decision_v2.schema.json"
INVALIDATION_SCHEMA = "maskfactory_invalidation_event_v2.schema.json"
AUTHORITY_RANK = {state: index for index, state in enumerate(["invalid", "hypothesis", "draft", "qa_passed_noncertified", "certified"])}


def _load_verifier():
    spec = importlib.util.spec_from_file_location("wave64_maskfactory_release_verifier_for_authority", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("MaskFactory release verifier cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VERIFY = _load_verifier()
CORE = VERIFY.CORE


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json(path: Path) -> dict[str, Any]:
    value = VERIFY.strict_json_file(path)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if set(value) != fields:
        raise ValueError(f"{label} closed fields differ: missing={sorted(fields - set(value))} unknown={sorted(set(value) - fields)}")
    return value


def validate_authority_crosswalks(
    authority_crosswalk: dict[str, Any] | None = None,
    legacy_crosswalk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authority = authority_crosswalk or strict_json(AUTHORITY_CROSSWALK_PATH)
    legacy = legacy_crosswalk or strict_json(LEGACY_CROSSWALK_PATH)
    if authority["access_modes"] != CORE.ACCESS_MODES:
        raise ValueError("authority crosswalk access-mode vocabulary drift")
    if authority["authority_states"] != CORE.AUTHORITY_STATES:
        raise ValueError("authority crosswalk authority-state vocabulary drift")
    if authority["issuer_kinds"] != CORE.ISSUER_KINDS:
        raise ValueError("authority crosswalk issuer vocabulary drift")
    if authority["claim_classes"] != CORE.CLAIM_CLASSES:
        raise ValueError("authority crosswalk claim-class vocabulary drift")
    matrix = authority["matrix"]
    expected_pairs = {(mode, state) for mode in CORE.ACCESS_MODES for state in CORE.AUTHORITY_STATES}
    observed_pairs = {(item["access_mode"], item["authority_state"]) for item in matrix}
    if observed_pairs != expected_pairs or len(matrix) != len(expected_pairs):
        raise ValueError("authority crosswalk matrix is incomplete or duplicated")
    if any(item["access_mode_implies_authority"] or item["promotion_eligible_by_state_alone"] for item in matrix):
        raise ValueError("access mode or authority state alone cannot authorize promotion")
    firewall = authority["operational_claim_firewall"]
    if (
        firewall["counts_as_independent_real_accuracy"]
        or firewall["counts_as_training_gold"]
        or firewall["legacy_autonomous_certified_gold_alias_allowed"]
        or not firewall["operationally_certified_artifact_can_support_exact_permitted_core_production_use"]
    ):
        raise ValueError("operational certificate claim firewall is weakened")
    if authority["human_anchor_required_for_core"]:
        raise ValueError("optional human anchor was silently promoted to a core gate")
    if legacy["legacy_string_gate_can_authorize_promotion"] or legacy["live_qa_dial_can_mutate_core_decision"]:
        raise ValueError("legacy string or live QA control retains authority")
    if legacy["optional_independent_accuracy_can_mutate_core_decision"]:
        raise ValueError("optional accuracy profile can mutate the core decision")
    migrations = legacy["migrations"]
    if not migrations or any(not item["validator_required"] for item in migrations):
        raise ValueError("legacy migration lacks a required validator")
    if len({item["legacy_surface"] for item in migrations}) != len(migrations):
        raise ValueError("legacy migration surfaces are duplicated")
    return {
        "status": "PASS",
        "classification": "MASKFACTORY_AUTHORITY_CROSSWALK_FROZEN",
        "authority_state_count": len(CORE.AUTHORITY_STATES),
        "issuer_kind_count": len(CORE.ISSUER_KINDS),
        "claim_class_count": len(CORE.CLAIM_CLASSES),
        "access_mode_authority_matrix_count": len(matrix),
        "legacy_migration_count": len(migrations),
        "human_anchor_required_for_core": False,
        "runtime_completion_claimed": False,
    }


def verify_result_certificate(
    result: dict[str, Any],
    certificate: dict[str, Any] | None,
    *,
    production_required: bool,
    trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
) -> dict[str, Any]:
    VERIFY.validate_schema(result, RESULT_SCHEMA)
    if certificate is not None:
        VERIFY.validate_schema(certificate, CERTIFICATE_SCHEMA)
    CORE.validate_result_certificate_pair(
        result,
        certificate,
        trusted_keys,
        runtime_verification_context,
        use_time=use_time,
        production_required=production_required,
    )
    if certificate is not None:
        CORE.validate_operational_certificate_record(
            certificate,
            production_required=production_required,
            trusted_keys=trusted_keys,
            runtime_verification_context=runtime_verification_context,
            use_time=use_time,
        )
    certified = result["authority"]["authority_state"] == "certified"
    if certified != (certificate is not None):
        raise ValueError("certified result and exact operational certificate presence disagree")
    if production_required and (
        result["fixture_only"]
        or certificate is None
        or certificate["fixture_only"]
        or certificate["certification_context"] != "production_runtime"
    ):
        raise ValueError("production authority requires a non-fixture production certificate")
    return {
        "status": "PASS",
        "classification": "MASKFACTORY_CERTIFICATE_VERIFIED" if production_required else "MASKFACTORY_FIXTURE_OR_NONPRODUCTION_BINDING_VERIFIED",
        "production_required": production_required,
        "certificate_present": certificate is not None,
        "production_authority_verified": production_required and certificate is not None,
        "runtime_completion_claimed": False,
    }


def _result_ref(result: dict[str, Any]) -> dict[str, str]:
    return {
        "record_type": result["record_type"],
        "record_id": result["maskfactory_bridge_result_v2_id"],
        "revision": result["revision"],
        "sha256": result["normalization_payload_sha256"],
    }


def derive_authority_decision(
    request: dict[str, Any],
    result: dict[str, Any],
    policy: dict[str, Any],
    observations: dict[str, dict[str, Any]],
    *,
    certificate: dict[str, Any] | None = None,
    blockers: list[dict[str, Any]] | None = None,
    production_required: bool = False,
    trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
    decision_evidence_refs: list[dict[str, Any]] | None = None,
    genuine_runtime_evidence_refs: list[dict[str, Any]] | None = None,
    certificate_temporal_evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_authority_crosswalks()
    VERIFY.validate_schema(request, REQUEST_SCHEMA)
    VERIFY.validate_schema(result, RESULT_SCHEMA)
    VERIFY.validate_schema(policy, POLICY_SCHEMA)
    CORE.validate_request_result_pair(request, result)
    CORE.validate_promotion_policy_record(
        policy,
        trusted_keys,
        production_required=production_required,
        runtime_verification_context=runtime_verification_context,
        use_time=use_time,
    )
    certificate_report = verify_result_certificate(
        result,
        certificate,
        production_required=production_required,
        trusted_keys=trusted_keys,
        runtime_verification_context=runtime_verification_context,
        use_time=use_time,
    )
    policy_ids = [criterion["criterion_id"] for criterion in policy["criteria"]]
    if set(observations) != set(policy_ids) or len(observations) != len(policy_ids):
        raise ValueError("criterion observations do not exactly cover the signed policy")
    blockers = copy.deepcopy(blockers or [])
    evaluations: list[dict[str, Any]] = []
    for criterion in policy["criteria"]:
        observation = _exact_object(observations[criterion["criterion_id"]], {"observed", "evidence_ref"}, "criterion observation")
        passed = CORE.criterion_passes(criterion["comparator"], criterion["threshold"], observation["observed"], blockers)
        evaluations.append(
            {
                "criterion_id": criterion["criterion_id"],
                "comparator": criterion["comparator"],
                "threshold": criterion["threshold"],
                "observed": observation["observed"],
                "status": "pass" if passed else "fail",
                "evidence_ref": copy.deepcopy(observation["evidence_ref"]),
            }
        )
    observed_authority = copy.deepcopy(result["authority"])
    rank_sufficient = AUTHORITY_RANK[observed_authority["authority_state"]] >= AUTHORITY_RANK[request["minimum_authority_state"]]
    issuer_allowed = observed_authority["issuer_kind"] in request["accepted_issuer_kinds"]
    claim_allowed = observed_authority["claim_class"] in request["accepted_claim_classes"]
    scope_sufficient = set(request["required_certificate_scope"]).issubset(observed_authority["certificate_scope"])
    criteria_pass = all(item["status"] == "pass" for item in evaluations)
    runtime_refs = copy.deepcopy(genuine_runtime_evidence_refs or [])
    eligible = (
        production_required
        and not request["fixture_only"]
        and not result["fixture_only"]
        and policy["policy_context"] == "production_runtime"
        and bool(runtime_refs)
        and rank_sufficient
        and issuer_allowed
        and claim_allowed
        and scope_sufficient
        and criteria_pass
        and not blockers
        and certificate_report["production_authority_verified"]
    )
    if request["production_promotion_requested"] and not eligible:
        decision_value = "blocked"
    elif eligible:
        decision_value = "eligible"
    else:
        decision_value = "diagnostic_only"
    decision = copy.deepcopy(CORE.build_examples()["maskfactory_authority_decision_v2.example.json"])
    digest = sha256_bytes(canonical_json([_result_ref(result), policy["policy_sha256"], request["intended_use"], evaluations, blockers]))
    decision.update(
        {
            "maskfactory_authority_decision_v2_id": f"mfb_authority_decision_{digest[:24]}",
            "created_at": request["created_at"],
            "fixture_only": request["fixture_only"] or result["fixture_only"],
            "result_ref": _result_ref(result),
            "access_mode": result["access_mode"],
            "observed_authority": observed_authority,
            "required_authority_state": request["minimum_authority_state"],
            "required_issuer_kinds": copy.deepcopy(request["accepted_issuer_kinds"]),
            "required_claim_classes": copy.deepcopy(request["accepted_claim_classes"]),
            "required_certificate_scope": copy.deepcopy(request["required_certificate_scope"]),
            "intended_use": request["intended_use"],
            "decision": decision_value,
            "eligible_for_intended_use": eligible,
            "decision_at": use_time or request["created_at"],
            "certificate_temporal_evaluation": copy.deepcopy(certificate_temporal_evaluation),
            "certificate_signature_trust": copy.deepcopy(certificate["signature_trust"]) if certificate is not None and eligible else None,
            "decision_evidence_refs": copy.deepcopy(decision_evidence_refs or []),
            "genuine_runtime_evidence_refs": runtime_refs,
            "consumer_policy_ref": copy.deepcopy(policy["policy_artifact_ref"]),
            "consumer_policy_sha256": policy["policy_sha256"],
            "criterion_evaluations": evaluations,
            "crosswalk_rule_id": "exact_signed_policy_recomputed_no_legacy_authority",
            "blockers": blockers,
        }
    )
    VERIFY.validate_schema(decision, DECISION_SCHEMA)
    CORE.validate_authority_decision_record(
        decision,
        certificate,
        trusted_keys,
        policy,
        runtime_verification_context,
        use_time=use_time,
        production_required=production_required,
    )
    return decision


def validate_invalidation_event(
    event: dict[str, Any],
    *,
    production_required: bool = False,
    trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
) -> None:
    VERIFY.validate_schema(event, INVALIDATION_SCHEMA)
    CORE.validate_invalidation_event_record(
        event,
        trusted_keys,
        production_required=production_required,
        runtime_verification_context=runtime_verification_context,
        use_time=use_time,
    )


def apply_invalidation_event(
    state: dict[str, Any],
    event: dict[str, Any],
    *,
    production_required: bool = False,
    trusted_keys: dict[str, Any] | None = None,
    runtime_verification_context: dict[str, Any] | None = None,
    use_time: str | None = None,
) -> dict[str, Any]:
    _exact_object(state, {"schema_version", "record_type", "targets", "tombstones", "unrelated_branch_ids", "applied_event_refs", "runtime_completion_claimed"}, "authority state")
    if state["schema_version"] != "1.0.0" or state["record_type"] != "maskfactory_authority_runtime_state":
        raise ValueError("authority state type or version is unsupported")
    if state["runtime_completion_claimed"]:
        raise ValueError("authority state cannot claim runtime completion")
    validate_invalidation_event(
        event,
        production_required=production_required,
        trusted_keys=trusted_keys,
        runtime_verification_context=runtime_verification_context,
        use_time=use_time,
    )
    event_ref = {
        "record_type": event["record_type"],
        "record_id": event["maskfactory_invalidation_event_v2_id"],
        "revision": event["revision"],
        "sha256": event["invalidation_event_sha256"],
    }
    if event_ref in state["applied_event_refs"]:
        return copy.deepcopy(state)
    updated = copy.deepcopy(state)
    targets = {(item["target_kind"], item["target_id"]): item for item in updated["targets"]}
    if len(targets) != len(updated["targets"]):
        raise ValueError("authority state contains duplicate target identities")
    affected: set[tuple[str, str]] = set()
    for transition in event["target_transitions"]:
        key = (transition["target_kind"], transition["target_id"])
        target = targets.get(key)
        if target is None:
            raise ValueError("invalidation target is absent from Main authority state")
        _exact_object(
            target,
            {"target_kind", "target_id", "target_sha256", "scope_sha256", "authority_state", "certificate_status", "cache_state", "dependent_pass_ids", "branch_id"},
            "authority target",
        )
        if (
            target["target_sha256"] != transition["target_sha256"]
            or target["scope_sha256"] != transition["scope_sha256"]
            or target["authority_state"] != transition["previous_authority_state"]
            or target["certificate_status"] != transition["previous_certificate_status"]
        ):
            raise ValueError("invalidation target hash, scope, authority, or certificate predecessor mismatch")
        if AUTHORITY_RANK[transition["new_authority_state"]] > AUTHORITY_RANK[target["authority_state"]]:
            raise ValueError("invalidation cannot elevate target authority")
        target["authority_state"] = transition["new_authority_state"]
        target["certificate_status"] = transition["new_certificate_status"]
        target["cache_state"] = "tombstoned"
        affected.add(key)
        updated["tombstones"].append(
            {
                "target_kind": target["target_kind"],
                "target_id": target["target_id"],
                "target_sha256": target["target_sha256"],
                "scope_sha256": target["scope_sha256"],
                "event_ref": copy.deepcopy(event_ref),
                "reason": event["reason"],
                "effective_at": event["effective_at"],
            }
        )
    if not affected:
        raise ValueError("invalidation event did not affect any exact target")
    unaffected_before = {
        (item["target_kind"], item["target_id"]): copy.deepcopy(item)
        for item in state["targets"]
        if (item["target_kind"], item["target_id"]) not in affected
    }
    unaffected_after = {
        (item["target_kind"], item["target_id"]): item
        for item in updated["targets"]
        if (item["target_kind"], item["target_id"]) not in affected
    }
    if unaffected_before != unaffected_after:
        raise ValueError("invalidation mutated unrelated targets")
    updated["applied_event_refs"].append(event_ref)
    return updated

