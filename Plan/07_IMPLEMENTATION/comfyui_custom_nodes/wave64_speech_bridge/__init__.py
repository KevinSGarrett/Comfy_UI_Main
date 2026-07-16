"""Dependency-light, fail-closed Wave64 speech orchestration bridge for ComfyUI."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
AUTHORITY_FIELDS = (
    "voice_authority_valid",
    "engine_runtime_valid",
    "asset_license_valid",
    "exact_assets_resolved",
    "production_authorized",
)


class SpeechBridgeError(ValueError):
    pass


def project_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "Plan").is_dir() and (ancestor / "runtime_artifacts").is_dir():
            return ancestor
    raise SpeechBridgeError("C:/Comfy_UI_Main project root is not discoverable")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise SpeechBridgeError(f"INVALID_BRIDGE_REQUEST:{field}:expected_lowercase_sha256")
    return value


def validate_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:root_must_be_object")
    required = {
        "schema_version", "request_id", "engine", "line_contract_sha256", "reference_bindings",
        "seed", "sampling_params", "preprocessing_transform_ids", "authority", "dry_run",
    }
    if set(value) != required:
        raise SpeechBridgeError(f"INVALID_BRIDGE_REQUEST:root_keys:{sorted(set(value) ^ required)}")
    if value["schema_version"] != "1.0":
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:schema_version")
    if not isinstance(value["request_id"], str) or not REQUEST_ID_RE.fullmatch(value["request_id"]):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:request_id")
    engine = value["engine"]
    if not isinstance(engine, dict) or set(engine) != {"family", "revision_sha256", "model_asset_sha256"}:
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:engine")
    if not isinstance(engine["family"], str) or not engine["family"].strip():
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:engine.family")
    _require_sha256(engine["revision_sha256"], "engine.revision_sha256")
    assets = engine["model_asset_sha256"]
    if not isinstance(assets, list) or not assets or len(set(assets)) != len(assets):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:engine.model_asset_sha256")
    for index, item in enumerate(assets):
        _require_sha256(item, f"engine.model_asset_sha256[{index}]")
    _require_sha256(value["line_contract_sha256"], "line_contract_sha256")
    references = value["reference_bindings"]
    if not isinstance(references, list) or not references:
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:reference_bindings")
    for index, reference in enumerate(references):
        if not isinstance(reference, dict) or set(reference) != {"sha256", "rights_valid", "provenance_valid"}:
            raise SpeechBridgeError(f"INVALID_BRIDGE_REQUEST:reference_bindings[{index}]")
        _require_sha256(reference["sha256"], f"reference_bindings[{index}].sha256")
        if not isinstance(reference["rights_valid"], bool) or not isinstance(reference["provenance_valid"], bool):
            raise SpeechBridgeError(f"INVALID_BRIDGE_REQUEST:reference_bindings[{index}].authority")
    if not isinstance(value["seed"], int) or isinstance(value["seed"], bool) or not 0 <= value["seed"] <= 2**64 - 1:
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:seed")
    if not isinstance(value["sampling_params"], dict):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:sampling_params")
    transforms = value["preprocessing_transform_ids"]
    if not isinstance(transforms, list) or any(not isinstance(item, str) or not item for item in transforms):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:preprocessing_transform_ids")
    if len(set(transforms)) != len(transforms):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:duplicate_preprocessing_transform_ids")
    authority = value["authority"]
    if not isinstance(authority, dict) or set(authority) != set(AUTHORITY_FIELDS):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:authority")
    if any(not isinstance(authority[field], bool) for field in AUTHORITY_FIELDS):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:authority_boolean")
    if not isinstance(value["dry_run"], bool):
        raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:dry_run")
    return value


def cache_key_payload(request: dict[str, Any]) -> dict[str, Any]:
    request = validate_request(request)
    return {
        "engine_family": request["engine"]["family"],
        "engine_revision_hash": request["engine"]["revision_sha256"],
        "model_asset_hashes": sorted(request["engine"]["model_asset_sha256"]),
        "line_contract_hash": request["line_contract_sha256"],
        "reference_hashes": sorted(item["sha256"] for item in request["reference_bindings"]),
        "seed": request["seed"],
        "sampling_params": request["sampling_params"],
        "preprocessing_transform_ids": sorted(request["preprocessing_transform_ids"]),
    }


def compute_cache_key(request: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(cache_key_payload(request)).encode("utf-8"))


def authority_blockers(request: dict[str, Any]) -> list[str]:
    request = validate_request(request)
    authority = request["authority"]
    blockers: list[str] = []
    if not authority["voice_authority_valid"]:
        blockers.append("BLOCKED_VOICE_AUTHORITY_MISSING")
    if any(not item["rights_valid"] or not item["provenance_valid"] for item in request["reference_bindings"]):
        blockers.append("BLOCKED_REFERENCE_RIGHTS_OR_PROVENANCE")
    if not authority["engine_runtime_valid"]:
        blockers.append("BLOCKED_ENGINE_MODEL_OR_RUNTIME_MISSING")
    if not authority["asset_license_valid"]:
        blockers.append("BLOCKED_ASSET_LICENSE_OR_GATED_ACCESS")
    if not authority["exact_assets_resolved"]:
        blockers.append("BLOCKED_ASSET_EXACT_SOURCE_OR_HASH_UNRESOLVED")
    if not authority["production_authorized"]:
        blockers.append("BLOCKED_PRODUCTION_CERTIFICATION_INCOMPLETE")
    return blockers


def write_json_atomic(path: Path, value: dict[str, Any], *, immutable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if path.is_file():
        if path.read_text(encoding="utf-8") == content:
            return
        if immutable:
            raise SpeechBridgeError(f"IMMUTABLE_BRIDGE_RESULT_CONFLICT:{path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def cache_lock(cache_root: Path, cache_key: str) -> Iterator[Path]:
    lock = cache_root / "locks" / f"{cache_key}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SpeechBridgeError(f"SPEECH_BRIDGE_CACHE_KEY_LOCKED:{cache_key}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield lock
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def execute_request(request: dict[str, Any], *, dry_run: bool, root: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    request = validate_request(request)
    if dry_run is not True or request["dry_run"] is not True:
        raise SpeechBridgeError("BRIDGE_VERSION_1_REQUIRES_DRY_RUN_NO_ENGINE_DISPATCH")
    root = Path(root or project_root()).resolve()
    cache_root = root / "runtime_artifacts/audio_speech_cache"
    key = compute_cache_key(request)
    blockers = authority_blockers(request)
    with cache_lock(cache_root, key):
        result = {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "status": "BLOCKED" if blockers else "PASS",
            "classification": (
                "W64_SPEECH_BRIDGE_DRY_RUN_VALIDATED_AUTHORITY_BLOCKED"
                if blockers else "W64_SPEECH_BRIDGE_DRY_RUN_PASS_NO_DISPATCH"
            ),
            "cache_key": key,
            "cache_key_payload": cache_key_payload(request),
            "blockers": blockers,
            "state_history": [
                "REQUESTED", "SCHEMA_VALIDATED", "CACHE_KEY_COMPUTED", "AUTHORITY_CHECKED",
                "ROUTED_TO_DRY_RUN_NO_ENGINE_DISPATCH", "RESULT_HASH_BOUND",
            ],
            "boundaries": {
                "dry_run": True,
                "engine_subprocess_called": False,
                "media_generated": False,
                "candidate_media_written": False,
                "promotion_attempted": False,
                "production_authority_claimed": False,
                "content_based_suppression": False,
                "aws_or_ec2_used": False,
                "mask_or_wave71_touched": False,
            },
        }
        result_path = root / "runtime_artifacts/audio_speech_bridge/results" / request["request_id"] / "result.json"
        write_json_atomic(result_path, result, immutable=True)
        result["result_binding"] = {
            "path": str(result_path), "sha256": sha256_file(result_path), "bytes": result_path.stat().st_size,
        }
    telemetry = {
        "schema_version": "1.0",
        "request_id": request["request_id"],
        "cache_key": key,
        "cache_hit": False,
        "device": "control_plane_cpu",
        "wall_clock_seconds": round(time.perf_counter() - started, 9),
        "peak_memory_bytes": None,
        "subprocess_exit_code": None,
        "engine_revision_hash": request["engine"]["revision_sha256"],
        "estimated_cost_usd": None,
        "media_generated": False,
    }
    telemetry_path = cache_root / "telemetry" / f"{request['request_id']}.{uuid.uuid4().hex}.json"
    write_json_atomic(telemetry_path, telemetry, immutable=True)
    result["telemetry_binding"] = {
        "path": str(telemetry_path), "sha256": sha256_file(telemetry_path), "bytes": telemetry_path.stat().st_size,
    }
    return result


class Wave64SpeechBridge:
    CATEGORY = "Wave64/Speech"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("result_json", "status", "cache_key")
    FUNCTION = "execute"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "request_json": ("STRING", {"default": "{}", "multiline": True}),
                "dry_run": ("BOOLEAN", {"default": True}),
            }
        }

    def execute(self, request_json: str, dry_run: bool = True):
        try:
            request = json.loads(request_json)
        except json.JSONDecodeError as exc:
            raise SpeechBridgeError("INVALID_BRIDGE_REQUEST:malformed_json") from exc
        result = execute_request(request, dry_run=dry_run)
        encoded = json.dumps(result, sort_keys=True, ensure_ascii=True)
        return {
            "ui": {"text": [encoded]},
            "result": (encoded, result["status"], result["cache_key"]),
        }


NODE_CLASS_MAPPINGS = {"Wave64SpeechBridge": Wave64SpeechBridge}
NODE_DISPLAY_NAME_MAPPINGS = {"Wave64SpeechBridge": "Wave64 Speech Bridge (Dry Run)"}

__all__ = [
    "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "SpeechBridgeError", "authority_blockers",
    "cache_key_payload", "cache_lock", "compute_cache_key", "execute_request", "validate_request",
]
