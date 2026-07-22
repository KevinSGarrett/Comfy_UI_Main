#!/usr/bin/env python3
"""Validate the exact LatentSync 1.6 dependency lock and evidence boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse


EXPECTED_LOCK_SHA256 = "ac29c11ced5d4be9b22ff4c0fcec9a9d48361d9dfcb1996bf2fdd2a8526b9605"
EXPECTED_HOSTS = {
    "download-r2.pytorch.org",
    "files.pythonhosted.org",
}
EXPECTED_KEY_PACKAGES = {
    "diffusers": "0.32.2",
    "insightface": "0.7.3",
    "numpy": "1.26.4",
    "onnxruntime-gpu": "1.21.0",
    "python-speech-features": "0.6",
    "torch": "2.5.1+cu121",
    "torchvision": "0.20.1+cu121",
    "transformers": "4.48.0",
}
EXPECTED_SDIST_ONLY = {
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


def validate(evidence: dict, lock: dict, lock_path: Path) -> list[str]:
    errors: list[str] = []
    packages = lock.get("packages", [])
    if sha256_file(lock_path) != EXPECTED_LOCK_SHA256:
        errors.append("dependency lock hash mismatch")
    if evidence.get("lock", {}).get("sha256") != EXPECTED_LOCK_SHA256:
        errors.append("evidence lock hash mismatch")
    if lock.get("lock-version") != "1.0" or lock.get("created-by") != "uv":
        errors.append("dependency lock header mismatch")
    if lock.get("requires-python") != ">=3.11.10":
        errors.append("dependency lock Python requirement mismatch")
    if len(packages) != 149 or evidence.get("lock", {}).get("package_count") != 149:
        errors.append("dependency package count mismatch")

    names: dict[str, str] = {}
    hosts: set[str] = set()
    wheel_count = 0
    sdist_count = 0
    sdist_only: dict[str, tuple[str, str]] = {}
    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str) or name in names:
            errors.append("dependency package identity is missing or duplicated")
            continue
        names[name] = version
        wheels = package.get("wheels", [])
        wheel_count += len(wheels)
        artifacts = list(wheels)
        sdist = package.get("sdist")
        if sdist is not None:
            sdist_count += 1
            artifacts.append(sdist)
        if not wheels:
            if not isinstance(sdist, dict):
                errors.append(f"{name}: no wheel or sdist artifact")
            else:
                sdist_only[name] = (version, sdist.get("hashes", {}).get("sha256", ""))
        for artifact in artifacts:
            parsed = urlparse(artifact.get("url", ""))
            hosts.add(parsed.hostname or "")
            digest = artifact.get("hashes", {}).get("sha256")
            if parsed.scheme != "https" or not parsed.hostname:
                errors.append(f"{name}: artifact URL must use HTTPS")
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"{name}: artifact SHA-256 missing")

    if wheel_count != 152 or evidence.get("lock", {}).get("wheel_entry_count") != 152:
        errors.append("dependency wheel entry count mismatch")
    if sdist_count != 129 or evidence.get("lock", {}).get("sdist_entry_count") != 129:
        errors.append("dependency sdist entry count mismatch")
    if hosts != EXPECTED_HOSTS:
        errors.append("dependency artifact host allowlist mismatch")
    if sdist_only != EXPECTED_SDIST_ONLY:
        errors.append("source-only package set or hash mismatch")
    for name, version in EXPECTED_KEY_PACKAGES.items():
        if names.get(name) != version:
            errors.append(f"{name}: required version mismatch")

    claims = evidence.get("execution_claims", {})
    if any(claims.get(key) is not False for key in claims):
        errors.append("lock evidence exceeds non-execution authority")
    gate = evidence.get("source_wheel_gate", {})
    if gate.get("runtime_install_admitted") is not False:
        errors.append("source-wheel gate must block runtime install")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("lock", type=Path)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    lock = tomllib.loads(args.lock.read_text(encoding="utf-8"))
    errors = validate(evidence, lock, args.lock)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_DEPENDENCY_LOCK_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
