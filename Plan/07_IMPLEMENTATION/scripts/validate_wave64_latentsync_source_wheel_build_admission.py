#!/usr/bin/env python3
"""Validate the admitted LatentSync source-wheel build boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse


EXPECTED_BUILDER_LOCK_SHA256 = "06610318056d7345485f7623316882c20fbd07913aa05f28aa6ef79458db16a7"
EXPECTED_SOURCE_LOCK_SHA256 = "ac29c11ced5d4be9b22ff4c0fcec9a9d48361d9dfcb1996bf2fdd2a8526b9605"
EXPECTED_BUILDER_PACKAGES = {
    "cython": "3.2.8",
    "numpy": "1.26.4",
    "packaging": "26.2",
    "pip": "26.1.2",
    "setuptools": "83.0.0",
    "wheel": "0.46.3",
}
EXPECTED_SOURCES = {
    "antlr4-python3-runtime": (
        "4.9.3",
        "f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b",
    ),
    "insightface": (
        "0.7.3",
        "f191f719612ebb37018f41936814500544cd0f86e6fcd676c023f354c668ddf7",
    ),
    "python-speech-features": (
        "0.6",
        "a0aebf746464bc929dc3162cb369d7ff967c398c5120ddf5fb40a65f01b92b11",
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(admission: dict, builder_lock: dict, builder_lock_path: Path) -> list[str]:
    errors: list[str] = []
    if admission.get("status") != "SOURCE_WHEEL_BUILD_ADMITTED_EXECUTION_PENDING":
        errors.append("source-wheel build admission status mismatch")
    if sha256_file(builder_lock_path) != EXPECTED_BUILDER_LOCK_SHA256:
        errors.append("builder lock hash mismatch")
    if admission.get("builder", {}).get("lock_sha256") != EXPECTED_BUILDER_LOCK_SHA256:
        errors.append("admission builder lock binding mismatch")
    if admission.get("source_dependency_lock", {}).get("sha256") != EXPECTED_SOURCE_LOCK_SHA256:
        errors.append("source dependency lock binding mismatch")
    if builder_lock.get("lock-version") != "1.0" or builder_lock.get("created-by") != "uv":
        errors.append("builder lock header mismatch")
    if builder_lock.get("requires-python") != ">=3.11.10":
        errors.append("builder Python requirement mismatch")

    packages = builder_lock.get("packages", [])
    observed: dict[str, str] = {}
    hosts: set[str] = set()
    wheel_count = 0
    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str) or name in observed:
            errors.append("builder package identity is missing or duplicated")
            continue
        observed[name] = version
        wheels = package.get("wheels", [])
        if not wheels:
            errors.append(f"{name}: builder package has no wheel")
        wheel_count += len(wheels)
        for wheel in wheels:
            parsed = urlparse(wheel.get("url", ""))
            hosts.add(parsed.hostname or "")
            digest = wheel.get("hashes", {}).get("sha256")
            if parsed.scheme != "https" or not parsed.hostname:
                errors.append(f"{name}: builder wheel URL must use HTTPS")
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"{name}: builder wheel SHA-256 missing")
    if observed != EXPECTED_BUILDER_PACKAGES:
        errors.append("builder package set mismatch")
    if wheel_count != 7 or admission.get("builder", {}).get("wheel_entry_count") != 7:
        errors.append("builder wheel count mismatch")
    if hosts != {"files.pythonhosted.org"}:
        errors.append("builder host allowlist mismatch")

    sources = {
        source.get("name"): (source.get("version"), source.get("sha256"))
        for source in admission.get("sources", [])
    }
    if sources != EXPECTED_SOURCES:
        errors.append("source distribution set or hash mismatch")
    for source in admission.get("sources", []):
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
            errors.append("source distribution host is not admitted")

    authority = admission.get("authority", {})
    allowed_true = {
        "exact_sdist_download",
        "isolated_builder_create",
        "exact_sdist_build_execution",
        "wheel_publish",
    }
    if any(authority.get(key) is not True for key in allowed_true):
        errors.append("required source-wheel build authority missing")
    if any(value is not False for key, value in authority.items() if key not in allowed_true):
        errors.append("source-wheel admission exceeds build authority")
    if admission.get("targets", {}).get("active_comfyui_environment_mutable") is not False:
        errors.append("active ComfyUI environment must remain immutable")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("admission", type=Path)
    parser.add_argument("builder_lock", type=Path)
    args = parser.parse_args()
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    builder_lock = tomllib.loads(args.builder_lock.read_text(encoding="utf-8"))
    errors = validate(admission, builder_lock, args.builder_lock)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_SOURCE_WHEEL_BUILD_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
