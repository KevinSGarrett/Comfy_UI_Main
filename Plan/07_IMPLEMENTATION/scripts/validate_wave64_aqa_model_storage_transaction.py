#!/usr/bin/env python3
"""Validate a fail-closed W64-AQA model storage transaction plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
TRANSACTION_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_flux2_klein_companion_storage_transaction.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_model_storage_transaction.schema.json")


class StorageTransactionError(ValueError):
    """Raised when a transaction drifts or becomes prematurely executable."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StorageTransactionError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_id(value: dict[str, Any]) -> str:
    candidate = json.loads(json.dumps(value))
    candidate["transaction_id"] = "0" * 64
    data = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def validate_transaction(root: Path, value: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["transaction_id"] != content_id(value):
        raise StorageTransactionError("storage transaction identity drift")
    dependency_binding = value["dependency_bundle"]
    dependency_path = root / Path(dependency_binding["path"])
    if sha256_file(dependency_path) != dependency_binding["sha256"]:
        raise StorageTransactionError("dependency bundle hash drift")
    dependency = load_json(dependency_path)
    if dependency.get("bundle_id") != dependency_binding["id"]:
        raise StorageTransactionError("dependency bundle id drift")
    expected = {
        component["role"]: (component["bytes"], component["sha256"], component["current_pod_path"])
        for component in dependency["components"] if component["role"] in {"text_encoder", "vae"}
    }
    observed = {item["role"]: (item["bytes"], item["sha256"], item["target_path"]) for item in value["files"]}
    if observed != expected:
        raise StorageTransactionError("transaction file identity drift")
    total = sum(item["bytes"] for item in value["files"])
    storage = value["storage_gate"]
    if total != storage["total_promotion_bytes"]:
        raise StorageTransactionError("promotion byte total drift")
    if total + storage["minimum_post_promotion_reserve_bytes"] != storage["minimum_verified_free_before_bytes"]:
        raise StorageTransactionError("reserve arithmetic drift")
    staging = [item["staging_path"] for item in value["files"]]
    targets = [item["target_path"] for item in value["files"]]
    if len(set(staging)) != 2 or len(set(targets)) != 2 or any(path in targets for path in staging):
        raise StorageTransactionError("staging or target collision")
    text_encoder = next(item for item in value["files"] if item["role"] == "text_encoder")
    local_path = Path(text_encoder["source"]["path_or_uri"])
    if not local_path.is_file() or local_path.stat().st_size != text_encoder["bytes"]:
        raise StorageTransactionError("retained text encoder source size or presence drift")
    vae = next(item for item in value["files"] if item["role"] == "vae")
    if vae["source"]["local_bytes_verified"] or vae["source"]["state"] != "EXACT_REMOTE_IDENTITY_ACQUISITION_PENDING":
        raise StorageTransactionError("missing Klein VAE was falsely marked local")
    if value["executable"] or any(value["authority"][key] for key in ("acquisition", "storage_mutation", "runtime", "activation", "promotion")):
        raise StorageTransactionError("prepared transaction gained unsupported authority")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--transaction", type=Path, default=TRANSACTION_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.transaction if args.transaction.is_absolute() else root / args.transaction
    value = load_json(path)
    validate_transaction(root, value)
    print(json.dumps({"status": "PASS", "transaction_id": value["transaction_id"], "executable": value["executable"], "blocker_count": len(value["blockers"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
