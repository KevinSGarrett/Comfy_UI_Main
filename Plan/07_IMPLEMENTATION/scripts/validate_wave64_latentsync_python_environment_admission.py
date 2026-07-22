#!/usr/bin/env python3
"""Validate the LatentSync isolated dependency-environment admission."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse


LOCK_SHA256 = "fcda64087e19f7a23106b6b1d93bfc99ee7928a8c5516dd9815f4acbc04b599e"
EXPECTED_HOSTS = {"files.pythonhosted.org", "download-r2.pytorch.org"}
EXPECTED_LOCAL_WHEELS = {
    "decord": (
        "decord-0.6.0-py3-none-manylinux2010_x86_64.whl",
        13583977,
        "7f966303534244867e2c7bb5640349465d6601139d393677a200c83d1e6f9cfa",
    ),
    "antlr4-python3-runtime": (
        "antlr4_python3_runtime-4.9.3-py3-none-any.whl",
        144589,
        "33b8ef731ab54955e6a77eaca700428b2829a1ffe2cd31e797ad23c6ea9fd93e",
    ),
    "insightface": (
        "insightface-0.7.3-cp311-cp311-linux_x86_64.whl",
        1065080,
        "605ffbee47d29222ead2308db3fd705a11dca4248ac761ff5216d0098a9d92df",
    ),
    "python-speech-features": (
        "python_speech_features-0.6-py3-none-any.whl",
        5891,
        "7c754cba8f6d46e8eff77014cd179e4ffd1b141772b0113e925eee45c63f3a05",
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(admission: dict, lock: dict, lock_path: Path) -> list[str]:
    errors: list[str] = []
    resolution = admission.get("resolution", {})
    authority = admission.get("authority", {})
    packages = lock.get("packages", [])
    if admission.get("status") != "DEPENDENCY_ENVIRONMENT_BUILD_ADMITTED_EXECUTION_PENDING":
        errors.append("environment admission status mismatch")
    if sha256_file(lock_path) != LOCK_SHA256 or resolution.get("lock_sha256") != LOCK_SHA256:
        errors.append("runtime lock hash mismatch")
    if lock.get("lock-version") != "1.0" or lock.get("created-by") != "uv":
        errors.append("runtime lock header mismatch")
    if lock.get("requires-python") != ">=3.11.10":
        errors.append("runtime lock Python requirement mismatch")
    if len(packages) != 149 or resolution.get("package_count") != 149:
        errors.append("runtime package count mismatch")

    names: set[str] = set()
    wheel_count = 0
    sdist_count = 0
    remote_hosts: set[str] = set()
    local_artifacts: dict[str, tuple[str, int, str]] = {}
    for package in packages:
        name = package.get("name")
        if not isinstance(name, str) or name in names:
            errors.append("runtime package identity is missing or duplicated")
            continue
        names.add(name)
        wheels = package.get("wheels", [])
        if not wheels:
            errors.append(f"{name}: no selected wheel")
        wheel_count += len(wheels)
        sdist_count += int("sdist" in package)
        for wheel in wheels:
            parsed = urlparse(wheel.get("url", ""))
            digest = wheel.get("hashes", {}).get("sha256")
            size = wheel.get("size")
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"{name}: wheel hash missing")
            if parsed.scheme == "https":
                remote_hosts.add(parsed.hostname or "")
            elif parsed.scheme == "file":
                if not isinstance(size, int):
                    errors.append(f"{name}: local wheel size missing")
                else:
                    local_artifacts[name] = (Path(parsed.path).name, size, digest)
            else:
                errors.append(f"{name}: unsupported wheel URL scheme")
    if wheel_count != 155 or resolution.get("wheel_count") != 155:
        errors.append("runtime wheel count mismatch")
    if sdist_count != 126 or resolution.get("sdist_count") != 126:
        errors.append("runtime sdist count mismatch")
    if remote_hosts != EXPECTED_HOSTS:
        errors.append("runtime wheel host allowlist mismatch")
    if local_artifacts != EXPECTED_LOCAL_WHEELS:
        errors.append("local wheel identity set mismatch")

    admitted_local = {
        item.get("name"): (item.get("filename"), item.get("bytes"), item.get("sha256"))
        for item in admission.get("local_wheelhouse", {}).get("wheels", [])
    }
    repaired_wheel = admission.get("repaired_wheelhouse", {}).get("wheel", {})
    admitted_local[repaired_wheel.get("name")] = (
        repaired_wheel.get("filename"),
        repaired_wheel.get("bytes"),
        repaired_wheel.get("sha256"),
    )
    if admitted_local != EXPECTED_LOCAL_WHEELS:
        errors.append("admission local wheel identity mismatch")
    if admission.get("base_python") != {
        "executable": "/usr/bin/python3",
        "sha256": "45c68b7ca1e3765a06756734c15af204ca9c0588a3f6d7a6d8bb8ed58e3e2a1a",
        "install_allowed": False,
    }:
        errors.append("base Python identity mismatch")
    if resolution.get("python_version") != "3.11.10" or resolution.get("uv_version") != "0.11.30":
        errors.append("Python or uv identity mismatch")
    targets = admission.get("targets", {})
    if targets.get("active_comfyui_environment_mutable") is not False:
        errors.append("active ComfyUI environment must remain immutable")
    if targets.get("global_python_environment_mutable") is not False:
        errors.append("global Python environment must remain immutable")
    allowed_true = {"environment_create", "locked_wheel_install"}
    if any(authority.get(name) is not True for name in allowed_true):
        errors.append("required dependency-build authority missing")
    if any(authority.get(name) is not False for name in set(authority) - allowed_true):
        errors.append("dependency build admission exceeds non-runtime authority")
    if admission.get("network", {}).get("allowed_hosts") != [
        "files.pythonhosted.org",
        "download-r2.pytorch.org",
    ]:
        errors.append("admission network allowlist mismatch")
    if admission.get("network", {}).get("model_download_allowed") is not False:
        errors.append("model download must remain forbidden")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("admission", type=Path)
    parser.add_argument("lock", type=Path)
    args = parser.parse_args()
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    lock = tomllib.loads(args.lock.read_text(encoding="utf-8"))
    errors = validate(admission, lock, args.lock)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_PYTHON_ENVIRONMENT_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
