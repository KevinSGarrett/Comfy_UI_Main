#!/usr/bin/env python3
"""Validate the storage-only Qwen3-Omni Thinking install admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


REPOSITORY = "Qwen/Qwen3-Omni-30B-A3B-Thinking"
REVISION = "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b"
TARGET_ROOT = f"/workspace/w64_aqa/models/Qwen3-Omni-30B-A3B-Thinking/{REVISION}"
CANONICAL_MANIFEST_SHA256 = "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480"
WEIGHT_BYTES = 63440997640
MINIMUM_FREE_BYTES = 79547125000
REQUIRED_FORBIDDEN = {
    "model_load",
    "inference",
    "gpu_probe",
    "lease_poll",
    "service_restart",
    "runtime_dependency_install",
    "role_activation",
    "audio_approval",
    "av_approval",
    "product_approval",
    "promotion",
    "migration",
    "current_pod_stop",
}


def canonical_sha256(data: dict) -> str:
    encoded = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if canonical_sha256(data) != CANONICAL_MANIFEST_SHA256:
        errors.append("canonical admission manifest identity mismatch")
    if data.get("schema_version") != "wave64.aqa.model_install_admission.v1":
        errors.append("schema version mismatch")
    if data.get("package_id") != "W64-AQA-PKG-QWEN3-OMNI-30B-A3B":
        errors.append("package identity mismatch")
    if data.get("status") != "STORAGE_INSTALL_ADMITTED_EXECUTION_PENDING":
        errors.append("status must remain execution pending")
    source = data.get("source", {})
    if source.get("repository_id") != REPOSITORY or source.get("revision") != REVISION:
        errors.append("source repository or revision mismatch")
    if (
        source.get("license") != "apache-2.0"
        or source.get("license_decision")
        != "ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE"
    ):
        errors.append("license admission mismatch")
    storage = data.get("storage", {})
    if storage.get("target_root") != TARGET_ROOT:
        errors.append("target root mismatch")
    if (
        storage.get("weight_bytes") != WEIGHT_BYTES
        or storage.get("minimum_free_bytes_before_install") != MINIMUM_FREE_BYTES
    ):
        errors.append("storage byte envelope mismatch")
    if (
        storage.get("atomic_publish") is not True
        or storage.get("overwrite_forbidden") is not True
    ):
        errors.append("storage publish controls must fail closed")

    files = data.get("files", [])
    paths: set[str] = set()
    weight_count = 0
    weight_bytes = 0
    for item in files:
        path = item.get("path", "")
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or path in paths:
            errors.append(f"unsafe or duplicate file path: {path}")
        paths.add(path)
        kind = item.get("identity_kind")
        identity = str(item.get("identity"))
        if kind == "sha256":
            weight_count += 1
            weight_bytes += item.get("bytes") or 0
            if re.fullmatch(r"[0-9a-f]{64}", identity) is None:
                errors.append(f"invalid SHA-256 identity: {path}")
        elif kind == "git_blob_sha1":
            if re.fullmatch(r"[0-9a-f]{40}", identity) is None:
                errors.append(f"invalid Git blob identity: {path}")
        else:
            errors.append(f"unsupported identity kind: {path}")
    if len(files) != 26 or len(paths) != 26 or weight_count != 16:
        errors.append("exact source file inventory shape mismatch")
    if weight_bytes != WEIGHT_BYTES:
        errors.append("weight byte sum mismatch")
    forbidden = set(data.get("authority", {}).get("forbidden", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        errors.append("forbidden runtime authority is incomplete")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors = validate(json.loads(args.manifest.read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_QWEN3_OMNI_INSTALL_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
