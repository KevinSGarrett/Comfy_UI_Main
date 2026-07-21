#!/usr/bin/env python3
"""Execute one admitted W64-AQA artifact read as a bounded digest-only action."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
GATEWAY_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py"
REQUEST_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_request.schema.json"
DECISION_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_decision.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_tool_executor_receipt.schema.json"
GATEWAY_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json"
EXECUTOR_POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_executor_policy.json"
ZERO_HASH = "0" * 64

CONTENT_SECRET_PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_token": re.compile(rb"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}\b"),
}


class ExecutorError(ValueError):
    """Raised when the executor cannot prove a safe, immutable read."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutorError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExecutorError(f"JSON root must be an object: {path}")
    return value


def _load_gateway():
    spec = importlib.util.spec_from_file_location("w64_aqa_tool_gateway_for_executor", GATEWAY_PATH)
    if spec is None or spec.loader is None:
        raise ExecutorError("cannot load the deterministic gateway")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _identity(value: os.stat_result) -> dict[str, int]:
    return {
        "device": int(value.st_dev),
        "inode": int(value.st_ino),
        "size": int(value.st_size),
        "mtime_ns": int(value.st_mtime_ns),
    }


def _is_reparse(value: os.stat_result) -> bool:
    attributes = int(getattr(value, "st_file_attributes", 0))
    flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(value.st_mode) or bool(attributes & flag)


def _validate_executor_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("schema_version") != "wave64.aqa.tool_executor_policy.v1":
        raise ExecutorError("unsupported executor policy")
    if policy.get("qualified_actions") != ["artifact_read"]:
        raise ExecutorError("executor policy must qualify artifact_read only")
    action = policy.get("artifact_read")
    if not isinstance(action, dict):
        raise ExecutorError("executor artifact_read policy is missing")
    required = {
        "digest_only": True,
        "content_exposure_allowed": False,
        "target_write_allowed": False,
        "network_allowed": False,
        "parameters_required_empty": True,
        "reject_symlinks_and_reparse_points": True,
        "require_stable_identity_before_open_after": True,
    }
    if any(action.get(key) is not expected for key, expected in required.items()):
        raise ExecutorError("executor policy weakens a mandatory read-only control")
    if not isinstance(action.get("max_bytes"), int) or not 1 <= action["max_bytes"] <= 16777216:
        raise ExecutorError("executor max_bytes is missing or unsafe")
    if not isinstance(action.get("max_elapsed_ms"), int) or not 1 <= action["max_elapsed_ms"] <= 30000:
        raise ExecutorError("executor max_elapsed_ms is missing or unsafe")
    if not isinstance(action.get("chunk_bytes"), int) or not 1 <= action["chunk_bytes"] <= 1048576:
        raise ExecutorError("executor chunk_bytes is missing or unsafe")
    return action


def _reject_sensitive_path(target: str, action_policy: dict[str, Any]) -> None:
    basename = PurePosixPath(target).name.lower()
    suffix = PurePosixPath(target).suffix.lower()
    if suffix in {str(value).lower() for value in action_policy["forbidden_suffixes"]}:
        raise ExecutorError("SENSITIVE_PATH_SUFFIX_DENIED")
    for pattern in action_policy["forbidden_basename_patterns"]:
        if re.search(pattern, basename, flags=re.IGNORECASE):
            raise ExecutorError("SENSITIVE_PATH_NAME_DENIED")


def _resolve_regular_file(job_root: Path, target: str) -> tuple[Path, os.stat_result]:
    root_lstat = os.lstat(job_root)
    if _is_reparse(root_lstat) or not stat.S_ISDIR(root_lstat.st_mode):
        raise ExecutorError("JOB_ROOT_NOT_PLAIN_DIRECTORY")
    canonical_root = job_root.resolve(strict=True)
    pure = PurePosixPath(target)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ExecutorError("UNSAFE_NORMALIZED_TARGET")
    current = canonical_root
    final_stat: os.stat_result | None = None
    for part in pure.parts:
        current = current / part
        try:
            final_stat = os.lstat(current)
        except OSError as exc:
            raise ExecutorError("TARGET_COMPONENT_NOT_READABLE") from exc
        if _is_reparse(final_stat):
            raise ExecutorError("SYMLINK_OR_REPARSE_POINT_DENIED")
    try:
        current.resolve(strict=True).relative_to(canonical_root)
    except (OSError, ValueError) as exc:
        raise ExecutorError("TARGET_ESCAPED_JOB_ROOT") from exc
    if final_stat is None or not stat.S_ISREG(final_stat.st_mode):
        raise ExecutorError("TARGET_NOT_REGULAR_FILE")
    return current, final_stat


