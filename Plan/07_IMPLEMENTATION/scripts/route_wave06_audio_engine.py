#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_AUTHORITY_HASHES = {
    "registry": "9c44937c07289f2e585d537bb8a5873115f781b7da89245d93d2b4770139109a",
    "matrix": "cc5e7fee7bb64ea8854dfab097c0e2d4ab4a6e010b55d5c48bc7bed5f6d81fb2",
    "rules": "a8a624a83c11e9f30fa8186674be8df5a863787033413fc5d47f34a1275dd8b4",
    "notes": "0134d9ed5921db96334904275036bee27a3746e2e031900fd6ddd3bfa277f744",
}

ROUTE_TYPES = {
    "dialogue_voice",
    "breath_body_effort",
    "foley_contact_fabric",
    "ambience_room_tone",
    "music",
    "synchronized_av",
}
OUTPUT_TYPES = {"audio", "av"}
USAGE_SCOPES = {"internal_eval", "client_preview", "production"}
TARGET_OUTPUTS = {"wav", "flac", "aac", "pcm"}
TARGET_CONTAINERS = {"wav", "flac", "mp4", "mov", "mkv"}
CHANNEL_LAYOUTS = {"mono", "stereo", "5.1"}

PROOF_KINDS = ("capability", "license", "asset", "runtime", "qa")

# No current Wave06 authority record defines an approved production-audio status.
APPROVED_AUDIO_PROMOTION_STATUSES: frozenset[str] = frozenset()

PROOF_KEYSETS: dict[str, set[str]] = {
    "capability": {
        "proof_kind",
        "engine_id",
        "constraints_hash",
        "verified_route_types",
        "duration_seconds",
        "sample_rates_hz",
        "channels",
        "channel_layouts",
        "output_targets",
        "container_formats",
    },
    "license": {
        "proof_kind",
        "engine_id",
        "constraints_hash",
        "license_id",
        "license_artifact_path",
        "license_artifact_sha256",
        "allowed_usage_scopes",
    },
    "asset": {
        "proof_kind",
        "engine_id",
        "constraints_hash",
        "asset_bundle_id",
        "asset_bundle_path",
        "asset_bundle_bytes",
        "asset_bundle_sha256",
        "install_state",
        "runtime_state",
    },
    "runtime": {
        "proof_kind",
        "engine_id",
        "constraints_hash",
        "asset_bundle_id",
        "asset_bundle_sha256",
        "tested_duration_seconds",
        "tested_sample_rate_hz",
        "tested_channels",
        "tested_channel_layout",
        "tested_output_target",
        "tested_container",
        "execution_passed",
    },
    "qa": {
        "proof_kind",
        "engine_id",
        "constraints_hash",
        "runtime_proof_sha256",
        "decode_passed",
        "duration_passed",
        "loudness_passed",
        "clipping_passed",
        "sync_passed",
        "route_review_passed",
    },
}


class RouteRequestError(ValueError):
    pass


