#!/usr/bin/env python3
"""Validate the retained Qwen3-Omni isolated environment build receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RECEIPT_SHA256 = "d89ec8ba5588e8ba07f76522c74bfbfe51284c55baf934ab7f4729fed298deb8"
EXPECTED_KEY_DISTRIBUTIONS = {
    "accelerate": "1.14.0",
    "av": "18.0.0",
    "qwen-omni-utils": "0.0.9",
    "torch": "2.4.1+cu124",
    "torchvision": "0.19.1+cu124",
    "transformers": "5.2.0",
}


def validate(receipt: dict, receipt_path: Path) -> list[str]:
    errors: list[str] = []
    if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != RECEIPT_SHA256:
        errors.append("Omni environment build receipt hash mismatch")
    if receipt.get("status") != "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING":
        errors.append("Omni environment build status mismatch")
    distributions = receipt.get("distributions", [])
    observed: dict[str, str] = {}
    for item in distributions:
        name = str(item.get("name", "")).lower()
        version = item.get("version")
        if not name or not isinstance(version, str) or name in observed:
            errors.append("installed distribution identity is missing or duplicated")
            continue
        observed[name] = version
    if len(distributions) != 75 or receipt.get("distribution_count") != 75:
        errors.append("installed distribution count mismatch")
    if "decord" in observed:
        errors.append("incompatible Decord distribution is installed")
    for name, version in EXPECTED_KEY_DISTRIBUTIONS.items():
        if observed.get(name) != version:
            errors.append(f"{name}: installed version mismatch")
    if receipt.get("pip_check") != "PASS_75_PACKAGES_COMPATIBLE":
        errors.append("installed dependency compatibility check missing")
    tree = receipt.get("environment_tree", {})
    if tree.get("sha256") != "2ae7708993cab848861688ae1b89a2233d61fa02b49e1c14bf51b188a2dd59c5":
        errors.append("environment tree digest mismatch")
    active = receipt.get("active_environment", {})
    if active.get("unchanged") is not True or active.get("metadata_signature_before") != active.get(
        "metadata_signature_after"
    ):
        errors.append("active Python environment changed")
    if any(receipt.get("runtime_claims", {}).values()):
        errors.append("environment build receipt contains a false runtime claim")
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
    print("W64_AQA_QWEN3_OMNI_PYTHON_ENVIRONMENT_BUILD_RECEIPT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
