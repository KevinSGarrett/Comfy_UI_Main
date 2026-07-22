#!/usr/bin/env python3
"""Validate the LatentSync runtime lock with four accepted local wheels."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tomllib
from urllib.parse import urlparse


EXPECTED_V1_SHA256 = "862e85d3cbb3a1dd9a90dd9541bff24b20ae997c95326f9331b9e466dc6b40ff"
EXPECTED_V2_SHA256 = "fcda64087e19f7a23106b6b1d93bfc99ee7928a8c5516dd9815f4acbc04b599e"
EXPECTED_DECORD = {
    "filename": "decord-0.6.0-py3-none-manylinux2010_x86_64.whl",
    "bytes": 13583977,
    "sha256": "7f966303534244867e2c7bb5640349465d6601139d393677a200c83d1e6f9cfa",
}
EXPECTED_REMOTE_HOSTS = {"files.pythonhosted.org", "download-r2.pytorch.org"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(v1: dict, v2: dict, v1_path: Path, v2_path: Path) -> list[str]:
    errors: list[str] = []
    if sha256_file(v1_path) != EXPECTED_V1_SHA256:
        errors.append("v1 runtime lock hash mismatch")
    if sha256_file(v2_path) != EXPECTED_V2_SHA256:
        errors.append("v2 runtime lock hash mismatch")
    v1_packages = {item.get("name"): item for item in v1.get("packages", [])}
    v2_packages = {item.get("name"): item for item in v2.get("packages", [])}
    if len(v1_packages) != 149 or len(v2_packages) != 149 or set(v1_packages) != set(v2_packages):
        errors.append("v2 runtime package identity set mismatch")
    for name in sorted(set(v1_packages) & set(v2_packages)):
        before = v1_packages[name]
        after = v2_packages[name]
        if name != "decord":
            if before != after:
                errors.append(f"{name}: package changed outside decord repair")
            continue
        before_identity = {key: value for key, value in before.items() if key not in {"sdist", "wheels"}}
        after_identity = {key: value for key, value in after.items() if key not in {"sdist", "wheels"}}
        if before_identity != after_identity or "sdist" in after or len(after.get("wheels", [])) != 1:
            errors.append("decord package identity changed beyond wheel substitution")
            continue
        wheel = after["wheels"][0]
        parsed = urlparse(wheel.get("url", ""))
        if (
            parsed.scheme != "file"
            or Path(parsed.path).name != EXPECTED_DECORD["filename"]
            or wheel.get("size") != EXPECTED_DECORD["bytes"]
            or wheel.get("hashes", {}).get("sha256") != EXPECTED_DECORD["sha256"]
        ):
            errors.append("decord repaired wheel binding mismatch")

    wheel_count = 0
    sdist_count = 0
    local_count = 0
    remote_hosts: set[str] = set()
    for package in v2_packages.values():
        wheels = package.get("wheels", [])
        if not wheels:
            errors.append(f"{package.get('name')}: v2 runtime lock has no wheel")
        wheel_count += len(wheels)
        sdist_count += int("sdist" in package)
        for wheel in wheels:
            parsed = urlparse(wheel.get("url", ""))
            if parsed.scheme == "file":
                local_count += 1
            elif parsed.scheme == "https":
                remote_hosts.add(parsed.hostname or "")
            else:
                errors.append(f"{package.get('name')}: unsupported wheel URL scheme")
            digest = wheel.get("hashes", {}).get("sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"{package.get('name')}: wheel SHA-256 missing")
    if wheel_count != 155 or sdist_count != 126 or local_count != 4:
        errors.append("v2 runtime artifact counts mismatch")
    if remote_hosts != EXPECTED_REMOTE_HOSTS:
        errors.append("v2 remote wheel host allowlist mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("v1_lock", type=Path)
    parser.add_argument("v2_lock", type=Path)
    args = parser.parse_args()
    v1 = tomllib.loads(args.v1_lock.read_text(encoding="utf-8"))
    v2 = tomllib.loads(args.v2_lock.read_text(encoding="utf-8"))
    errors = validate(v1, v2, args.v1_lock, args.v2_lock)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_RUNTIME_LOCK_V2_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
