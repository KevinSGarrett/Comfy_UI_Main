from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
VERIFIER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/verify_wave64_maskfactory_release_adoption.py"
POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_maskfactory_bridge_arbitration_cache_recovery_policy_v2.json"
RESULT_SCHEMA = "maskfactory_bridge_result_v2.schema.json"
HEALTH_SCHEMA = "maskfactory_health_capability_snapshot_v2.schema.json"
AUTHORITY_RANK = {
    "invalid": 0,
    "hypothesis": 1,
    "draft": 2,
    "qa_passed_noncertified": 3,
    "certified": 4,
}


def _load_verifier():
    spec = importlib.util.spec_from_file_location("wave64_maskfactory_release_verifier_for_adapter", VERIFIER_PATH)
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


def _exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if set(value) != fields:
        raise ValueError(f"{label} closed fields differ: missing={sorted(fields - set(value))} unknown={sorted(set(value) - fields)}")
    return value


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("package artifact path is unsafe")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("package artifact path is unsafe")
    return relative


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an offset")
    return parsed


def _request_ref(request: dict[str, Any]) -> dict[str, str]:
    return {
        "record_type": request["record_type"],
        "record_id": request["maskfactory_bridge_request_v2_id"],
        "revision": request["revision"],
        "sha256": sha256_bytes(canonical_json(request)),
    }


def _fixture_trust(*, signer_role: str) -> dict[str, Any]:
    return CORE.fixture_signing_trust(trusted=False, signer_role=signer_role)


def _validate_fixture_boundary(request: dict[str, Any], *, allow_fixture: bool) -> None:
    VERIFY.validate_schema(request, "maskfactory_bridge_request_v2.schema.json")
    CORE.validate_request_ownership(request)
    if not request["fixture_only"]:
        raise ValueError("production adapter execution requires an adopted producer release and is not enabled by this fixture batch")
    if not allow_fixture:
        raise ValueError("fixture adapter execution requires explicit allow_fixture")
    if request["production_promotion_requested"]:
        raise ValueError("fixture execution cannot request production promotion")


def _validate_package_manifest(request: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    _exact_object(
        manifest,
        {
            "schema_version", "record_type", "package_id", "revision", "created_at", "fixture_only",
            "release_snapshot_ref", "route_id", "execution_stack_ref", "source_artifact", "media_scope",
            "owner_bindings", "transform_chain", "ontology_labels", "artifacts",
        },
        "Mode A package manifest",
    )
    if manifest["schema_version"] != "1.0.0" or manifest["record_type"] != "maskfactory_mode_a_package_manifest":
        raise ValueError("Mode A package manifest version or type is unsupported")
    if manifest["fixture_only"] is not True:
        raise ValueError("fixture adapter accepts only an explicitly fixture-only Mode A package")
    for field in ("release_snapshot_ref", "source_artifact", "media_scope", "owner_bindings", "transform_chain"):
        if manifest[field] != request[field]:
            raise ValueError(f"Mode A package {field} binding differs from the request")
    requested_labels = sorted(intent["label"] for intent in request["mask_intents"])
    if sorted(manifest["ontology_labels"]) != requested_labels:
        raise ValueError("Mode A package ontology labels do not exactly match request intents")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list) or sorted(item.get("label") for item in artifacts) != requested_labels:
        raise ValueError("Mode A package must contain exactly one artifact for every requested label")
    return artifacts


