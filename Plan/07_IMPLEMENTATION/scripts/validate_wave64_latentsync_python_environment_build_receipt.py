#!/usr/bin/env python3
"""Validate the retained LatentSync isolated environment build receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


RECEIPT_SHA256 = "a13ba52cb63e871ada18550db06544fee51c58341d546edb276b3ecdf4c3f68e"
LOCK_SHA256 = "fcda64087e19f7a23106b6b1d93bfc99ee7928a8c5516dd9815f4acbc04b599e"
EXPECTED_TREE = {
    "regular_file_count": 41719,
    "sha256": "9e95a8d17cf8b38fb93b117327c9e68b68c4bfd5935cca81fb67fd6e1798028b",
    "symlink_count": 4,
    "total_regular_file_bytes": 7362946200,
}
EXPECTED_LOCAL_WHEEL_HASHES = {
    "33b8ef731ab54955e6a77eaca700428b2829a1ffe2cd31e797ad23c6ea9fd93e",
    "605ffbee47d29222ead2308db3fd705a11dca4248ac761ff5216d0098a9d92df",
    "7c754cba8f6d46e8eff77014cd179e4ffd1b141772b0113e925eee45c63f3a05",
    "7f966303534244867e2c7bb5640349465d6601139d393677a200c83d1e6f9cfa",
}


def normalized_name(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(".", "-")


def validate(receipt: dict, receipt_path: Path, lock: dict, lock_path: Path) -> list[str]:
    errors: list[str] = []
    if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != RECEIPT_SHA256:
        errors.append("LatentSync environment receipt hash mismatch")
    if hashlib.sha256(lock_path.read_bytes()).hexdigest() != LOCK_SHA256:
        errors.append("LatentSync runtime lock hash mismatch")
    if receipt.get("status") != "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING":
        errors.append("LatentSync environment build status mismatch")
    expected = {
        normalized_name(item["name"]): item["version"] for item in lock.get("packages", [])
    }
    observed = {
        normalized_name(item.get("name", "")): item.get("version")
        for item in receipt.get("distributions", [])
    }
    if len(expected) != 149 or len(observed) != 149 or observed != expected:
        errors.append("installed distribution manifest does not exactly match lock")
    if receipt.get("distribution_count") != 149:
        errors.append("installed distribution count mismatch")
    if receipt.get("pip_check") != "PASS_149_PACKAGES_COMPATIBLE":
        errors.append("installed dependency compatibility check missing")
    if receipt.get("environment_tree") != EXPECTED_TREE:
        errors.append("LatentSync environment tree digest mismatch")
    local_hashes = {item.get("sha256") for item in receipt.get("local_wheels", [])}
    if local_hashes != EXPECTED_LOCAL_WHEEL_HASHES:
        errors.append("installed local wheel identity set mismatch")
    active = receipt.get("active_environment", {})
    if active.get("unchanged") is not True or active.get("metadata_signature_before") != active.get(
        "metadata_signature_after"
    ):
        errors.append("active Python environment changed")
    storage = receipt.get("storage_authority", {})
    if storage.get("logical_filesystem_free_bytes_is_billing_quota_authority") is not False:
        errors.append("receipt overstates logical filesystem storage authority")
    if any(receipt.get("runtime_claims", {}).values()):
        errors.append("environment build receipt contains a false runtime claim")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("lock", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    lock = tomllib.loads(args.lock.read_text(encoding="utf-8"))
    errors = validate(receipt, args.receipt, lock, args.lock)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_PYTHON_ENVIRONMENT_BUILD_RECEIPT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