def _sha256_bytes(payload: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(payload)
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json_strict(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")

    def _reject_constant(value: str) -> None:
        raise ValueError(f"invalid non-finite json token: {value}")

    return json.loads(text, parse_constant=_reject_constant)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".tmp_wave06_audio_router_", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RouteRequestError(message)


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_lower_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _is_strict_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_strict_number(value: Any, *, positive: bool = False, nonnegative: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    numeric = float(value)
    if not math.isfinite(numeric):
        return False
    if positive and numeric <= 0.0:
        return False
    if nonnegative and numeric < 0.0:
        return False
    return True


def _is_unique_typed_list(values: Any, *, element_type: type, non_empty: bool = True) -> bool:
    if not isinstance(values, list):
        return False
    if non_empty and not values:
        return False
    if element_type is int:
        valid = [isinstance(item, int) and not isinstance(item, bool) for item in values]
    elif element_type is float:
        valid = [isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(float(item)) for item in values]
    else:
        valid = [isinstance(item, element_type) for item in values]
    if not all(valid):
        return False
    return len(values) == len(set(values))


def _resolve_root_bound_path(root: Path, raw_path: str, *, label: str) -> Path:
    _require(_is_non_empty_string(raw_path), f"{label}_path_not_non_empty_string")
    root_resolved = root.resolve()
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root_resolved / raw_path).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as error:
        raise RouteRequestError(f"{label}_path_outside_root") from error
    return resolved


def _validate_proof_payload_strict(root: Path, proof_kind: str, proof: dict[str, Any]) -> None:
    if proof_kind == "capability":
        _require(_is_unique_typed_list(proof["verified_route_types"], element_type=str), "malformed_capability_verified_route_types")
        _require(isinstance(proof["duration_seconds"], dict), "malformed_capability_duration_seconds")
        duration_window = proof["duration_seconds"]
        _require(set(duration_window.keys()) == {"min", "max"}, "malformed_capability_duration_seconds")
        _require(_is_strict_number(duration_window["min"], nonnegative=True), "malformed_capability_duration_min")
        _require(_is_strict_number(duration_window["max"], positive=True), "malformed_capability_duration_max")
        _require(float(duration_window["max"]) >= float(duration_window["min"]), "malformed_capability_duration_range")
        _require(_is_unique_typed_list(proof["sample_rates_hz"], element_type=int), "malformed_capability_sample_rates")
        _require(all(rate > 0 for rate in proof["sample_rates_hz"]), "malformed_capability_sample_rates")
        _require(_is_unique_typed_list(proof["channels"], element_type=int), "malformed_capability_channels")
        _require(all(channels > 0 for channels in proof["channels"]), "malformed_capability_channels")
        _require(_is_unique_typed_list(proof["channel_layouts"], element_type=str), "malformed_capability_channel_layouts")
        _require(_is_unique_typed_list(proof["output_targets"], element_type=str), "malformed_capability_output_targets")
        _require(_is_unique_typed_list(proof["container_formats"], element_type=str), "malformed_capability_container_formats")
        return

    if proof_kind == "license":
        _require(_is_non_empty_string(proof["license_id"]), "malformed_license_id")
        _require(_is_non_empty_string(proof["license_artifact_path"]), "malformed_license_artifact_path")
        _require(_is_lower_sha256(proof["license_artifact_sha256"]), "malformed_license_artifact_sha256")
        _require(_is_unique_typed_list(proof["allowed_usage_scopes"], element_type=str), "malformed_allowed_usage_scopes")
        license_artifact_path = _resolve_root_bound_path(
            root,
            proof["license_artifact_path"],
            label="license_artifact",
        )
        if not license_artifact_path.exists():
            raise RouteRequestError("missing_license_artifact")
        if not license_artifact_path.is_file():
            raise RouteRequestError("invalid_license_artifact")
        observed_sha256 = _sha256_file(license_artifact_path)
        if observed_sha256 != proof["license_artifact_sha256"]:
            raise RouteRequestError("license_artifact_sha256_mismatch")
        return

    if proof_kind == "asset":
        _require(_is_non_empty_string(proof["asset_bundle_id"]), "malformed_asset_bundle_id")
        _require(_is_non_empty_string(proof["asset_bundle_path"]), "malformed_asset_bundle_path")
        _require(_is_strict_number(proof["asset_bundle_bytes"], positive=True), "malformed_asset_bundle_bytes")
        _require(isinstance(proof["asset_bundle_bytes"], int) and not isinstance(proof["asset_bundle_bytes"], bool), "malformed_asset_bundle_bytes")
        _require(_is_lower_sha256(proof["asset_bundle_sha256"]), "malformed_asset_bundle_sha256")
        _require(_is_non_empty_string(proof["install_state"]), "malformed_asset_install_state")
        _require(_is_non_empty_string(proof["runtime_state"]), "malformed_asset_runtime_state")
        bundle_path = _resolve_root_bound_path(root, proof["asset_bundle_path"], label="asset_bundle")
        if not bundle_path.exists():
            raise RouteRequestError("missing_asset_bundle_artifact")
        if not bundle_path.is_file():
            raise RouteRequestError("invalid_asset_bundle_artifact")
        observed_bytes = bundle_path.stat().st_size
        if observed_bytes != proof["asset_bundle_bytes"]:
            raise RouteRequestError("asset_bundle_bytes_mismatch")
        observed_sha256 = _sha256_file(bundle_path)
        if observed_sha256 != proof["asset_bundle_sha256"]:
            raise RouteRequestError("asset_bundle_sha256_mismatch")
        return

    if proof_kind == "runtime":
        _require(_is_non_empty_string(proof["asset_bundle_id"]), "malformed_runtime_asset_bundle_id")
        _require(_is_lower_sha256(proof["asset_bundle_sha256"]), "malformed_runtime_asset_bundle_sha256")
        _require(_is_strict_number(proof["tested_duration_seconds"], positive=True), "malformed_runtime_tested_duration_seconds")
        _require(isinstance(proof["tested_sample_rate_hz"], int) and not isinstance(proof["tested_sample_rate_hz"], bool) and proof["tested_sample_rate_hz"] > 0, "malformed_runtime_tested_sample_rate_hz")
        _require(isinstance(proof["tested_channels"], int) and not isinstance(proof["tested_channels"], bool) and proof["tested_channels"] > 0, "malformed_runtime_tested_channels")
        _require(_is_non_empty_string(proof["tested_channel_layout"]), "malformed_runtime_tested_channel_layout")
        _require(_is_non_empty_string(proof["tested_output_target"]), "malformed_runtime_tested_output_target")
        _require(_is_non_empty_string(proof["tested_container"]), "malformed_runtime_tested_container")
        _require(_is_strict_bool(proof["execution_passed"]), "malformed_runtime_execution_passed")
        return

    if proof_kind == "qa":
        _require(_is_lower_sha256(proof["runtime_proof_sha256"]), "malformed_qa_runtime_proof_sha256")
        required_flags = (
            "decode_passed",
            "duration_passed",
            "loudness_passed",
            "clipping_passed",
            "sync_passed",
            "route_review_passed",
        )
        for flag in required_flags:
            _require(_is_strict_bool(proof[flag]), f"malformed_qa_{flag}")
        return

    raise RouteRequestError(f"unknown_proof_kind_{proof_kind}")


def _validate_request_shape(payload: Any) -> dict[str, Any]:
    _require(isinstance(payload, dict), "request must be an object")
    required = {
        "output_type",
        "route_type",
        "duration_seconds",
        "sample_rate_hz",
        "channels",
        "channel_layout",
        "target_output",
        "target_container",
        "usage_scope",
        "physical_action_present",
        "aligned_audio_event_present",
        "is_synthetic",
        "proof_bindings",
    }
    optional = {"preferred_engine_id"}
    keys = set(payload.keys())
    _require(required.issubset(keys), "request missing required keys")
    _require(keys.issubset(required | optional), "request contains unknown keys")

    _require(payload["output_type"] in OUTPUT_TYPES, "output_type must be audio|av")
    _require(payload["route_type"] in ROUTE_TYPES, "unknown route_type taxonomy")
    _require(
        isinstance(payload["duration_seconds"], (int, float))
        and math.isfinite(float(payload["duration_seconds"]))
        and float(payload["duration_seconds"]) > 0.0,
        "duration_seconds must be finite and positive",
    )
    _require(
        isinstance(payload["sample_rate_hz"], int) and payload["sample_rate_hz"] > 0,
        "sample_rate_hz must be a positive integer",
    )
    _require(isinstance(payload["channels"], int) and payload["channels"] > 0, "channels must be a positive integer")
    _require(payload["channel_layout"] in CHANNEL_LAYOUTS, "unsupported channel_layout")
    _require(payload["target_output"] in TARGET_OUTPUTS, "unsupported target_output")
    _require(payload["target_container"] in TARGET_CONTAINERS, "unsupported target_container")
    _require(payload["usage_scope"] in USAGE_SCOPES, "unsupported usage_scope")
    _require(isinstance(payload["physical_action_present"], bool), "physical_action_present must be boolean")
    _require(isinstance(payload["aligned_audio_event_present"], bool), "aligned_audio_event_present must be boolean")
    _require(isinstance(payload["is_synthetic"], bool), "is_synthetic must be boolean")
    if "preferred_engine_id" in payload:
        _require(
            payload["preferred_engine_id"] is None or isinstance(payload["preferred_engine_id"], str),
            "preferred_engine_id must be string|null",
        )

    proof_bindings = payload["proof_bindings"]
    _require(isinstance(proof_bindings, dict), "proof_bindings must be object")
    _require(set(proof_bindings.keys()) == set(PROOF_KINDS), "proof_bindings must contain exact proof kinds")
    for proof_kind in PROOF_KINDS:
        binding = proof_bindings[proof_kind]
        _require(isinstance(binding, dict), f"{proof_kind} binding must be object")
        _require(set(binding.keys()) == {"path", "sha256"}, f"{proof_kind} binding must contain exact keys path,sha256")
        _require(isinstance(binding["path"], str) and binding["path"], f"{proof_kind} binding path must be non-empty string")
        _require(
            isinstance(binding["sha256"], str) and len(binding["sha256"]) == 64 and all(c in "0123456789abcdef" for c in binding["sha256"]),
            f"{proof_kind} binding sha256 must be lowercase hex",
        )
    return payload


def _constraints_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_type": request["output_type"],
        "route_type": request["route_type"],
        "duration_seconds": float(request["duration_seconds"]),
        "sample_rate_hz": request["sample_rate_hz"],
        "channels": request["channels"],
        "channel_layout": request["channel_layout"],
        "target_output": request["target_output"],
        "target_container": request["target_container"],
        "usage_scope": request["usage_scope"],
        "physical_action_present": request["physical_action_present"],
        "aligned_audio_event_present": request["aligned_audio_event_present"],
        "is_synthetic": request["is_synthetic"],
        "preferred_engine_id": request.get("preferred_engine_id"),
    }


def _load_proof(
    *,
    root: Path,
    proof_kind: str,
    binding: dict[str, str],
    expected_engine_id: str,
    constraints_hash: str,
) -> tuple[str, str | None, dict[str, Any] | None, str | None]:
    try:
        proof_path = _resolve_root_bound_path(
            root,
            binding["path"],
            label=f"{proof_kind}_proof",
        )
    except RouteRequestError as error:
        return ("malformed", str(error), None, None)
    if not proof_path.exists():
        return ("missing", f"missing_{proof_kind}_proof", None, None)
    try:
        observed_hash = _sha256_file(proof_path)
    except Exception:
        return ("malformed", f"unreadable_{proof_kind}_proof", None, None)
    if observed_hash != binding["sha256"]:
        return ("hash_mismatch", f"{proof_kind}_proof_hash_mismatch", None, observed_hash)
    try:
        payload = _load_json_strict(proof_path)
    except Exception:
        return ("malformed", f"malformed_{proof_kind}_proof", None, observed_hash)
    if not isinstance(payload, dict):
        return ("malformed", f"malformed_{proof_kind}_proof", None, observed_hash)
    if set(payload.keys()) != PROOF_KEYSETS[proof_kind]:
        return ("unsupported", f"unknown_{proof_kind}_proof_keys", None, observed_hash)
    if payload.get("proof_kind") != proof_kind:
        return ("unsupported", f"{proof_kind}_proof_kind_mismatch", None, observed_hash)
    if payload.get("engine_id") != expected_engine_id:
        return ("unsupported", f"{proof_kind}_proof_engine_mismatch", None, observed_hash)
    if payload.get("constraints_hash") != constraints_hash:
        return ("stale", f"{proof_kind}_proof_constraints_hash_mismatch", None, observed_hash)
    try:
        _validate_proof_payload_strict(root, proof_kind, payload)
    except RouteRequestError as error:
        return ("malformed", str(error), None, observed_hash)
    return ("pass", None, payload, observed_hash)


def _validate_capability_coverage(request: dict[str, Any], proof: dict[str, Any]) -> str | None:
    route_types = proof["verified_route_types"]
    if not isinstance(route_types, list) or request["route_type"] not in route_types:
        return "unsupported_route_type"
    duration = proof["duration_seconds"]
    if not isinstance(duration, dict) or set(duration.keys()) != {"min", "max"}:
        return "unsupported_duration"
    if float(request["duration_seconds"]) < float(duration["min"]) or float(request["duration_seconds"]) > float(duration["max"]):
        return "unsupported_duration"
    if request["sample_rate_hz"] not in proof["sample_rates_hz"]:
        return "unsupported_sample_rate"
    if request["channels"] not in proof["channels"]:
        return "unsupported_channels"
    if request["channel_layout"] not in proof["channel_layouts"]:
        return "unsupported_channel_layout"
    if request["target_output"] not in proof["output_targets"]:
        return "unsupported_output_target"
    if request["target_container"] not in proof["container_formats"]:
        return "unsupported_container_format"
    return None


def _validate_license_coverage(request: dict[str, Any], proof: dict[str, Any]) -> str | None:
    scopes = proof["allowed_usage_scopes"]
    if not isinstance(scopes, list) or request["usage_scope"] not in scopes:
        return "unsupported_usage_scope"
    return None


def _validate_asset_state(proof: dict[str, Any]) -> str | None:
    if proof["install_state"] != "installed":
        return "asset_install_state_mismatch"
    if proof["runtime_state"] != "ready":
        return "asset_runtime_state_mismatch"
    return None


def _validate_runtime_coverage(request: dict[str, Any], runtime_proof: dict[str, Any], asset_proof: dict[str, Any]) -> str | None:
    if runtime_proof["asset_bundle_id"] != asset_proof["asset_bundle_id"]:
        return "runtime_asset_bundle_mismatch"
    if runtime_proof["asset_bundle_sha256"] != asset_proof["asset_bundle_sha256"]:
        return "runtime_asset_bundle_sha256_mismatch"
    if not runtime_proof["execution_passed"]:
        return "runtime_execution_failed"
    if float(runtime_proof["tested_duration_seconds"]) < float(request["duration_seconds"]):
        return "runtime_duration_mismatch"
    if runtime_proof["tested_sample_rate_hz"] != request["sample_rate_hz"]:
        return "runtime_sample_rate_mismatch"
    if runtime_proof["tested_channels"] != request["channels"]:
        return "runtime_channels_mismatch"
    if runtime_proof["tested_channel_layout"] != request["channel_layout"]:
        return "runtime_channel_layout_mismatch"
    if runtime_proof["tested_output_target"] != request["target_output"]:
        return "runtime_output_target_mismatch"
    if runtime_proof["tested_container"] != request["target_container"]:
        return "runtime_container_mismatch"
    return None


def _validate_qa_coverage(qa_proof: dict[str, Any], runtime_sha256: str) -> str | None:
    if qa_proof["runtime_proof_sha256"] != runtime_sha256:
        return "qa_runtime_hash_mismatch"
    required_flags = (
        "decode_passed",
        "duration_passed",
        "loudness_passed",
        "clipping_passed",
        "sync_passed",
        "route_review_passed",
    )
    if not all(qa_proof[key] is True for key in required_flags):
        return "qa_gate_failed"
    return None


def _load_authority(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    authority_paths = {
        "registry": root / "Plan/10_REGISTRIES/wave06_engine_registry.json",
        "matrix": root / "Plan/10_REGISTRIES/wave06_engine_compatibility_matrix.json",
        "rules": root / "Plan/10_REGISTRIES/wave06_engine_router_rules.json",
        "notes": root / "Plan/10_REGISTRIES/wave06_source_flow_engine_notes.json",
    }
    hashes = {key: _sha256_file(path) for key, path in authority_paths.items()}
    payloads = {key: _load_json_strict(path) for key, path in authority_paths.items()}
    return payloads, hashes


def _prefilter_audio_candidates(registry: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> list[str]:
    registered_ids = {entry["engine_id"] for entry in registry if isinstance(entry, dict) and "engine_id" in entry}
    candidates: list[str] = []
    for row in matrix:
        if not isinstance(row, dict):
            continue
        engine_id = row.get("engine_id")
        if not isinstance(engine_id, str):
            continue
        if row.get("route_as_audio") != "yes":
            continue
        if engine_id not in registered_ids:
            continue
        if engine_id not in candidates:
            candidates.append(engine_id)
    return candidates


def route_request(root: Path, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    authority_payloads, authority_hashes = _load_authority(root)
    blockers: list[str] = []
    required_next_proofs: list[str] = []

    for key, expected in EXPECTED_AUTHORITY_HASHES.items():
        if authority_hashes[key] != expected:
            blockers.append(f"authority_hash_mismatch_{key}")

    constraints = _constraints_payload(request)
    constraints_hash = _sha256_bytes(_canonical_json(constraints).encode("utf-8"))

    registry = authority_payloads["registry"]
    matrix = authority_payloads["matrix"]
    _require(isinstance(registry, list), "registry must be a list")
    _require(isinstance(matrix, list), "matrix must be a list")
    candidates = _prefilter_audio_candidates(registry, matrix)

    registry_by_engine = {entry.get("engine_id"): entry for entry in registry if isinstance(entry, dict) and isinstance(entry.get("engine_id"), str)}
    matrix_by_engine = {entry.get("engine_id"): entry for entry in matrix if isinstance(entry, dict) and isinstance(entry.get("engine_id"), str)}

    preferred_engine = request.get("preferred_engine_id")
    if preferred_engine is not None and preferred_engine not in candidates:
        blockers.append("preferred_engine_not_audio_capable")

    selected_candidate = None
    if preferred_engine is not None and preferred_engine in candidates:
        selected_candidate = preferred_engine
    elif candidates:
        selected_candidate = candidates[0]

    if selected_candidate is not None:
        registry_row = registry_by_engine.get(selected_candidate, {})
        matrix_row = matrix_by_engine.get(selected_candidate, {})
        registry_status = registry_row.get("promotion_status")
        matrix_status = matrix_row.get("promotion_status")
        if (
            registry_status not in APPROVED_AUDIO_PROMOTION_STATUSES
            or matrix_status not in APPROVED_AUDIO_PROMOTION_STATUSES
        ):
            blockers.append("engine_promotion_status_not_approved")
        blocked_until = matrix_row.get("blocked_until")
        if blocked_until == "runtime proof":
            # Runtime proof satisfies blocked_until only when it passes strict validation.
            runtime_binding = request["proof_bindings"]["runtime"]
            runtime_result = _load_proof(
                root=root,
                proof_kind="runtime",
                binding=runtime_binding,
                expected_engine_id=selected_candidate,
                constraints_hash=constraints_hash,
            )
            if runtime_result[0] != "pass":
                blockers.append("engine_blocked_until_runtime_proof")

    proof_results: dict[str, tuple[str, str | None, dict[str, Any] | None, str | None]] = {}
    if selected_candidate is not None:
        for proof_kind in PROOF_KINDS:
            proof_results[proof_kind] = _load_proof(
                root=root,
                proof_kind=proof_kind,
                binding=request["proof_bindings"][proof_kind],
                expected_engine_id=selected_candidate,
                constraints_hash=constraints_hash,
            )
            result = proof_results[proof_kind]
            if result[1]:
                blockers.append(result[1])
                if proof_kind not in required_next_proofs:
                    required_next_proofs.append(proof_kind)
    else:
        for proof_kind in PROOF_KINDS:
            proof_results[proof_kind] = ("missing", f"missing_{proof_kind}_proof", None, None)
            if proof_kind not in required_next_proofs:
                required_next_proofs.append(proof_kind)
            blockers.append(f"missing_{proof_kind}_proof")

    if selected_candidate is not None and all(proof_results[p][0] == "pass" for p in PROOF_KINDS):
        capability = proof_results["capability"][2]
        license_proof = proof_results["license"][2]
        asset = proof_results["asset"][2]
        runtime = proof_results["runtime"][2]
        qa = proof_results["qa"][2]
        assert capability is not None and license_proof is not None and asset is not None and runtime is not None and qa is not None

        capability_block = _validate_capability_coverage(request, capability)
        if capability_block:
            blockers.append(capability_block)
            required_next_proofs.append("capability")

        license_block = _validate_license_coverage(request, license_proof)
        if license_block:
            blockers.append(license_block)
            required_next_proofs.append("license")

        asset_block = _validate_asset_state(asset)
        if asset_block:
            blockers.append(asset_block)
            required_next_proofs.append("asset")

        runtime_block = _validate_runtime_coverage(request, runtime, asset)
        if runtime_block:
            blockers.append(runtime_block)
            required_next_proofs.append("runtime")

        runtime_sha = proof_results["runtime"][3] or ""
        qa_block = _validate_qa_coverage(qa, runtime_sha)
        if qa_block:
            blockers.append(qa_block)
            required_next_proofs.append("qa")

    if request["physical_action_present"] and not request["aligned_audio_event_present"]:
        blockers.append("missing_aligned_audio_event")

    route_mode = "audio_engine_selected"
    selected_engine_id = selected_candidate
    block_final_av_promotion = False
    exit_code = 0

    if request["is_synthetic"]:
        blockers.append("synthetic_input_no_engine_selection")
        required_next_proofs = list(PROOF_KINDS)
        route_mode = "manifest_only" if request["output_type"] == "audio" else "silent_video_plus_audio_plan_manifest"
        selected_engine_id = None
        block_final_av_promotion = True
        exit_code = 2
    elif blockers:
        route_mode = "manifest_only" if request["output_type"] == "audio" else "silent_video_plus_audio_plan_manifest"
        selected_engine_id = None
        block_final_av_promotion = True
        exit_code = 2

    required_next_proofs = sorted(set(required_next_proofs))
    normalized_blockers = sorted(set(blockers))

    proof_eval = {}
    for proof_kind, result in proof_results.items():
        if request["is_synthetic"]:
            proof_eval[proof_kind] = "synthetic_blocked"
        else:
            proof_eval[proof_kind] = result[0]

    decision = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "decision_version": 1,
        "output_type": request["output_type"],
        "route_type": request["route_type"],
        "request_constraints_hash": constraints_hash,
        "selected_engine_id": selected_engine_id,
        "route_mode": route_mode,
        "block_final_av_promotion": block_final_av_promotion,
        "is_synthetic": request["is_synthetic"],
        "blockers": normalized_blockers,
        "required_next_proofs": required_next_proofs,
        "evaluated_candidates": candidates,
        "authority_bindings": {
            "registry_sha256": authority_hashes["registry"],
            "matrix_sha256": authority_hashes["matrix"],
            "rules_sha256": authority_hashes["rules"],
            "notes_sha256": authority_hashes["notes"],
        },
        "proof_evaluation": proof_eval,
    }
    return exit_code, decision


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route Wave06 audio engine requests with strict proof validation.")
    parser.add_argument("--root", required=True, help="Repository root path")
    parser.add_argument("--request", required=True, help="Path to request JSON file")
    parser.add_argument("--output", required=True, help="Path to decision JSON output file")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    root = Path(args.root).resolve()
    request_path = Path(args.request).resolve()
    output_path = Path(args.output).resolve()

    try:
        request_payload = _validate_request_shape(_load_json_strict(request_path))
    except (RouteRequestError, ValueError) as error:
        print(f"ERROR: invalid request: {error}")
        return 1

    try:
        code, decision = route_request(root, request_payload)
    except (RouteRequestError, ValueError, OSError) as error:
        print(f"ERROR: routing failure: {error}")
        return 1

    _write_json_atomic(output_path, decision)
    print(json.dumps({"status": "ok" if code == 0 else "blocked", "exit_code": code, "output": str(output_path)}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
