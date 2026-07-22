#!/usr/bin/env python3
"""Validate the retained exact decord wheel metadata-repair receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RECEIPT_SHA256 = "b267a2c84e0e7876767b46a76680333a26b33a3d8debb8488871817e38505445"
REPAIRED_WHEEL_SHA256 = "7f966303534244867e2c7bb5640349465d6601139d393677a200c83d1e6f9cfa"


def validate(receipt: dict, receipt_path: Path) -> list[str]:
    errors: list[str] = []
    if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != RECEIPT_SHA256:
        errors.append("decord repair receipt hash mismatch")
    if receipt.get("status") != "DECORD_WHEEL_METADATA_REPAIRED_HASHED_INSTALL_IMPORT_PENDING":
        errors.append("decord repair status mismatch")
    repaired = receipt.get("repaired_wheel", {})
    if repaired.get("sha256") != REPAIRED_WHEEL_SHA256 or repaired.get("bytes") != 13583977:
        errors.append("repaired decord wheel identity mismatch")
    if repaired.get("changed_entries") != [
        "decord-0.6.0.dist-info/RECORD",
        "decord-0.6.0.dist-info/WHEEL",
    ]:
        errors.append("decord repair exceeded the two-entry boundary")
    if repaired.get("record_integrity") != "PASS":
        errors.append("repaired decord RECORD integrity missing")
    if repaired.get("binary_sha256") != "98b260c5812106648ba299279916fbe98439893e346d4efdcf5cde66ba8973da":
        errors.append("decord shared-library bytes changed")
    if receipt.get("wheelhouse_tree") != {
        "file_count": 1,
        "sha256": "b710baa95bbc1584e45abebb037a2194249b44b375dddf5ef85aebf6f22d6efc",
        "total_bytes": 13583977,
    }:
        errors.append("repaired decord wheelhouse tree mismatch")
    if any(receipt.get("runtime_claims", {}).values()):
        errors.append("decord repair receipt exceeds non-runtime authority")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    errors = validate(receipt, args.receipt)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_DECORD_WHEEL_REPAIR_RECEIPT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
