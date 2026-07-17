from __future__ import annotations

import argparse
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
MAPPING_PATH = ROOT / "Plan/10_REGISTRIES/wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"
REQUEST_SCHEMA = "maskfactory_bridge_request_v2.schema.json"
INPUT_RECORD_TYPE = "maskfactory_bridge_request_compile_input"
RECEIPT_RECORD_TYPE = "maskfactory_bridge_request_compilation_receipt"
OWNED_REQUEST_FIELDS = {
    "schema_version",
    "record_type",
    "maskfactory_bridge_request_v2_id",
    "revision",
    "created_at",
    "fixture_only",
    "runtime_completion_claimed",
    "idempotency_key",
}
REQUIRED_PRODUCER_CONTRACTS = {"mask_acquisition_request", "mask_acquisition_receipt"}


def _load_verifier():
    spec = importlib.util.spec_from_file_location("wave64_maskfactory_release_verifier_for_compiler", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("MaskFactory release verifier cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VERIFY = _load_verifier()
CORE = VERIFY.CORE


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_file(path: Path) -> Any:
    return VERIFY.strict_json_file(path)


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{label} fields differ from the closed contract: "
            f"missing={sorted(expected - actual)} unknown={sorted(actual - expected)}"
        )
    return value


def _parse_timestamp(value: str, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a UTC offset")
    return parsed


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(f"unsafe immutable-record path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe immutable-record path: {value!r}")
    return path


def _immutable_ref_key(ref: dict[str, Any]) -> tuple[str, str, str, str]:
    _require_exact_keys(ref, {"record_type", "record_id", "revision", "sha256"}, "immutable ref")
    if not all(isinstance(ref[key], str) and ref[key] for key in ("record_type", "record_id", "revision")):
        raise ValueError("immutable ref identity fields must be non-empty strings")
    if not isinstance(ref["sha256"], str) or len(ref["sha256"]) != 64:
        raise ValueError("immutable ref SHA-256 must contain 64 lowercase hexadecimal characters")
    try:
        int(ref["sha256"], 16)
    except ValueError as exc:
        raise ValueError("immutable ref SHA-256 must contain 64 lowercase hexadecimal characters") from exc
    if ref["sha256"] != ref["sha256"].lower():
        raise ValueError("immutable ref SHA-256 must contain lowercase hexadecimal characters")
    return (ref["record_type"], ref["record_id"], ref["revision"], ref["sha256"])


def _collect_immutable_refs(value: Any) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    collected: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    identity_hashes: dict[tuple[str, str, str], str] = {}

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            if set(current) == {"record_type", "record_id", "revision", "sha256"}:
                key = _immutable_ref_key(current)
                identity = key[:3]
                previous_hash = identity_hashes.setdefault(identity, key[3])
                if previous_hash != key[3]:
                    raise ValueError("one immutable record identity resolves to multiple hashes")
                collected[key] = current
            for child in current.values():
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return collected


def _verify_immutable_records(
    request: dict[str, Any],
    authorization: dict[str, Any],
    records: list[dict[str, Any]],
    record_root: Path,
) -> dict[tuple[str, str, str, str], Path]:
    if not isinstance(records, list) or not records:
        raise ValueError("immutable_records must contain every referenced immutable record")
    expected = _collect_immutable_refs({"request": request, "authorization_ref": authorization["authorization_ref"]})
    resolved: dict[tuple[str, str, str, str], Path] = {}
    root = record_root.resolve()
    for entry in records:
        _require_exact_keys(entry, {"ref", "path"}, "immutable_records entry")
        key = _immutable_ref_key(entry["ref"])
        if key in resolved:
            raise ValueError("immutable_records contains a duplicate ref")
        relative = _safe_relative_path(entry["path"])
        path = root.joinpath(*relative.parts).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("immutable-record path escapes the declared record root") from exc
        if not path.is_file():
            raise ValueError(f"immutable-record bytes are missing: {relative.as_posix()}")
        if sha256_bytes(path.read_bytes()) != key[3]:
            raise ValueError(f"immutable-record hash mismatch: {relative.as_posix()}")
        resolved[key] = path
    missing = set(expected) - set(resolved)
    unused = set(resolved) - set(expected)
    if missing or unused:
        raise ValueError(
            "immutable-record catalog does not exactly cover request references: "
            f"missing={len(missing)} unused={len(unused)}"
        )
    return resolved


def _allowed_contract_bindings() -> set[bytes]:
    registry = strict_json_file(MAPPING_PATH)
    if not isinstance(registry, dict) or not isinstance(registry.get("mappings"), list):
        raise ValueError("producer wire mapping registry is malformed")
    allowed: set[bytes] = set()
    for mapping in registry["mappings"]:
        binding = mapping.get("producer_binding")
        if not isinstance(binding, dict):
            continue
        projected = {
            "wire_schema_name": binding["contract_name"],
            "schema_id": binding["schema_id"],
            "schema_version": binding["schema_version"],
            "schema_sha256": binding["schema_sha256"],
        }
        allowed.add(canonical_json(projected))
    return allowed


def _validate_contract_bindings(request: dict[str, Any]) -> None:
    bindings = request["expected_contract_bindings"]
    names = [binding["wire_schema_name"] for binding in bindings]
    if len(names) != len(set(names)):
        raise ValueError("expected contract bindings contain duplicate wire schema names")
    missing = REQUIRED_PRODUCER_CONTRACTS - set(names)
    if missing:
        raise ValueError(f"expected contract bindings omit required producer contracts: {sorted(missing)}")
    allowed = _allowed_contract_bindings()
    for binding in bindings:
        identity = {
            key: binding[key]
            for key in ("wire_schema_name", "schema_id", "schema_version", "schema_sha256")
        }
        expected_source = f"maskfactory_release://contracts/{binding['wire_schema_name']}.schema.json"
        if binding["schema_source"] != expected_source:
            raise ValueError(
                f"expected contract binding does not use its immutable release-relative source: {binding['wire_schema_name']}"
            )
        if canonical_json(identity) not in allowed:
            raise ValueError(f"expected contract binding is not frozen in the executable mapping: {binding['wire_schema_name']}")


def _validate_authorization(
    authorization: dict[str, Any],
    request: dict[str, Any],
) -> None:
    _require_exact_keys(
        authorization,
        {
            "principal_id",
            "principal_role",
            "nonce",
            "issued_at",
            "expires_at",
            "allowed_access_modes",
            "allowed_intended_uses",
            "authorization_ref",
        },
        "authorization_context",
    )
    for field in ("principal_id", "principal_role", "nonce"):
        if not isinstance(authorization[field], str) or len(authorization[field]) < 3:
            raise ValueError(f"authorization_context.{field} must be a non-empty stable identifier")
    modes = authorization["allowed_access_modes"]
    uses = authorization["allowed_intended_uses"]
    if not isinstance(modes, list) or len(modes) != len(set(modes)) or request["access_mode"] not in modes:
        raise ValueError("authorization does not allow the exact requested access mode")
    if not isinstance(uses, list) or len(uses) != len(set(uses)) or request["intended_use"] not in uses:
        raise ValueError("authorization does not allow the exact requested intended use")
    issued = _parse_timestamp(authorization["issued_at"], "authorization_context.issued_at")
    expires = _parse_timestamp(authorization["expires_at"], "authorization_context.expires_at")
    created = _parse_timestamp(request["created_at"], "request.created_at")
    deadline = _parse_timestamp(request["deadline_at"], "request.deadline_at")
    if not issued <= created < deadline <= expires:
        raise ValueError("authorization window does not cover request creation through deadline")
    _immutable_ref_key(authorization["authorization_ref"])


def _validate_request_policy(request: dict[str, Any], known_outputs: list[str]) -> None:
    created = _parse_timestamp(request["created_at"], "request.created_at")
    deadline = _parse_timestamp(request["deadline_at"], "request.deadline_at")
    if deadline <= created:
        raise ValueError("request deadline must be later than request creation")
    if not isinstance(known_outputs, list) or len(known_outputs) != len(set(known_outputs)):
        raise ValueError("known_output_artifact_sha256s must be a unique array")
    for value in known_outputs:
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError("known output artifact hashes must be SHA-256 values")
    region_hashes: set[str] = set()
    for region in request["target_region_bindings"] + request["protected_region_bindings"]:
        digest = region["region_sha256"]
        if digest in region_hashes:
            raise ValueError("target and protected input regions contain an ambiguous hash identity")
        region_hashes.add(digest)
        if digest in known_outputs:
            mode_a_exception = (
                request["access_mode"] == "mode_a_package_read"
                and region["selector_kind"] == "mode_a_exact_package_artifact"
            )
            if not mode_a_exception:
                raise ValueError("MFB_INPUT_OUTPUT_IDENTITY_COLLISION")
    promotion_bound = request["intended_use"] == "promotion_bound"
    if request["production_promotion_requested"] != promotion_bound:
        raise ValueError("promotion request flag and intended use disagree")
    if promotion_bound:
        if request["fixture_only"]:
            raise ValueError("fixture requests cannot request production promotion")
        if request["minimum_authority_state"] != "certified":
            raise ValueError("promotion-bound requests require certified minimum authority")
        if "operationally_certified_artifact" not in request["accepted_claim_classes"]:
            raise ValueError("promotion-bound requests require the operational certificate claim class")
        if not request["required_certificate_scope"]:
            raise ValueError("promotion-bound requests require an explicit certificate scope")
    _validate_contract_bindings(request)
    CORE.validate_request_ownership(request)


def _validate_active_pin(request: dict[str, Any], active_pin: dict[str, Any] | None) -> None:
    if request["fixture_only"]:
        return
    if active_pin is None:
        raise ValueError("production request compilation requires an active MaskFactory release pin")
    expected = {
        "schema_version",
        "record_type",
        "release_ref",
        "adoption_ref",
        "decided_at",
        "valid_until",
        "previous_pin_sha256",
        "rollback_candidate_present",
        "rollback_requires_fresh_revocation_revalidation",
        "production_consumption_allowed",
        "fixture_only",
    }
    _require_exact_keys(active_pin, expected, "active release pin")
    if active_pin["record_type"] != "maskfactory_active_release_pin" or active_pin["fixture_only"]:
        raise ValueError("active release pin is not production-authoritative")
    if not active_pin["production_consumption_allowed"]:
        raise ValueError("active release pin forbids production consumption")
    if active_pin["release_ref"] != request["release_snapshot_ref"]:
        raise ValueError("request release snapshot does not match the active release pin")
    if _parse_timestamp(request["created_at"], "request.created_at") > _parse_timestamp(
        active_pin["valid_until"], "active_pin.valid_until"
    ):
        raise ValueError("active release pin is expired at request creation")


def _derive_request(packet: dict[str, Any]) -> dict[str, Any]:
    schemas = CORE.build_schemas()
    expected_body_fields = set(schemas[REQUEST_SCHEMA]["required"]) - OWNED_REQUEST_FIELDS
    body = _require_exact_keys(packet["request_body"], expected_body_fields, "request_body")
    logical_effect = {
        "request_revision": packet["request_revision"],
        "request_body": body,
    }
    digest = sha256_bytes(canonical_json(logical_effect))
    return {
        "schema_version": "2.0.0",
        "record_type": "maskfactory_bridge_request_v2",
        "maskfactory_bridge_request_v2_id": f"mfb_request_{digest[:40]}",
        "revision": packet["request_revision"],
        "created_at": packet["created_at"],
        "fixture_only": packet["fixture_only"],
        "runtime_completion_claimed": False,
        "idempotency_key": f"mfb_idempotency_{digest}",
        **body,
    }


def _reserve_nonce(
    state_root: Path,
    authorization: dict[str, Any],
    request_sha256: str,
) -> dict[str, Any]:
    state_root.mkdir(parents=True, exist_ok=True)
    nonce_digest = sha256_bytes(
        f"{authorization['principal_id']}\0{authorization['nonce']}".encode("utf-8")
    )
    target = state_root / f"{nonce_digest}.json"
    lock = state_root / f".{nonce_digest}.lock"
    lock_fd = None
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(lock_fd, str(os.getpid()).encode("ascii"))
        os.fsync(lock_fd)
        os.close(lock_fd)
        lock_fd = None
        if target.exists():
            raise ValueError("authorization nonce replay detected")
        record = {
            "schema_version": "1.0.0",
            "record_type": "maskfactory_request_nonce_reservation",
            "principal_id": authorization["principal_id"],
            "principal_role": authorization["principal_role"],
            "nonce_sha256": nonce_digest,
            "authorization_ref": authorization["authorization_ref"],
            "request_payload_sha256": request_sha256,
            "issued_at": authorization["issued_at"],
            "expires_at": authorization["expires_at"],
        }
        payload = canonical_json(record)
        temp = state_root / f".{nonce_digest}.{os.getpid()}.tmp"
        with temp.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, target)
        return {
            "record_path": target.as_posix(),
            "record_sha256": sha256_bytes(payload),
            "nonce_sha256": nonce_digest,
        }
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def compile_request(
    packet: dict[str, Any],
    *,
    record_root: Path,
    nonce_state_root: Path,
    active_pin: dict[str, Any] | None = None,
    allow_fixture: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_exact_keys(
        packet,
        {
            "schema_version",
            "record_type",
            "request_revision",
            "created_at",
            "fixture_only",
            "request_body",
            "authorization_context",
            "immutable_records",
            "known_output_artifact_sha256s",
        },
        "compile input",
    )
    if packet["schema_version"] != "1.0.0" or packet["record_type"] != INPUT_RECORD_TYPE:
        raise ValueError("compile input type or version is unsupported")
    if packet["fixture_only"] and not allow_fixture:
        raise ValueError("fixture request compilation requires explicit allow_fixture")
    request = _derive_request(packet)
    VERIFY.validate_schema(request, REQUEST_SCHEMA)
    _validate_authorization(packet["authorization_context"], request)
    _validate_request_policy(request, packet["known_output_artifact_sha256s"])
    _validate_active_pin(request, active_pin)
    resolved = _verify_immutable_records(
        request,
        packet["authorization_context"],
        packet["immutable_records"],
        record_root,
    )
    request_payload = canonical_json(request)
    request_sha256 = sha256_bytes(request_payload)
    nonce = _reserve_nonce(nonce_state_root, packet["authorization_context"], request_sha256)
    receipt = {
        "schema_version": "1.0.0",
        "record_type": RECEIPT_RECORD_TYPE,
        "request_ref": {
            "record_type": request["record_type"],
            "record_id": request["maskfactory_bridge_request_v2_id"],
            "revision": request["revision"],
            "sha256": request_sha256,
        },
        "authorization_ref": packet["authorization_context"]["authorization_ref"],
        "principal_id": packet["authorization_context"]["principal_id"],
        "principal_role": packet["authorization_context"]["principal_role"],
        "nonce_sha256": nonce["nonce_sha256"],
        "nonce_reservation_sha256": nonce["record_sha256"],
        "idempotency_key": request["idempotency_key"],
        "resolved_immutable_reference_count": len(resolved),
        "active_release_pin_required": not request["fixture_only"],
        "active_release_pin_matched": not request["fixture_only"],
        "fixture_only": request["fixture_only"],
        "runtime_completion_claimed": False,
        "production_submission_authorized": False,
        "result": "PASS_STATIC_REQUEST_COMPILATION_ONLY",
        "blockers": ["runtime_route_admission_and_submission_not_executed"],
    }
    return request, receipt


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(canonical_json(payload))
        output.flush()
        os.fsync(output.fileno())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile one strict Main-owned MaskFactory bridge v2 request")
    parser.add_argument("--compile-input", type=Path, required=True)
    parser.add_argument("--record-root", type=Path, required=True)
    parser.add_argument("--nonce-state-root", type=Path, required=True)
    parser.add_argument("--active-pin", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--allow-fixture", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.output.exists() or args.receipt.exists():
            raise ValueError("output and receipt paths must not already exist")
        packet = strict_json_file(args.compile_input)
        active_pin = strict_json_file(args.active_pin) if args.active_pin else None
        request, receipt = compile_request(
            packet,
            record_root=args.record_root,
            nonce_state_root=args.nonce_state_root,
            active_pin=active_pin,
            allow_fixture=args.allow_fixture,
        )
        _write_new(args.output, request)
        _write_new(args.receipt, receipt)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "classification": "MASKFACTORY_REQUEST_COMPILATION_REJECTED", "issue": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "PASS",
                "classification": "MASKFACTORY_REQUEST_COMPILED_STATIC_ONLY",
                "request": str(args.output.resolve()),
                "receipt": str(args.receipt.resolve()),
                "runtime_completion_claimed": False,
                "production_submission_authorized": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
