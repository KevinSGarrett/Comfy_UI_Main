#!/usr/bin/env python3
"""Validate the Qwen3-Omni isolated dependency environment admission."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse


LOCK_SHA256 = "a19d160721dfb74cf89bc70eebec10f45b2e6f58b7a109726d658db7d361277c"
EXPECTED_HOSTS = {"files.pythonhosted.org", "download-r2.pytorch.org"}
EXPECTED_KEY_PACKAGES = {
    "accelerate": "1.14.0",
    "av": "18.0.0",
    "librosa": "0.11.0",
    "pillow": "12.3.0",
    "qwen-omni-utils": "0.0.9",
    "soundfile": "0.14.0",
    "torch": "2.4.1+cu124",
    "torchvision": "0.19.1+cu124",
    "transformers": "5.2.0",
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
        errors.append("dependency lock hash mismatch")
    if lock.get("lock-version") != "1.0" or lock.get("created-by") != "uv":
        errors.append("dependency lock header mismatch")
    if lock.get("requires-python") != ">=3.12":
        errors.append("dependency lock Python requirement mismatch")
    if len(packages) != 75 or resolution.get("package_count") != 75:
        errors.append("dependency package count mismatch")
    names: dict[str, str] = {}
    wheel_count = 0
    hosts: set[str] = set()
    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str) or name in names:
            errors.append("dependency package identity is missing or duplicated")
            continue
        names[name] = version
        wheels = package.get("wheels", [])
        if not wheels:
            errors.append(f"{name}: no selected wheel")
        wheel_count += len(wheels)
        for wheel in wheels:
            parsed = urlparse(wheel.get("url", ""))
            hosts.add(parsed.hostname or "")
            digest = wheel.get("hashes", {}).get("sha256")
            if parsed.scheme != "https" or not parsed.hostname:
                errors.append(f"{name}: wheel URL must use HTTPS")
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"{name}: wheel SHA-256 missing")
    if wheel_count != 78 or resolution.get("wheel_count") != 78:
        errors.append("dependency wheel count mismatch")
    if hosts != EXPECTED_HOSTS:
        errors.append("dependency wheel host allowlist mismatch")
    for name, version in EXPECTED_KEY_PACKAGES.items():
        if names.get(name) != version:
            errors.append(f"{name}: required version mismatch")
    if "vllm" in names or "flash-attn" in names:
        errors.append("minimal Transformers environment cannot include vLLM or FlashAttention")
    if "decord" in names:
        errors.append("Python 3.12 environment cannot include the CPython 3.6-tagged Decord wheel")
    if resolution.get("python_version") != "3.12.13" or resolution.get("uv_version") != "0.11.30":
        errors.append("Python or uv build identity mismatch")
    base = admission.get("base_python", {})
    if base.get("install_allowed") is not False or base.get("sha256") != "7d43f6e86a6c6dd12005ec77eb2055f1be3f1bb3adedf8afe0a87973fa7371ce":
        errors.append("base Python reuse identity mismatch")
    if admission.get("targets", {}).get("active_comfyui_environment_mutable") is not False:
        errors.append("active ComfyUI environment must remain immutable")
    forbidden = (
        "model_library_import",
        "model_load",
        "weight_access",
        "tensor_allocation",
        "gpu_or_lease_poll",
        "inference",
        "service_change",
        "role_activation",
        "audio_or_av_authority",
        "product_authority",
    )
    if any(authority.get(key) is not False for key in forbidden):
        errors.append("dependency build admission exceeds non-runtime authority")
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
    print("W64_AQA_QWEN3_OMNI_PYTHON_ENVIRONMENT_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
