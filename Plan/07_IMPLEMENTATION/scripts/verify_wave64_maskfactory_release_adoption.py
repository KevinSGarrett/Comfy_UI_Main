from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[3]
SEMANTIC_CORE = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_maskfactory_autonomous_bridge_package.py"
REQUIRED_BUNDLE_FILES = ("release.json", "adoption.json", "consumer.json")
MAX_ARCHIVE_FILES = 4096
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
UNPUBLISHED_BLOCKER = "Blocked_MaskFactory_Runtime_Release_Unpublished"


def load_semantic_core():
    spec = importlib.util.spec_from_file_location("wave64_maskfactory_bridge_semantic_core", SEMANTIC_CORE)
    if spec is None or spec.loader is None:
        raise RuntimeError("MaskFactory bridge semantic core cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_semantic_core()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def strict_json_bytes(raw: bytes) -> Any:
    return CORE.strict_json_loads(raw)


def strict_json_file(path: Path) -> Any:
    return strict_json_bytes(path.read_bytes())


def _safe_member_path(name: str) -> PurePosixPath:
    if not name or "\\" in name or ":" in name:
        raise ValueError(f"unsafe archive member path: {name!r}")
    value = PurePosixPath(name)
    if value.is_absolute() or any(part in {"", ".", ".."} for part in value.parts):
        raise ValueError(f"unsafe archive member path: {name!r}")
    return value


def safe_extract_zip(archive: Path, destination: Path) -> None:
    seen: set[str] = set()
    total_bytes = 0
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > MAX_ARCHIVE_FILES:
            raise ValueError("release archive exceeds the member-count limit")
        for member in members:
            relative = _safe_member_path(member.filename.rstrip("/"))
            collision_key = relative.as_posix().casefold()
            if collision_key in seen:
                raise ValueError("release archive contains duplicate or case-colliding paths")
            seen.add(collision_key)
            unix_mode = member.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise ValueError("release archive contains a symbolic link")
            if member.flag_bits & 0x1:
                raise ValueError("encrypted release archives are not accepted")
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError("release archive member exceeds the size limit")
            total_bytes += member.file_size
            if total_bytes > MAX_ARCHIVE_BYTES:
                raise ValueError("release archive exceeds the uncompressed-size limit")
            if member.compress_size == 0 and member.file_size:
                raise ValueError("release archive member has an invalid compression ratio")
            if member.compress_size and member.file_size / member.compress_size > MAX_COMPRESSION_RATIO:
                raise ValueError("release archive member exceeds the compression-ratio limit")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            written = 0
            with bundle.open(member, "r") as source, target.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > member.file_size or written > MAX_MEMBER_BYTES:
                        raise ValueError("release archive member expanded beyond its declared size")
                    output.write(chunk)
            if written != member.file_size:
                raise ValueError("release archive member size differs from its ZIP declaration")


def _resolve_bundle_file(root: Path, relative: str) -> Path:
    value = _safe_member_path(relative)
    root_resolved = root.resolve()
    candidate = root.joinpath(*value.parts).resolve(strict=True)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"bundle path escapes the release root: {relative}") from exc
    if not candidate.is_file():
        raise ValueError(f"bundle path is not a regular file: {relative}")
    return candidate


def _ref_key(value: dict[str, str]) -> tuple[str, str, str, str]:
    return tuple(value[key] for key in ("record_type", "record_id", "revision", "sha256"))


