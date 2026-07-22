#!/usr/bin/env python3
"""Validate the wheel-complete LatentSync runtime lock derivation."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tomllib
from urllib.parse import urlparse


EXPECTED_SOURCE_SHA256 = "ac29c11ced5d4be9b22ff4c0fcec9a9d48361d9dfcb1996bf2fdd2a8526b9605"
EXPECTED_RUNTIME_SHA256 = "862e85d3cbb3a1dd9a90dd9541bff24b20ae997c95326f9331b9e466dc6b40ff"
EXPECTED_LOCAL_WHEELS = {
    "antlr4-python3-runtime": (
        "33b8ef731ab54955e6a77eaca700428b2829a1ffe2cd31e797ad23c6ea9fd93e",
        144589,
    ),
    "insightface": (
        "605ffbee47d29222ead2308db3fd705a11dca4248ac761ff5216d0098a9d92df",
        1065080,
    ),
    "python-speech-features": (
        "7c754cba8f6d46e8eff77014cd179e4ffd1b141772b0113e925eee45c63f3a05",
        5891,
    ),
}
LOCAL_PREFIX = "/workspace/w64_aqa/wheelhouse/LatentSync-1.6/"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(source: dict, runtime: dict, source_path: Path, runtime_path: Path) -> list[str]:
    errors: list[str] = []
    if sha256_file(source_path) != EXPECTED_SOURCE_SHA256:
        errors.append("source dependency lock hash mismatch")
    if sha256_file(runtime_path) != EXPECTED_RUNTIME_SHA256:
        errors.append("runtime dependency lock hash mismatch")
    if runtime.get("lock-version") != "1.0" or runtime.get("created-by") != "uv":
        errors.append("runtime lock header mismatch")
    if runtime.get("requires-python") != ">=3.11.10":
        errors.append("runtime lock Python requirement mismatch")

    source_packages = {item.get("name"): item for item in source.get("packages", [])}
    runtime_packages = {item.get("name"): item for item in runtime.get("packages", [])}
    if len(source_packages) != 149 or len(runtime_packages) != 149:
        errors.append("runtime lock package count mismatch")
    if set(source_packages) != set(runtime_packages):
        errors.append("runtime lock package identity set mismatch")

    for name in sorted(set(source_packages) & set(runtime_packages)):
        original = source_packages[name]
        derived = runtime_packages[name]
        if name not in EXPECTED_LOCAL_WHEELS:
            if original != derived:
                errors.append(f"{name}: non-source-only package changed")
            continue
        original_identity = {key: value for key, value in original.items() if key not in {"sdist", "wheels"}}
        derived_identity = {key: value for key, value in derived.items() if key not in {"sdist", "wheels"}}
        if original_identity != derived_identity or original.get("wheels"):
            errors.append(f"{name}: package identity changed beyond artifact substitution")
        wheels = derived.get("wheels", [])
        if "sdist" in derived or len(wheels) != 1:
            errors.append(f"{name}: runtime artifact must be one local wheel")
            continue
        wheel = wheels[0]
        parsed = urlparse(wheel.get("url", ""))
        expected_hash, expected_size = EXPECTED_LOCAL_WHEELS[name]
        if parsed.scheme != "file" or not parsed.path.startswith(LOCAL_PREFIX):
            errors.append(f"{name}: local wheel path is outside the admitted wheelhouse")
        if wheel.get("hashes", {}).get("sha256") != expected_hash or wheel.get("size") != expected_size:
            errors.append(f"{name}: local wheel hash or size mismatch")

    wheel_count = 0
    sdist_count = 0
    for package in runtime_packages.values():
        wheels = package.get("wheels", [])
        if not wheels:
            errors.append(f"{package.get('name')}: runtime lock has no wheel")
        wheel_count += len(wheels)
        sdist_count += int("sdist" in package)
        for artifact in list(wheels) + ([package["sdist"]] if "sdist" in package else []):
            digest = artifact.get("hashes", {}).get("sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"{package.get('name')}: artifact SHA-256 missing")
    if wheel_count != 155 or sdist_count != 126:
        errors.append("runtime lock artifact counts mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_lock", type=Path)
    parser.add_argument("runtime_lock", type=Path)
    args = parser.parse_args()
    source = tomllib.loads(args.source_lock.read_text(encoding="utf-8"))
    runtime = tomllib.loads(args.runtime_lock.read_text(encoding="utf-8"))
    errors = validate(source, runtime, args.source_lock, args.runtime_lock)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_RUNTIME_LOCK_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
