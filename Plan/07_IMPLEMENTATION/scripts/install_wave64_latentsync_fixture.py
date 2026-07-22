#!/usr/bin/env python3
"""Atomically publish the admitted LatentSync fixture without GPU or runtime authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


class FixtureInstallError(RuntimeError):
    """Raised when fixture storage publication cannot fail closed."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _verify_admission(admission: dict[str, Any]) -> None:
    if admission.get("schema_version") != "wave64.aqa.latentsync_fixture_admission.v1":
        raise FixtureInstallError("fixture admission schema mismatch")
    if admission.get("status") != "RIGHTS_AND_TECHNICAL_FIXTURE_ADMITTED_STORAGE_PUBLISH_PENDING":
        raise FixtureInstallError("fixture admission status mismatch")
    authority = admission.get("authority", {})
    allowed = {
        "local_fixture_binding",
        "rights_provenance_validation",
        "technical_decode_validation",
        "remote_storage_stage",
        "atomic_no_overwrite_publish",
        "storage_receipt",
    }
    if any(authority.get(name) is not True for name in allowed):
        raise FixtureInstallError("fixture storage authority missing")
    if any(value is not False for name, value in authority.items() if name not in allowed):
        raise FixtureInstallError("fixture admission exceeds storage authority")


def _records(admission: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "role": role,
            "name": admission[role]["remote_name"],
            "bytes": admission[role]["bytes"],
            "sha256": admission[role]["sha256"],
        }
        for role in ("video", "audio")
    ]


def _verify_file(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FixtureInstallError(f"missing, non-file, or symlink fixture: {record['name']}")
    if path.stat().st_size != record["bytes"]:
        raise FixtureInstallError(f"fixture size mismatch: {record['name']}")
    observed = sha256(path)
    if observed != record["sha256"]:
        raise FixtureInstallError(f"fixture sha256 mismatch: {record['name']}")
    return {**record, "sha256": observed}


def install(
    admission: dict[str, Any],
    source_root: Path,
    target: Path,
    receipt_path: Path,
    *,
    production: bool = True,
) -> dict[str, Any]:
    _verify_admission(admission)
    declared_target = admission["remote"]["target_root"]
    declared_receipt = admission["remote"]["receipt_path"]
    if production:
        if target.as_posix() != declared_target or receipt_path.as_posix() != declared_receipt:
            raise FixtureInstallError("CLI paths differ from admitted production paths")
        if not declared_target.startswith("/workspace/w64_aqa/fixtures/W64-AQA-017/"):
            raise FixtureInstallError("fixture target escaped admitted durable root")
        if not source_root.as_posix().startswith("/workspace/w64_aqa/tmp/"):
            raise FixtureInstallError("fixture source escaped transient staging root")
    records = _records(admission)
    source_verified = [_verify_file(source_root / record["name"], record) for record in records]
    admission_sha256 = hashlib.sha256(canonical_bytes(admission)).hexdigest()
    target_receipt_name = ".w64_aqa_fixture_receipt.json"

    if target.exists():
        target_receipt = target / target_receipt_name
        if not target.is_dir() or target.is_symlink() or not target_receipt.is_file():
            raise FixtureInstallError("target exists without a valid fixture receipt")
        receipt = json.loads(target_receipt.read_text(encoding="utf-8"))
        if receipt.get("admission_sha256") != admission_sha256:
            raise FixtureInstallError("existing fixture receipt admission mismatch")
        target_verified = [_verify_file(target / record["name"], record) for record in records]
        if receipt.get("files") != target_verified:
            raise FixtureInstallError("existing fixture receipt inventory mismatch")
        if receipt_path.exists():
            external = json.loads(receipt_path.read_text(encoding="utf-8"))
            if external != receipt:
                raise FixtureInstallError("external fixture receipt mismatch")
        else:
            atomic_json(receipt_path, receipt)
        return {**receipt, "replay": "REUSED_VERIFIED_FIXTURE"}

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.installing"
    if staging.exists():
        raise FixtureInstallError("fixture staging path already exists")
    staging.mkdir()
    try:
        for record in records:
            destination = staging / record["name"]
            with (source_root / record["name"]).open("rb") as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
        target_verified = [_verify_file(staging / record["name"], record) for record in records]
        if target_verified != source_verified:
            raise FixtureInstallError("published fixture differs from staged source")
        receipt = {
            "schema_version": "wave64.aqa.latentsync_fixture_receipt.v1",
            "program_id": "W64-AQA",
            "tracker_id": "TRK-W64-137",
            "fixture_id": admission["fixture_id"],
            "status": "FIXTURE_BYTES_VERIFIED_NOT_LOADED_OR_INFERRED",
            "admission_sha256": admission_sha256,
            "target_root": declared_target,
            "files": target_verified,
            "rights_scope": admission["purpose"],
            "runtime_claims": {
                "gpu_or_lease_polled": False,
                "model_loaded": False,
                "inference_performed": False,
                "identity_preservation": False,
                "av_sync": False,
                "product_authority": False,
            },
        }
        atomic_json(staging / target_receipt_name, receipt)
        os.replace(staging, target)
        atomic_json(receipt_path, receipt)
        return {**receipt, "replay": "NEW_ATOMIC_FIXTURE_INSTALL"}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--test-mode", action="store_true")
    args = parser.parse_args()
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    result = install(
        admission,
        args.source_root,
        args.target,
        args.receipt,
        production=not args.test_mode,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