def _resolve_package_artifacts(package_root: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root = package_root.resolve()
    resolved: list[dict[str, Any]] = []
    for artifact in artifacts:
        _exact_object(
            artifact,
            {
                "label", "mask_type", "mask_ref", "path", "sha256", "bytes", "width", "height",
                "coordinate_space", "owner", "authority", "certificate_ref", "qa_record_refs",
            },
            "Mode A artifact",
        )
        relative = _safe_relative_path(artifact["path"])
        path = root.joinpath(*relative.parts).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("Mode A package artifact escapes package root") from exc
        if not path.is_file():
            raise ValueError(f"Mode A package artifact is missing: {relative.as_posix()}")
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        if digest != artifact["sha256"] or len(raw) != artifact["bytes"] or artifact["mask_ref"]["sha256"] != digest:
            raise ValueError(f"Mode A package artifact hash/size/ref mismatch: {relative.as_posix()}")
        authority = artifact["authority"]
        if authority["authority_state"] == "certified" or artifact["certificate_ref"] is not None:
            raise ValueError("fixture Mode A package cannot assert certified authority")
        if authority["certificate_ref"] is not None or authority["certificate_scope"]:
            raise ValueError("uncertified Mode A artifact cannot carry certificate scope")
        resolved.append(copy.deepcopy(artifact))
    return resolved


def _observation(request: dict[str, Any], *, route_id: str, output_bytes: int) -> dict[str, Any]:
    created = request["created_at"]
    if _timestamp(created) > _timestamp(request["deadline_at"]):
        raise ValueError("request was created after its deadline")
    return {
        "execution_scope": copy.deepcopy(request["scope"]),
        "attempt_number": request["attempt_number"],
        "hypothesis": copy.deepcopy(request["hypothesis"]),
        "admitted_at": created,
        "queue_started_at": created,
        "execution_started_at": created,
        "completed_at": created,
        "queue_ms": 0,
        "runtime_ms": 0,
        "peak_vram_mb": 0,
        "peak_ram_mb": 1,
        "output_bytes": output_bytes,
        "deadline_met": True,
        "resource_envelope_met": True,
        "selected_route_id": route_id,
        "selection_reason_code": "exact_fixture_route",
        "eligible_alternative_route_ids": [],
        "route_selection_evidence_refs": [CORE.ref("route_selection_evidence", f"{route_id}_selection", "6")],
        "factual_not_promotion_authority": True,
    }


def _minimum_authority(masks: list[dict[str, Any]]) -> dict[str, Any]:
    if not masks:
        return CORE.fixture_authority(state="invalid")
    return copy.deepcopy(min((mask["authority"] for mask in masks), key=lambda value: AUTHORITY_RANK[value["authority_state"]]))


def _normalize_result(
    request: dict[str, Any],
    *,
    access_mode: str,
    release_snapshot_ref: dict[str, Any],
    route_id: str,
    execution_stack_ref: dict[str, Any],
    raw_receipt_id: str,
    raw_receipt_payload_sha256: str,
    artifacts: list[dict[str, Any]],
    output_bytes: int,
    cache_state: str,
) -> dict[str, Any]:
    masks = []
    qa_refs: list[dict[str, Any]] = []
    for artifact in artifacts:
        authority = copy.deepcopy(artifact["authority"])
        if AUTHORITY_RANK[authority["authority_state"]] > AUTHORITY_RANK["draft"]:
            raise ValueError("fixture normalization cannot elevate output above draft authority")
        masks.append(
            {
                "mask_ref": copy.deepcopy(artifact["mask_ref"]),
                "mask_sha256": artifact["sha256"],
                "label": artifact["label"],
                "mask_type": artifact["mask_type"],
                "coordinate_space": artifact["coordinate_space"],
                "width": artifact["width"],
                "height": artifact["height"],
                "owner": copy.deepcopy(artifact["owner"]),
                "authority": authority,
                "lineage_kind": "original",
                "parents": [],
                "derivation_operation": "none",
            }
        )
        qa_refs.extend(copy.deepcopy(artifact["qa_record_refs"]))
    input_hashes = {
        region["region_sha256"]
        for region in request["target_region_bindings"] + request["protected_region_bindings"]
    }
    collisions = input_hashes.intersection(mask["mask_sha256"] for mask in masks)
    mode_a_exception = bool(collisions) and access_mode == "mode_a_package_read" and all(
        region["selector_kind"] == "mode_a_exact_package_artifact"
        for region in request["target_region_bindings"] + request["protected_region_bindings"]
        if region["region_sha256"] in collisions
    )
    result = copy.deepcopy(CORE.build_examples()["maskfactory_bridge_result_v2.example.json"])
    result.update(
        {
            "maskfactory_bridge_result_v2_id": f"mfb_result_{sha256_bytes(canonical_json([_request_ref(request), raw_receipt_payload_sha256]))[:24]}",
            "created_at": request["created_at"],
            "fixture_only": True,
            "request_ref": _request_ref(request),
            "release_snapshot_ref": copy.deepcopy(release_snapshot_ref),
            "access_mode": access_mode,
            "raw_producer_receipt_ref": CORE.ref("mask_acquisition_receipt", raw_receipt_id, raw_receipt_payload_sha256[0]),
            "raw_producer_receipt_payload_sha256": raw_receipt_payload_sha256,
            "raw_producer_receipt_signature": "fixture-receipt-attestation-not-runtime-authority",
            "raw_producer_receipt_signature_trust": _fixture_trust(signer_role="maskfactory_receipt_signer"),
            "normalization_signature": "fixture-normalization-attestation-not-runtime-authority",
            "normalization_signature_trust": _fixture_trust(signer_role="main_normalization_signer"),
            "status": "succeeded",
            "source_artifact": copy.deepcopy(request["source_artifact"]),
            "media_scope": copy.deepcopy(request["media_scope"]),
            "route_id": route_id,
            "execution_stack_ref": copy.deepcopy(execution_stack_ref),
            "owner_bindings": copy.deepcopy(request["owner_bindings"]),
            "transform_chain": copy.deepcopy(request["transform_chain"]),
            "input_region_lineage": {
                "target_region_refs": [copy.deepcopy(region["region_ref"]) for region in request["target_region_bindings"]],
                "protected_region_refs": [copy.deepcopy(region["region_ref"]) for region in request["protected_region_bindings"]],
                "request_transform_chain_sha256": request["transform_chain"]["chain_sha256"],
                "input_roi_hashes_are_output_artifact_hashes": bool(collisions),
                "mode_a_exact_selector_exception_applied": mode_a_exception,
            },
            "execution_observation": _observation(request, route_id=route_id, output_bytes=output_bytes),
            "roundtrip_max_error_pixels": 0.0,
            "authority": _minimum_authority(masks),
            "operational_certificate_ref": None,
            "masks": masks,
            "qa_record_refs": qa_refs,
            "blockers": [],
            "cache_state": cache_state,
        }
    )
    result["raw_producer_receipt_ref"]["sha256"] = raw_receipt_payload_sha256
    CORE.seal_normalized_result(result)
    VERIFY.validate_schema(result, RESULT_SCHEMA)
    CORE.validate_request_result_pair(request, result)
    CORE.validate_result_certificate_pair(result, None, production_required=False)
    return result


def execute_mode_a_fixture(
    request: dict[str, Any], manifest: dict[str, Any], package_root: Path, *, allow_fixture: bool = False
) -> dict[str, Any]:
    _validate_fixture_boundary(request, allow_fixture=allow_fixture)
    if request["access_mode"] != "mode_a_package_read":
        raise ValueError("Mode A adapter requires mode_a_package_read")
    artifacts = _resolve_package_artifacts(package_root, _validate_package_manifest(request, manifest))
    manifest_sha256 = sha256_bytes(canonical_json(manifest))
    return _normalize_result(
        request,
        access_mode="mode_a_package_read",
        release_snapshot_ref=manifest["release_snapshot_ref"],
        route_id=manifest["route_id"],
        execution_stack_ref=manifest["execution_stack_ref"],
        raw_receipt_id=manifest["package_id"],
        raw_receipt_payload_sha256=manifest_sha256,
        artifacts=artifacts,
        output_bytes=sum(item["bytes"] for item in artifacts),
        cache_state="bypassed",
    )


def validate_health_for_request(request: dict[str, Any], health: dict[str, Any]) -> dict[str, Any]:
    VERIFY.validate_schema(health, HEALTH_SCHEMA)
    if not health["fixture_only"] or health["service_status"] != "healthy":
        raise ValueError("fixture Mode B service health is not healthy")
    if health["release_snapshot_ref"] != request["release_snapshot_ref"]:
        raise ValueError("health snapshot is bound to a different release")
    if not (_timestamp(health["observed_at"]) <= _timestamp(request["created_at"]) <= _timestamp(health["expires_at"])):
        raise ValueError("health snapshot is stale for request admission")
    requested_labels = {intent["label"] for intent in request["mask_intents"]}
    routes = [
        route for route in health["routes"]
        if route["access_mode"] == request["access_mode"] and route["status"] == "available" and requested_labels <= set(route["supported_labels"])
    ]
    if len(routes) != 1:
        raise ValueError("health snapshot does not identify one exact eligible Mode B route")
    route = routes[0]
    if route["default_authority_state"] != "draft" or health["current_mode_b_default_authority_state"] != "draft":
        raise ValueError("Mode B default authority must remain draft")
    return route


def _lifecycle_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))["execution_lifecycle"]


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    lock_fd: int | None = None
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with temp.open("xb") as output:
            output.write(canonical_json(value))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    except FileExistsError as exc:
        raise ValueError("lifecycle state is locked by another adapter operation") from exc
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        if lock_fd is not None:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass


