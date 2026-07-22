#!/usr/bin/env python3
"""Validate the retained LatentSync source-wheel build receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_RECEIPT_SHA256 = "3865d6576e1795b9d080175fdec9c4fba5374e5bc7ad3ec787129aef6ab89df7"
EXPECTED_BUILDER = {
    "cython": "3.2.8",
    "numpy": "1.26.4",
    "packaging": "26.2",
    "pip": "26.1.2",
    "setuptools": "83.0.0",
    "wheel": "0.46.3",
}
EXPECTED_SOURCES = {
    "antlr4-python3-runtime": ("4.9.3", "f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b"),
    "insightface": ("0.7.3", "f191f719612ebb37018f41936814500544cd0f86e6fcd676c023f354c668ddf7"),
    "python-speech-features": ("0.6", "a0aebf746464bc929dc3162cb369d7ff967c398c5120ddf5fb40a65f01b92b11"),
}
EXPECTED_WHEELS = {
    "antlr4-python3-runtime": ("4.9.3", "33b8ef731ab54955e6a77eaca700428b2829a1ffe2cd31e797ad23c6ea9fd93e"),
    "insightface": ("0.7.3", "605ffbee47d29222ead2308db3fd705a11dca4248ac761ff5216d0098a9d92df"),
    "python-speech-features": ("0.6", "7c754cba8f6d46e8eff77014cd179e4ffd1b141772b0113e925eee45c63f3a05"),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(receipt: dict, receipt_path: Path) -> list[str]:
    errors: list[str] = []
    if sha256_file(receipt_path) != EXPECTED_RECEIPT_SHA256:
        errors.append("source-wheel receipt hash mismatch")
    if receipt.get("status") != "SOURCE_WHEELS_BUILT_HASHED_METADATA_VERIFIED_RUNTIME_INSTALL_PENDING":
        errors.append("source-wheel receipt status mismatch")
    builder = {row.get("name"): row.get("version") for row in receipt.get("builder", {}).get("distributions", [])}
    if builder != EXPECTED_BUILDER or receipt.get("builder", {}).get("pip_check") != "PASS_6_PACKAGES_COMPATIBLE":
        errors.append("isolated builder manifest mismatch")
    sources = {row.get("name"): (row.get("version"), row.get("sha256")) for row in receipt.get("sources", [])}
    if sources != EXPECTED_SOURCES:
        errors.append("source manifest mismatch")
    wheels = {row.get("name"): (row.get("version"), row.get("sha256")) for row in receipt.get("wheels", [])}
    if wheels != EXPECTED_WHEELS:
        errors.append("wheel manifest mismatch")
    for wheel in receipt.get("wheels", []):
        if wheel.get("record_present") is not True or wheel.get("symlink_count") != 0:
            errors.append("wheel archive safety metadata mismatch")
    for audit in receipt.get("static_audits", []):
        if audit.get("static_findings") != [] or audit.get("root_setup_script") != "setup.py":
            errors.append("source static audit mismatch")
    tree = receipt.get("wheelhouse_tree", {})
    if tree != {"file_count": 3, "sha256": "139140835f9e003c87187ee9d1f81edd458474ffb00c128fb3d844b505680ff6", "total_bytes": 1215560}:
        errors.append("wheelhouse tree mismatch")
    active = receipt.get("active_environment", {})
    if active.get("unchanged") is not True or active.get("metadata_signature_before") != active.get("metadata_signature_after"):
        errors.append("active environment mutation detected")
    claims = receipt.get("runtime_claims", {})
    if any(value is not False for value in claims.values()):
        errors.append("source-wheel receipt exceeds non-runtime authority")
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
    print("W64_AQA_LATENTSYNC_SOURCE_WHEEL_BUILD_RECEIPT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
