#!/usr/bin/env python3
"""Validate the exact LatentSync decord wheel metadata-repair admission."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


SOURCE_SHA256 = "51997f20be8958e23b7c4061ba45d0efcd86bffd5fe81c695d0befee0d442976"
ALLOWED_TRUE = {
    "exact_wheel_download",
    "wheel_metadata_retag",
    "record_regeneration",
    "repaired_wheel_publish",
}


def validate(admission: dict) -> list[str]:
    errors: list[str] = []
    source = admission.get("source", {})
    repair = admission.get("repair", {})
    targets = admission.get("targets", {})
    authority = admission.get("authority", {})
    if admission.get("status") != "DECORD_WHEEL_METADATA_REPAIR_ADMITTED_EXECUTION_PENDING":
        errors.append("wheel repair admission status mismatch")
    parsed = urlparse(source.get("url", ""))
    if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
        errors.append("wheel source is outside the exact network boundary")
    if source.get("sha256") != SOURCE_SHA256 or source.get("bytes") != 13602299:
        errors.append("source wheel identity mismatch")
    if source.get("observed_internal_tag") != "cp36-cp36m-manylinux2010_x86_64":
        errors.append("source wheel defect identity mismatch")
    if repair.get("replacement_internal_tag") != "py3-none-manylinux2010_x86_64":
        errors.append("replacement wheel tag mismatch")
    if repair.get("allowed_changed_entries") != [
        "decord-0.6.0.dist-info/WHEEL",
        "decord-0.6.0.dist-info/RECORD",
    ]:
        errors.append("wheel repair change boundary mismatch")
    wheelhouse = targets.get("wheelhouse_root", "")
    if not wheelhouse.startswith("/workspace/w64_aqa/wheelhouse/LatentSync-1.6/"):
        errors.append("unsafe repaired wheel target")
    if not targets.get("receipt_path", "").startswith("/workspace/w64_aqa/control/receipts/"):
        errors.append("unsafe repaired wheel receipt target")
    if any(authority.get(name) is not True for name in ALLOWED_TRUE):
        errors.append("required wheel repair authority missing")
    if any(value is not False for name, value in authority.items() if name not in ALLOWED_TRUE):
        errors.append("wheel repair admission exceeds non-runtime authority")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("admission", type=Path)
    args = parser.parse_args()
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    errors = validate(admission)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_DECORD_WHEEL_REPAIR_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