def load_lifecycle(path: Path, request: dict[str, Any]) -> dict[str, Any]:
    request_sha256 = sha256_bytes(canonical_json(request))
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        _exact_object(
            state,
            {"schema_version", "record_type", "request_payload_sha256", "idempotency_key", "state", "transitions", "resubmission_authorization_ref", "resubmission_authorization_consumed"},
            "lifecycle state",
        )
        if state["request_payload_sha256"] != request_sha256 or state["idempotency_key"] != request["idempotency_key"]:
            raise ValueError("lifecycle state is bound to a different request or idempotency key")
        return state
    return {
        "schema_version": "1.0.0",
        "record_type": "maskfactory_bridge_adapter_lifecycle_state",
        "request_payload_sha256": request_sha256,
        "idempotency_key": request["idempotency_key"],
        "state": "compiled",
        "transitions": [],
        "resubmission_authorization_ref": None,
        "resubmission_authorization_consumed": False,
    }


def advance_lifecycle(path: Path, request: dict[str, Any], to_state: str, *, evidence_ref: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_lifecycle(path, request)
    pair = [state["state"], to_state]
    if pair not in _lifecycle_policy()["allowed_transitions"]:
        raise ValueError(f"unregistered lifecycle transition: {pair[0]} -> {pair[1]}")
    if state["state"] == "outcome_unknown" and to_state == "reconciled_not_found":
        if evidence_ref is None or set(evidence_ref) != {"record_type", "record_id", "revision", "sha256"}:
            raise ValueError("safe resubmission requires exact signed not-found evidence")
        state["resubmission_authorization_ref"] = copy.deepcopy(evidence_ref)
        state["resubmission_authorization_consumed"] = False
    elif state["state"] == "reconciled_not_found" and to_state == "submitted":
        if evidence_ref != state["resubmission_authorization_ref"] or state["resubmission_authorization_consumed"]:
            raise ValueError("resubmission must consume the exact one-use not-found authorization")
        state["resubmission_authorization_consumed"] = True
    elif evidence_ref is not None:
        raise ValueError("lifecycle evidence is not permitted for this transition")
    state["transitions"].append({"from_state": state["state"], "to_state": to_state, "evidence_ref": copy.deepcopy(evidence_ref)})
    state["state"] = to_state
    _write_atomic(path, state)
    return state


def _validate_fixture_not_found_evidence(request: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    _exact_object(
        evidence,
        {
            "schema_version", "record_type", "fixture_only", "request_payload_sha256", "idempotency_key",
            "outcome", "remote_status", "resubmission_authorized", "evidence_ref", "signature_trust",
        },
        "not-found reconciliation evidence",
    )
    if evidence["schema_version"] != "1.0.0" or evidence["record_type"] != "maskfactory_fixture_not_found_reconciliation_evidence":
        raise ValueError("not-found reconciliation evidence type or version is unsupported")
    if evidence["fixture_only"] is not True:
        raise ValueError("fixture reconciliation cannot accept production evidence")
    if evidence["request_payload_sha256"] != sha256_bytes(canonical_json(request)) or evidence["idempotency_key"] != request["idempotency_key"]:
        raise ValueError("not-found reconciliation evidence is bound to a different request or idempotency key")
    if evidence["outcome"] != "not_found_safe_to_submit" or evidence["remote_status"] != "not_found" or evidence["resubmission_authorized"] is not True:
        raise ValueError("reconciliation evidence does not authorize exact safe resubmission")
    trust = evidence["signature_trust"]
    if (
        trust.get("signature_verified") is not True
        or trust.get("signer_role") != "maskfactory_reconciliation_signer"
        or trust.get("trust_result") != "fixture_only_untrusted"
    ):
        raise ValueError("fixture reconciliation evidence lacks its explicit non-production signature verification")
    ref = evidence["evidence_ref"]
    if set(ref) != {"record_type", "record_id", "revision", "sha256"}:
        raise ValueError("reconciliation evidence ref is not immutable")
    return ref


def execute_mode_b_fixture(
    request: dict[str, Any],
    health: dict[str, Any],
    artifacts: list[dict[str, Any]],
    lifecycle_path: Path,
    *,
    transport_outcome: str = "success",
    allow_fixture: bool = False,
) -> dict[str, Any]:
    _validate_fixture_boundary(request, allow_fixture=allow_fixture)
    if request["access_mode"] not in {"mode_b_live_predict", "mode_b_live_refine"}:
        raise ValueError("Mode B adapter requires predict or refine access mode")
    route = validate_health_for_request(request, health)
    state = load_lifecycle(lifecycle_path, request)
    if state["state"] != "compiled":
        raise ValueError("existing lifecycle must be reconciled or completed before another submission")
    for next_state in ("admitted", "submitted", "accepted", "running"):
        state = advance_lifecycle(lifecycle_path, request, next_state)
    if transport_outcome == "ambiguous":
        state = advance_lifecycle(lifecycle_path, request, "outcome_unknown")
        return {
            "schema_version": "1.0.0",
            "record_type": "maskfactory_bridge_adapter_outcome",
            "status": "outcome_unknown",
            "request_ref": _request_ref(request),
            "idempotency_key": request["idempotency_key"],
            "lifecycle_state": state,
            "resubmission_allowed": False,
            "required_action": "reconcile_exact_remote_outcome_before_resubmission",
            "runtime_completion_claimed": False,
        }
    if transport_outcome != "success":
        raise ValueError("unsupported synthetic transport outcome")
    state = advance_lifecycle(lifecycle_path, request, "succeeded")
    receipt_payload = {
        "request_ref": _request_ref(request),
        "idempotency_key": request["idempotency_key"],
        "route_id": route["route_id"],
        "state": state["state"],
        "artifact_refs": [copy.deepcopy(item["mask_ref"]) for item in artifacts],
    }
    receipt_sha256 = sha256_bytes(canonical_json(receipt_payload))
    normalized = _normalize_result(
        request,
        access_mode=request["access_mode"],
        release_snapshot_ref=health["release_snapshot_ref"],
        route_id=route["route_id"],
        execution_stack_ref=route["execution_stack_ref"],
        raw_receipt_id=f"fixture_receipt_{receipt_sha256[:20]}",
        raw_receipt_payload_sha256=receipt_sha256,
        artifacts=artifacts,
        output_bytes=sum(item["bytes"] for item in artifacts),
        cache_state="fresh_written",
    )
    return {"status": "succeeded", "result": normalized, "lifecycle_state": state}


def reconcile_not_found_for_resubmission(
    lifecycle_path: Path, request: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, Any]:
    evidence_ref = _validate_fixture_not_found_evidence(request, evidence)
    state = advance_lifecycle(lifecycle_path, request, "reconciled_not_found", evidence_ref=evidence_ref)
    return advance_lifecycle(lifecycle_path, request, "submitted", evidence_ref=state["resubmission_authorization_ref"])


def arbitrate_results(
    candidates: list[tuple[dict[str, Any], dict[str, Any] | None]], *, branch_budget: int = 0
) -> dict[str, Any]:
    if not candidates:
        return {"decision": "abstain", "reason": "no_candidates", "selected_result_ref": None, "branch_result_refs": []}
    scope_key = None
    ranked: list[tuple[int, dict[str, Any]]] = []
    for result, certificate in candidates:
        VERIFY.validate_schema(result, RESULT_SCHEMA)
        CORE.validate_result_certificate_pair(result, certificate, production_required=False)
        candidate_scope = canonical_json(
            {
                "source_artifact": result["source_artifact"],
                "media_scope": result["media_scope"],
                "owner_bindings": result["owner_bindings"],
                "transform_chain": result["transform_chain"],
                "labels": sorted(mask["label"] for mask in result["masks"]),
            }
        )
        if scope_key is None:
            scope_key = candidate_scope
        elif candidate_scope != scope_key:
            return {"decision": "abstain", "reason": "scope_ambiguity", "selected_result_ref": None, "branch_result_refs": []}
        ranked.append((AUTHORITY_RANK[result["authority"]["authority_state"]], result))
    best_rank = max(rank for rank, _ in ranked)
    best = [result for rank, result in ranked if rank == best_rank]
    refs = [
        {
            "record_type": result["record_type"],
            "record_id": result["maskfactory_bridge_result_v2_id"],
            "revision": result["revision"],
            "sha256": result["normalization_payload_sha256"],
        }
        for result in best
    ]
    if len(best) == 1:
        return {"decision": "selected", "reason": "strongest_valid_authority", "selected_result_ref": refs[0], "branch_result_refs": []}
    if branch_budget > 0 and len(best) <= branch_budget:
        return {"decision": "branch_for_bounded_qa", "reason": "equal_authority_close_candidates", "selected_result_ref": None, "branch_result_refs": refs}
    return {"decision": "abstain", "reason": "equal_authority_ambiguity", "selected_result_ref": None, "branch_result_refs": []}
