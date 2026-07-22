#!/usr/bin/env python3
"""Validate a storage-only, non-runtime W64-AQA model install admission."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath


REVISION = "7278e1e70fe206f11671096ffdd38061171dd6e5"
TARGET_ROOT = f"/workspace/w64_aqa/models/Qwen3-ASR-1.7B/{REVISION}"
FILES = {
    ".gitattributes": ("git_blob_sha1", "a6344aac8c09253b3b630fb776ae94478aa0275b", None),
    "README.md": ("git_blob_sha1", "3a67d43f21febda213ff36efdb60ef10019af7f3", None),
    "chat_template.json": ("git_blob_sha1", "c44736493efd71ec96218cc626904698cdb13235", None),
    "config.json": ("git_blob_sha1", "2bc16c9d4ca08963715cfb94d879799b9adbd0e9", None),
    "generation_config.json": ("git_blob_sha1", "7382a4d347c0a865b76bb1b8277f66a5ac312854", None),
    "merges.txt": ("git_blob_sha1", "31349551d90c7606f325fe0f11bbb8bd5fa0d7c7", None),
    "model-00001-of-00002.safetensors": ("sha256", "a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6", 4220320824),
    "model-00002-of-00002.safetensors": ("sha256", "6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc", 478200688),
    "model.safetensors.index.json": ("git_blob_sha1", "1048a4eb4f21fef9aea06d8568a784b2b5595689", None),
    "preprocessor_config.json": ("git_blob_sha1", "8f7f07346466d5d494ec0d4969d1c3d0190eed72", None),
    "tokenizer_config.json": ("git_blob_sha1", "b93109843922a40c6654c5449d3bf95372267c66", None),
    "vocab.json": ("git_blob_sha1", "4783fe10ac3adce15ac8f358ef5462739852c569", None),
}
REQUIRED_FORBIDDEN = {
    "model_load", "inference", "gpu_probe", "lease_poll", "service_restart",
    "runtime_dependency_install", "role_activation", "product_approval", "promotion",
    "migration", "current_pod_stop",
}


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "wave64.aqa.model_install_admission.v1":
        errors.append("schema version mismatch")
    if data.get("status") != "STORAGE_INSTALL_ADMITTED_EXECUTION_PENDING":
        errors.append("status must remain execution pending")
    source = data.get("source", {})
    if source.get("repository_id") != "Qwen/Qwen3-ASR-1.7B" or source.get("revision") != REVISION:
        errors.append("source repository or revision mismatch")
    if source.get("license") != "apache-2.0" or source.get("license_decision") != "ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
        errors.append("license admission mismatch")
    storage = data.get("storage", {})
    if storage.get("target_root") != TARGET_ROOT:
        errors.append("target root mismatch")
    if storage.get("weight_bytes") != 4698521512 or storage.get("minimum_free_bytes_before_install") != 15435939752:
        errors.append("storage byte envelope mismatch")
    if storage.get("atomic_publish") is not True or storage.get("overwrite_forbidden") is not True:
        errors.append("storage publish controls must fail closed")

    observed: dict[str, tuple[str, str, int | None]] = {}
    for item in data.get("files", []):
        path = item.get("path", "")
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or path in observed:
            errors.append(f"unsafe or duplicate file path: {path}")
            continue
        kind = item.get("identity_kind")
        identity = item.get("identity")
        if kind == "sha256" and re.fullmatch(r"[0-9a-f]{64}", str(identity)) is None:
            errors.append(f"invalid SHA-256 identity: {path}")
        if kind == "git_blob_sha1" and re.fullmatch(r"[0-9a-f]{40}", str(identity)) is None:
            errors.append(f"invalid Git blob identity: {path}")
        observed[path] = (kind, identity, item.get("bytes"))
    if observed != FILES:
        errors.append("exact source file inventory mismatch")
    if sum(item[2] or 0 for item in observed.values()) != 4698521512:
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
    print("W64_AQA_MODEL_INSTALL_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