def load_runtime_context(root: Path, path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    raw = strict_json_file(path)
    if not isinstance(raw, dict):
        raise ValueError("verification context must be a JSON object")
    allowed = {
        "schema_version",
        "artifact_files",
        "producer_wire_schema_files",
        "trusted_keys",
        "trusted_clock",
        "last_accepted_use_time",
        "last_accepted_clock_sequence",
        "use_time",
        "producer_invalidation_policy",
        "producer_invalidation_policy_adopted_from_signed_release",
        "producer_release_revocation_refs",
        "producer_revocation_state_ref",
        "producer_active_revocation_count",
        "adopted_capability_snapshot_ref",
        "adopted_producer_release_binding",
        "adopted_main_release_ref",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"verification context has unknown fields: {sorted(unknown)}")
    if raw.get("schema_version") != "1.0.0":
        raise ValueError("verification context schema_version must be 1.0.0")
    context = {key: value for key, value in raw.items() if key not in {"artifact_files", "producer_wire_schema_files", "schema_version"}}
    context["artifact_bytes"] = {}
    for entry in raw.get("artifact_files", []):
        if not isinstance(entry, dict) or set(entry) != {"ref", "path"}:
            raise ValueError("artifact_files entries require exactly ref and path")
        payload = _resolve_bundle_file(root, entry["path"]).read_bytes()
        if sha256_bytes(payload) != entry["ref"]["sha256"]:
            raise ValueError("verification-context artifact hash mismatch")
        key = _ref_key(entry["ref"])
        if key in context["artifact_bytes"]:
            raise ValueError("verification context contains a duplicate immutable artifact ref")
        context["artifact_bytes"][key] = payload
    context["producer_wire_schema_bytes"] = {}
    for name, relative in raw.get("producer_wire_schema_files", {}).items():
        if name in context["producer_wire_schema_bytes"]:
            raise ValueError("verification context contains a duplicate producer schema name")
        context["producer_wire_schema_bytes"][name] = _resolve_bundle_file(root, relative).read_bytes()
    context["private_keys"] = {}
    return context


def validate_schema(record: dict[str, Any], schema_name: str) -> None:
    schemas = CORE.build_schemas()
    registry = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
    )
    schema = schemas[schema_name]
    errors = sorted(
        jsonschema.Draft202012Validator(
            schema,
            registry=registry,
            format_checker=jsonschema.FormatChecker(),
        ).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        pointer = "/" + "/".join(str(part) for part in first.absolute_path)
        raise ValueError(f"{schema_name} schema failure at {pointer}: {first.message}")


def verify_documents(
    release: dict[str, Any],
    adoption: dict[str, Any],
    consumer: dict[str, Any],
    context: dict[str, Any] | None,
    *,
    allow_fixture: bool,
) -> dict[str, Any]:
    validate_schema(release, "maskfactory_release_snapshot_v2.schema.json")
    validate_schema(adoption, "maskfactory_adoption_receipt_v2.schema.json")
    validate_schema(consumer, "maskfactory_consumer_requirements_v2.schema.json")
    production = bool(adoption["production_consumption_allowed"])
    if production:
        if context is None:
            raise ValueError("production adoption requires an independent verification context")
        trusted_keys = context.get("trusted_keys")
        if not isinstance(trusted_keys, dict):
            raise ValueError("production adoption requires an out-of-band trusted-key registry")
        use_time = context.get("use_time")
        CORE.validate_adoption_trust(
            adoption,
            consumer,
            release,
            trusted_keys,
            context,
            use_time=use_time,
        )
        return {
            "classification": "MASKFACTORY_PRODUCTION_ADOPTION_VERIFIED",
            "production_consumption_allowed": True,
            "active_pin_write_allowed": True,
            "fixture_only": False,
        }
    if not allow_fixture:
        raise ValueError("fixture-only release cannot satisfy production adoption")
    CORE.validate_adoption_trust(adoption, consumer, release, {}, None, use_time=None)
    if not release["fixture_only"] or not adoption["fixture_only"]:
        raise ValueError("non-production verification is restricted to explicit fixtures")
    return {
        "classification": "MASKFACTORY_FIXTURE_CONTRACT_VERIFIED_NOT_ADOPTED",
        "production_consumption_allowed": False,
        "active_pin_write_allowed": False,
        "fixture_only": True,
    }


def _pin_sha256(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(value))


def write_active_pin(
    state_root: Path,
    release: dict[str, Any],
    adoption: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    if not verification.get("active_pin_write_allowed"):
        raise ValueError("active pin write is forbidden for this verification result")
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / ".maskfactory-pin.lock"
    lock_fd = None
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(lock_fd, str(os.getpid()).encode("ascii"))
        os.fsync(lock_fd)
        os.close(lock_fd)
        lock_fd = None
        active_path = state_root / "active_pin.json"
        previous = strict_json_file(active_path) if active_path.exists() else None
        release_ref = CORE.immutable_release_ref(release)
        adoption_ref = CORE.immutable_adoption_ref(adoption)
        if previous and previous.get("release_ref") == release_ref and previous.get("adoption_ref") == adoption_ref:
            return {"idempotent": True, "active_pin": previous, "active_pin_sha256": _pin_sha256(previous)}
        previous_sha = _pin_sha256(previous) if previous else None
        if previous:
            history = state_root / "history"
            history.mkdir(parents=True, exist_ok=True)
            history_path = history / f"{previous_sha}.json"
            previous_bytes = canonical_json(previous)
            if history_path.exists() and history_path.read_bytes() != previous_bytes:
                raise ValueError("existing pin history entry does not match its canonical hash")
            if not history_path.exists():
                history_path.write_bytes(previous_bytes)
        pin = {
            "schema_version": "1.0.0",
            "record_type": "maskfactory_active_release_pin",
            "release_ref": release_ref,
            "adoption_ref": adoption_ref,
            "decided_at": adoption["decided_at"],
            "valid_until": adoption["valid_until"],
            "previous_pin_sha256": previous_sha,
            "rollback_candidate_present": previous is not None,
            "rollback_requires_fresh_revocation_revalidation": previous is not None,
            "production_consumption_allowed": True,
            "fixture_only": False,
        }
        payload = canonical_json(pin)
        temp_path = state_root / f".active_pin.{os.getpid()}.tmp"
        with temp_path.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, active_path)
        return {"idempotent": False, "active_pin": pin, "active_pin_sha256": sha256_bytes(payload)}
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def verify_bundle_root(root: Path, *, allow_fixture: bool, state_root: Path | None) -> dict[str, Any]:
    for name in REQUIRED_BUNDLE_FILES:
        _resolve_bundle_file(root, name)
    release = strict_json_file(_resolve_bundle_file(root, "release.json"))
    adoption = strict_json_file(_resolve_bundle_file(root, "adoption.json"))
    consumer = strict_json_file(_resolve_bundle_file(root, "consumer.json"))
    if not all(isinstance(value, dict) for value in (release, adoption, consumer)):
        raise ValueError("release, adoption, and consumer documents must be JSON objects")
    context_path = root / "verification_context.json"
    context = load_runtime_context(root, context_path if context_path.is_file() else None)
    verification = verify_documents(release, adoption, consumer, context, allow_fixture=allow_fixture)
    result = {
        "status": "PASS",
        **verification,
        "release_ref": CORE.immutable_release_ref(release),
        "adoption_ref": CORE.immutable_adoption_ref(adoption),
        "runtime_completion_claimed": False,
        "row348_release_claimed": False,
    }
    if verification["active_pin_write_allowed"]:
        if state_root is None:
            raise ValueError("production adoption verification requires --state-root for atomic pinning")
        result["pin"] = write_active_pin(state_root, release, adoption, verification)
    return result


def verify_bundle(bundle: Path, *, allow_fixture: bool, state_root: Path | None) -> dict[str, Any]:
    if bundle.is_dir():
        return verify_bundle_root(bundle.resolve(), allow_fixture=allow_fixture, state_root=state_root)
    if not bundle.is_file() or bundle.suffix.lower() != ".zip":
        raise ValueError("release bundle must be a directory or ZIP archive")
    with tempfile.TemporaryDirectory(prefix="maskfactory-release-") as temporary:
        root = Path(temporary)
        safe_extract_zip(bundle, root)
        return verify_bundle_root(root, allow_fixture=allow_fixture, state_root=state_root)


def unpublished_record() -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "classification": UNPUBLISHED_BLOCKER,
        "release_snapshot_available": False,
        "runtime_release_published": False,
        "runtime_release_adopted": False,
        "production_consumption_allowed": False,
        "active_pin_write_allowed": False,
        "runtime_completion_claimed": False,
        "row_states": {
            "ITEM-W64-321": "Planned_Autonomous_Implementation_Required",
            "ITEM-W64-322": "Planned_Autonomous_Implementation_Required",
            "ITEM-W64-323": "Planned_Autonomous_Implementation_Required",
            "ITEM-W64-324": "Planned_Autonomous_Implementation_Required",
        },
        "next_external_event": "MaskFactory publishes a genuine immutable v2-compatible signed runtime release",
    }


def write_output(path: Path | None, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(payload, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--bundle", type=Path)
    mode.add_argument("--record-unpublished", action="store_true")
    parser.add_argument("--allow-fixture", action="store_true")
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = unpublished_record() if args.record_unpublished else verify_bundle(
            args.bundle.resolve(),
            allow_fixture=args.allow_fixture,
            state_root=args.state_root.resolve() if args.state_root else None,
        )
        write_output(args.output, result)
    except Exception as exc:
        write_output(args.output, {
            "status": "FAIL",
            "classification": "MASKFACTORY_RELEASE_ADOPTION_VERIFICATION_FAILED",
            "error": str(exc),
            "production_consumption_allowed": False,
            "active_pin_write_allowed": False,
            "runtime_completion_claimed": False,
        })
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
