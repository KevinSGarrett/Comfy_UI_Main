#!/usr/bin/env python3
"""Validate the retained Qwen3-ASR isolated environment build receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RECEIPT_SHA256 = "e09c67aee503f511124b50af539067c9f82f1969490ab9b7d5127d9870c9dcd4"
EXPECTED_KEY_DISTRIBUTIONS = {
    "accelerate": "1.12.0",
    "librosa": "0.11.0",
    "qwen-asr": "0.0.6",
    "qwen-omni-utils": "0.0.9",
    "soundfile": "0.14.0",
    "torch": "2.4.1+cu124",
    "transformers": "4.57.6",
}


def validate(receipt: dict, receipt_path: Path) -> list[str]:
    errors: list[str] = []
    if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != RECEIPT_SHA256:
        errors.append("environment build receipt hash mismatch")
    if receipt.get("status") != "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING":
        errors.append("environment build status mismatch")
    distributions = receipt.get("distributions", [])
    observed: dict[str, str] = {}
    for item in distributions:
        name = str(item.get("name", "")).lower()
        version = item.get("version")
        if not name or not isinstance(version, str) or name in observed:
            errors.append("installed distribution identity is missing or duplicated")
            continue
        observed[name] = version
    if len(distributions) != 105 or receipt.get("distribution_count") != 105:
        errors.append("installed distribution count mismatch")
    for name, version in EXPECTED_KEY_DISTRIBUTIONS.items():
        if observed.get(name) != version:
            errors.append(f"{name}: installed version mismatch")
    if receipt.get("pip_check") != "PASS_105_PACKAGES_COMPATIBLE":
        errors.append("installed dependency compatibility check missing")
    tree = receipt.get("environment_tree", {})
    if tree.get("sha256") != "6625aa3c76c411424ede40ce6275d0fb378a1d9a017c205f74ffd356386f7c4a":
        errors.append("environment tree digest mismatch")
    correction = receipt.get("verification_command_correction", {})
    if correction.get("corrected_stdin_metadata_check") != "PASS":
        errors.append("corrected metadata verification did not pass")
    if correction.get("installed_bytes_changed_by_correction") is not False:
        errors.append("verification correction cannot mutate installed bytes")
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
    print("W64_AQA_PYTHON_ENVIRONMENT_BUILD_RECEIPT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