def _read_digest(
    path: Path,
    before: os.stat_result,
    *,
    max_bytes: int,
    max_elapsed_ms: int,
    chunk_bytes: int,
    after_open_hook: Callable[[Path], None] | None = None,
) -> tuple[str, int, os.stat_result, os.stat_result]:
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    started = time.monotonic()
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before):
            raise ExecutorError("FILE_IDENTITY_CHANGED_BEFORE_OPEN")
        if opened.st_size > max_bytes:
            raise ExecutorError("ARTIFACT_SIZE_LIMIT_EXCEEDED")
        if after_open_hook is not None:
            after_open_hook(path)
        digest = hashlib.sha256()
        scanned = bytearray()
        byte_count = 0
        while True:
            if (time.monotonic() - started) * 1000 > max_elapsed_ms:
                raise ExecutorError("ARTIFACT_READ_TIME_LIMIT_EXCEEDED")
            chunk = os.read(descriptor, chunk_bytes)
            if not chunk:
                break
            byte_count += len(chunk)
            if byte_count > max_bytes:
                raise ExecutorError("ARTIFACT_SIZE_LIMIT_EXCEEDED")
            digest.update(chunk)
            scanned.extend(chunk)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = os.lstat(path)
    identities = [_identity(before), _identity(opened), _identity(opened_after), _identity(after)]
    if len({tuple(sorted(value.items())) for value in identities}) != 1:
        raise ExecutorError("FILE_IDENTITY_CHANGED_DURING_READ")
    if _is_reparse(after) or not stat.S_ISREG(after.st_mode):
        raise ExecutorError("TARGET_TYPE_CHANGED_DURING_READ")
    categories = [name for name, pattern in CONTENT_SECRET_PATTERNS.items() if pattern.search(scanned)]
    if categories:
        raise ExecutorError("SECRET_LIKE_CONTENT_DENIED:" + ",".join(sorted(categories)))
    return digest.hexdigest(), byte_count, opened, after


def execute_artifact_read(
    request: dict[str, Any],
    decision: dict[str, Any],
    job_root: Path,
    *,
    gateway_policy: dict[str, Any] | None = None,
    executor_policy: dict[str, Any] | None = None,
    after_open_hook: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    gateway_policy = gateway_policy or _load_json(GATEWAY_POLICY_PATH)
    executor_policy = executor_policy or _load_json(EXECUTOR_POLICY_PATH)
    action_policy = _validate_executor_policy(executor_policy)
    request_schema = _load_json(REQUEST_SCHEMA_PATH)
    decision_schema = _load_json(DECISION_SCHEMA_PATH)
    receipt_schema = _load_json(RECEIPT_SCHEMA_PATH)
    jsonschema.Draft7Validator(request_schema).validate(request)
    jsonschema.Draft7Validator(decision_schema).validate(decision)
    expected_decision = _load_gateway().evaluate_request(request, gateway_policy)
    if decision != expected_decision:
        raise ExecutorError("DECISION_RECOMPUTE_MISMATCH")
    if decision["admission_disposition"] != "ADMIT_FOR_SEPARATE_EXECUTOR":
        raise ExecutorError("DECISION_NOT_ADMITTED")
    if request["action_type"] != "artifact_read" or decision["action_type"] != "artifact_read":
        raise ExecutorError("ACTION_NOT_QUALIFIED_BY_EXECUTOR")
    if request["parameters"] != {}:
        raise ExecutorError("ARTIFACT_READ_PARAMETERS_MUST_BE_EMPTY")
    target = decision["normalized_target"]
    if target != request["target"]:
        raise ExecutorError("NORMALIZED_TARGET_MISMATCH")
    _reject_sensitive_path(target, action_policy)
    path, before = _resolve_regular_file(job_root, target)
    artifact_sha256, byte_count, opened, after = _read_digest(
        path,
        before,
        max_bytes=action_policy["max_bytes"],
        max_elapsed_ms=action_policy["max_elapsed_ms"],
        chunk_bytes=action_policy["chunk_bytes"],
        after_open_hook=after_open_hook,
    )
    receipt = {
        "schema_version": "wave64.aqa.tool_executor_receipt.v1",
        "receipt_id": ZERO_HASH,
        "request_id": request["request_id"],
        "decision_id": decision["decision_id"],
        "job_id": request["job_id"],
        "actor_role_id": request["actor_role_id"],
        "authority_binding_sha256": request["authority_binding_sha256"],
        "gateway_policy_sha256": hashlib.sha256(canonical_bytes(gateway_policy)).hexdigest(),
        "executor_policy_sha256": hashlib.sha256(canonical_bytes(executor_policy)).hexdigest(),
        "action_type": "artifact_read",
        "normalized_target": target,
        "disposition": "PASS_READ_ONLY_ARTIFACT_DIGEST",
        "execution_performed": True,
        "content_exposed": False,
        "target_write_performed": False,
        "network_used": False,
        "byte_count": byte_count,
        "artifact_sha256": artifact_sha256,
        "identity_before": _identity(before),
        "identity_open": _identity(opened),
        "identity_after": _identity(after),
        "reason_codes": [
            "ADMITTED_DECISION_RECOMPUTED",
            "BOUNDED_DIGEST_ONLY",
            "FILE_IDENTITY_STABLE",
        ],
    }
    receipt["receipt_id"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    jsonschema.Draft7Validator(receipt_schema).validate(receipt)
    return receipt


def _publish_immutable(output: Path, rendered: str) -> None:
    if output.exists() or output.is_symlink():
        raise ExecutorError("receipt output already exists")
    parent_stat = os.lstat(output.parent)
    if _is_reparse(parent_stat) or not stat.S_ISDIR(parent_stat.st_mode):
        raise ExecutorError("receipt output parent is not a plain directory")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
    except FileExistsError as exc:
        raise ExecutorError("receipt output already exists") from exc
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("decision", type=Path)
    parser.add_argument("--job-root", type=Path, required=True)
    parser.add_argument("--gateway-policy", type=Path, default=GATEWAY_POLICY_PATH)
    parser.add_argument("--executor-policy", type=Path, default=EXECUTOR_POLICY_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        receipt = execute_artifact_read(
            _load_json(args.request),
            _load_json(args.decision),
            args.job_root,
            gateway_policy=_load_json(args.gateway_policy),
            executor_policy=_load_json(args.executor_policy),
        )
        rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.output:
            _publish_immutable(args.output, rendered)
        else:
            sys.stdout.write(rendered)
    except (ExecutorError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
