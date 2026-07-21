#!/usr/bin/env python3
"""Stage and replay a complete W64-AQA evidence bundle in S3 without promotion."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Protocol

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py"
POLICY_PATH = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_s3_bundle_transaction_policy.json"
RECEIPT_SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_s3_bundle_transaction_receipt.schema.json"
ZERO_HASH = "0" * 64


class BundleTransactionError(ValueError):
    """Raised when an S3 bundle transaction cannot remain exact and resumable."""


class S3Client(Protocol):
    def head(self, bucket: str, key: str) -> dict[str, Any] | None: ...
    def put_if_absent(self, bucket: str, key: str, source: Path, content_sha256: str, bundle_id: str) -> bool: ...


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleTransactionError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleTransactionError(f"JSON root must be an object: {path}")
    return value


def _load_component(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BundleTransactionError(f"cannot load component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_policy(policy: dict[str, Any]) -> None:
    exact = {
        "schema_version": "wave64.aqa.s3_bundle_transaction_policy.v1",
        "execution_authority": "CODEX_INTEGRATION_ONLY",
        "bucket": "comfy-ui-main-runtime-029530099913-us-east-1",
        "region": "us-east-1",
        "key_prefix": "evidence/w64-aqa/qualification/bundles",
        "content_addressed_objects_required": True,
        "manifest_written_last": True,
        "conditional_create_required": True,
        "head_replay_required": True,
        "checksum_sha256_required": True,
        "server_side_encryption": "AES256",
        "bucket_versioning_required": True,
        "resume_by_verified_reuse": True,
        "overwrite_allowed": False,
        "delete_allowed": False,
        "rollback_is_nonpublication": True,
        "s3_presence_is_acceptance": False,
        "product_promotion_allowed": False,
        "max_objects": 256,
        "max_object_bytes": 67108864,
        "max_total_bytes": 268435456,
        "all_other_buckets_or_prefixes": "UNQUALIFIED_DENY",
    }
    if any(policy.get(key) != expected for key, expected in exact.items()):
        raise BundleTransactionError("S3 bundle transaction policy changed or weakened")


def _verify_head(head: dict[str, Any] | None, key: str, expected_sha256: str, expected_size: int) -> dict[str, Any]:
    if head is None:
        raise BundleTransactionError(f"S3_HEAD_MISSING:{key}")
    metadata = {str(k).lower(): str(v) for k, v in head.get("Metadata", {}).items()}
    if metadata.get("content-sha256") != expected_sha256:
        raise BundleTransactionError(f"S3_METADATA_HASH_MISMATCH:{key}")
    if int(head.get("ContentLength", -1)) != expected_size:
        raise BundleTransactionError(f"S3_CONTENT_LENGTH_MISMATCH:{key}")
    if head.get("ServerSideEncryption") != "AES256":
        raise BundleTransactionError(f"S3_ENCRYPTION_MISMATCH:{key}")
    if not head.get("ChecksumSHA256"):
        raise BundleTransactionError(f"S3_CHECKSUM_MISSING:{key}")
    if not head.get("VersionId"):
        raise BundleTransactionError(f"S3_VERSION_ID_MISSING:{key}")
    return {
        "key": key,
        "content_sha256": expected_sha256,
        "size_bytes": expected_size,
        "version_id": head["VersionId"],
        "server_side_encryption": "AES256",
    }


def _stage_one(
    client: S3Client, bucket: str, key: str, source: Path, content_sha256: str, bundle_id: str,
) -> dict[str, Any]:
    size = source.stat().st_size
    existing = client.head(bucket, key)
    if existing is not None:
        result = _verify_head(existing, key, content_sha256, size)
        result["status"] = "REUSED_VERIFIED"
        return result
    created = client.put_if_absent(bucket, key, source, content_sha256, bundle_id)
    head = client.head(bucket, key)
    result = _verify_head(head, key, content_sha256, size)
    result["status"] = "CREATED_VERIFIED" if created else "REUSED_VERIFIED"
    return result


def execute_bundle_transaction(
    bundle: dict[str, Any], contract: dict[str, Any], decision: dict[str, Any],
    record_specs: list[dict[str, Any]], client: S3Client, source_head: str,
    *, policy: dict[str, Any] | None = None, inject_crash_after_objects: int | None = None,
) -> dict[str, Any]:
    policy = policy or _load_json(POLICY_PATH)
    _validate_policy(policy)
    if len(source_head) != 40 or any(ch not in "0123456789abcdef" for ch in source_head):
        raise BundleTransactionError("source_head must be a 40-character Git object ID")
    compiler = _load_component(COMPILER_PATH, "w64_bundle_compiler_for_s3_transaction")
    replay = compiler.replay_bundle(bundle, contract, decision, record_specs)
    if replay["replay_disposition"] != "MATCH":
        raise BundleTransactionError("EVIDENCE_BUNDLE_REPLAY_MISMATCH")
    records_by_hash: dict[str, Path] = {}
    for spec in record_specs:
        path = Path(spec["source_path"])
        digest = sha256_file(path)
        if digest in records_by_hash and records_by_hash[digest] != path:
            raise BundleTransactionError("duplicate content hash maps to multiple source paths")
        records_by_hash[digest] = path
    bundle_hashes = {record["content_sha256"] for record in bundle["records"]}
    if set(records_by_hash) != bundle_hashes:
        raise BundleTransactionError("record sources do not exactly match bundle objects")
    if len(bundle_hashes) > policy["max_objects"]:
        raise BundleTransactionError("S3_BUNDLE_OBJECT_COUNT_LIMIT_EXCEEDED")
    sizes = [path.stat().st_size for path in records_by_hash.values()]
    if any(size < 1 or size > policy["max_object_bytes"] for size in sizes):
        raise BundleTransactionError("S3_BUNDLE_OBJECT_SIZE_LIMIT_EXCEEDED")
    if sum(sizes) > policy["max_total_bytes"]:
        raise BundleTransactionError("S3_BUNDLE_TOTAL_SIZE_LIMIT_EXCEEDED")

    bucket = policy["bucket"]
    prefix = policy["key_prefix"]
    base = f"{prefix}/{bundle['bundle_id']}"
    object_receipts: list[dict[str, Any]] = []
    for index, digest in enumerate(sorted(bundle_hashes), start=1):
        key = f"{base}/objects/{digest}"
        object_receipts.append(_stage_one(client, bucket, key, records_by_hash[digest], digest, bundle["bundle_id"]))
        if inject_crash_after_objects == index:
            raise BundleTransactionError("INJECTED_CRASH_AFTER_OBJECT_STAGE")

    manifest_bytes = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    descriptor, name = tempfile.mkstemp(prefix="w64-aqa-bundle-", suffix=".json")
    manifest_path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(manifest_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        manifest_key = f"{base}/bundle.json"
        manifest_receipt = _stage_one(
            client, bucket, manifest_key, manifest_path, manifest_sha256, bundle["bundle_id"]
        )
    finally:
        manifest_path.unlink(missing_ok=True)

    created = sum(item["status"] == "CREATED_VERIFIED" for item in object_receipts) + (
        manifest_receipt["status"] == "CREATED_VERIFIED"
    )
    reused = len(object_receipts) + 1 - created
    receipt = {
        "schema_version": "wave64.aqa.s3_bundle_transaction_receipt.v1",
        "receipt_id": ZERO_HASH,
        "program_id": "W64-AQA",
        "source_head": source_head,
        "bundle_id": bundle["bundle_id"],
        "bucket": bucket,
        "key_prefix": prefix,
        "policy_sha256": hashlib.sha256(canonical_bytes(policy)).hexdigest(),
        "replay_disposition": "MATCH",
        "objects": object_receipts,
        "manifest": manifest_receipt,
        "created_object_count": int(created),
        "reused_object_count": int(reused),
        "manifest_written_last": True,
        "resume_safe": True,
        "overwrite_performed": False,
        "delete_performed": False,
        "rollback_disposition": "NONPUBLICATION_ONLY_CONTENT_ADDRESSED_OBJECTS_RETAINED",
        "s3_presence_is_acceptance": False,
        "product_promotion_granted": False,
        "disposition": "PASS_VERIFIED_RESUMABLE_S3_BUNDLE_STAGING_ONLY",
    }
    receipt["receipt_id"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    jsonschema.Draft7Validator(_load_json(RECEIPT_SCHEMA_PATH)).validate(receipt)
    return receipt


class AwsCliS3Client:
    """Exact AWS CLI adapter; credentials remain in the configured process environment."""

    def __init__(self, region: str) -> None:
        self.region = region

    def _run(self, args: list[str], *, allow_missing: bool = False, allow_precondition: bool = False) -> dict[str, Any] | None:
        completed = subprocess.run(
            ["aws", *args, "--region", self.region, "--output", "json"],
            check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if completed.returncode == 0:
            return json.loads(completed.stdout or "{}")
        stderr = completed.stderr or ""
        if allow_missing and ("Not Found" in stderr or "404" in stderr):
            return None
        if allow_precondition and ("PreconditionFailed" in stderr or "412" in stderr):
            return None
        raise BundleTransactionError("AWS_CLI_OPERATION_FAILED")

    def head(self, bucket: str, key: str) -> dict[str, Any] | None:
        return self._run(
            ["s3api", "head-object", "--bucket", bucket, "--key", key, "--checksum-mode", "ENABLED"],
            allow_missing=True,
        )

    def put_if_absent(self, bucket: str, key: str, source: Path, content_sha256: str, bundle_id: str) -> bool:
        digest = hashlib.sha256(source.read_bytes()).digest()
        checksum = __import__("base64").b64encode(digest).decode("ascii")
        result = self._run([
            "s3api", "put-object", "--bucket", bucket, "--key", key, "--body", str(source),
            "--if-none-match", "*", "--server-side-encryption", "AES256",
            "--checksum-algorithm", "SHA256", "--checksum-sha256", checksum,
            "--metadata", f"content-sha256={content_sha256},bundle-id={bundle_id},program-id=W64-AQA",
        ], allow_precondition=True)
        return result is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("decision", type=Path)
    parser.add_argument("records", type=Path)
    parser.add_argument("source_head")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        record_specs = json.loads(args.records.read_text(encoding="utf-8"))
        if not isinstance(record_specs, list):
            raise BundleTransactionError("records must be a JSON array")
        receipt = execute_bundle_transaction(
            _load_json(args.bundle), _load_json(args.contract), _load_json(args.decision),
            record_specs, AwsCliS3Client("us-east-1"), args.source_head,
        )
        rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise BundleTransactionError("receipt output already exists")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (BundleTransactionError, json.JSONDecodeError, jsonschema.ValidationError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
