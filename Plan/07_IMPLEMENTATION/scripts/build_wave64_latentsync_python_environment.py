#!/usr/bin/env python3
"""Build the admitted LatentSync environment without import or runtime authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


EXPECTED_ADMISSION_SHA256 = "d6c268984911f7d0e0f771ecdb814b9e29a401b32a0e265f068b05ae434b4e1b"
EXPECTED_LOCK_SHA256 = "862e85d3cbb3a1dd9a90dd9541bff24b20ae997c95326f9331b9e466dc6b40ff"
EXPECTED_PACKAGE_ID = "W64-AQA-PKG-LATENTSYNC-1.6"
EXPECTED_UV_VERSION = "0.11.30"
EXPECTED_PYTHON_VERSION = "3.11.10"
EXPECTED_BASE_PYTHON_SHA256 = "45c68b7ca1e3765a06756734c15af204ca9c0588a3f6d7a6d8bb8ed58e3e2a1a"
EXPECTED_DISTRIBUTION_COUNT = 149
EXPECTED_LOCAL_WHEELS = {
    "antlr4_python3_runtime-4.9.3-py3-none-any.whl": (
        144589,
        "33b8ef731ab54955e6a77eaca700428b2829a1ffe2cd31e797ad23c6ea9fd93e",
    ),
    "insightface-0.7.3-cp311-cp311-linux_x86_64.whl": (
        1065080,
        "605ffbee47d29222ead2308db3fd705a11dca4248ac761ff5216d0098a9d92df",
    ),
    "python_speech_features-0.6-py3-none-any.whl": (
        5891,
        "7c754cba8f6d46e8eff77014cd179e4ffd1b141772b0113e925eee45c63f3a05",
    ),
}
RUNTIME_CLAIMS = {
    "package_imported": False,
    "project_code_imported": False,
    "model_loaded": False,
    "weights_accessed": False,
    "tensor_allocated": False,
    "gpu_or_lease_polled": False,
    "inference_performed": False,
    "service_changed": False,
    "role_activated": False,
    "audio_visual_authority": False,
    "product_authority": False,
}


class BuildError(RuntimeError):
    """A fail-closed admission or environment-build error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, environment: dict[str, str] | None = None) -> str:
    process_environment = os.environ.copy()
    if environment:
        process_environment.update(environment)
    completed = subprocess.run(
        command,
        env=process_environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise BuildError(
            f"command failed ({completed.returncode}): {command!r}\n{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def normalized_name(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(".", "-")


def load_admission(path: Path, lock_path: Path) -> tuple[dict, dict]:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise BuildError("admission hash mismatch")
    if sha256_file(lock_path) != EXPECTED_LOCK_SHA256:
        raise BuildError("runtime lock hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    if admission.get("package_id") != EXPECTED_PACKAGE_ID:
        raise BuildError("admission package mismatch")
    if admission.get("status") != "DEPENDENCY_ENVIRONMENT_BUILD_ADMITTED_EXECUTION_PENDING":
        raise BuildError("environment build is not admitted")
    if admission.get("resolution", {}).get("lock_sha256") != EXPECTED_LOCK_SHA256:
        raise BuildError("admission lock binding mismatch")
    authority = admission.get("authority", {})
    allowed_true = {"environment_create", "locked_wheel_install"}
    if any(authority.get(name) is not True for name in allowed_true):
        raise BuildError("required dependency-build authority missing")
    if any(value is not False for name, value in authority.items() if name not in allowed_true):
        raise BuildError("admission contains forbidden runtime authority")
    return admission, lock


def validate_paths(admission: dict, receipt_path: Path) -> tuple[Path, Path, Path]:
    target_text = admission["targets"]["environment_root"]
    target = Path(target_text)
    if not target_text.startswith("/workspace/w64_aqa/environments/LatentSync-1.6/"):
        raise BuildError("unsafe environment target")
    if target.name != EXPECTED_LOCK_SHA256:
        raise BuildError("environment target is not lock-addressed")
    staging = target.with_name(f".{target.name}.installing")
    scratch = target.with_name(f".{target.name}.uv-scratch")
    if any(path.is_symlink() for path in (target, staging, scratch, receipt_path)):
        raise BuildError("environment target, staging, scratch, or receipt path is a symlink")
    if not receipt_path.as_posix().startswith("/workspace/w64_aqa/control/receipts/"):
        raise BuildError("unsafe receipt target")
    return target, staging, scratch


def python_identity(executable: Path) -> dict[str, str]:
    version = run([str(executable), "-c", "import platform; print(platform.python_version())"])
    return {"version": version, "executable": str(executable), "sha256": sha256_file(executable)}


def distribution_manifest(executable: Path | str) -> list[dict[str, str]]:
    observed = json.loads(run(["uv", "pip", "list", "--python", str(executable), "--format", "json"]))
    rows = sorted(
        (
            {"name": normalized_name(item["name"]), "version": item["version"]}
            for item in observed
            if item.get("name")
        ),
        key=lambda item: (item["name"], item["version"]),
    )
    if len({item["name"] for item in rows}) != len(rows):
        raise BuildError("installed distribution identity is duplicated")
    return rows


def expected_distribution_manifest(lock: dict) -> list[dict[str, str]]:
    rows = sorted(
        (
            {"name": normalized_name(item["name"]), "version": item["version"]}
            for item in lock.get("packages", [])
        ),
        key=lambda item: (item["name"], item["version"]),
    )
    if len(rows) != EXPECTED_DISTRIBUTION_COUNT or len({item["name"] for item in rows}) != len(rows):
        raise BuildError("runtime lock distribution identity mismatch")
    return rows


def distribution_signature(executable: Path | str) -> str:
    payload = json.dumps(distribution_manifest(executable), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def local_wheel_manifest(admission: dict) -> list[dict[str, str | int]]:
    root = Path(admission["local_wheelhouse"]["root"])
    if not root.is_dir() or root.is_symlink():
        raise BuildError("local wheelhouse is missing or unsafe")
    observed: list[dict[str, str | int]] = []
    for filename, (expected_bytes, expected_hash) in sorted(EXPECTED_LOCAL_WHEELS.items()):
        path = root / filename
        if not path.is_file() or path.is_symlink():
            raise BuildError(f"local wheel is missing or unsafe: {filename}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != expected_bytes or digest != expected_hash:
            raise BuildError(f"local wheel identity mismatch: {filename}")
        observed.append({"filename": filename, "bytes": size, "sha256": digest})
    if {path.name for path in root.iterdir()} != set(EXPECTED_LOCAL_WHEELS):
        raise BuildError("local wheelhouse contains an unexpected entry")
    return observed


def tree_manifest(root: Path) -> dict[str, str | int]:
    digest = hashlib.sha256()
    regular_file_count = 0
    symlink_count = 0
    total_regular_file_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            target = os.readlink(path)
            digest.update(f"L\0{relative}\0{target}\n".encode())
            symlink_count += 1
        elif path.is_file():
            size = path.stat().st_size
            file_hash = sha256_file(path)
            digest.update(f"F\0{relative}\0{size}\0{file_hash}\n".encode())
            regular_file_count += 1
            total_regular_file_bytes += size
    return {
        "sha256": digest.hexdigest(),
        "regular_file_count": regular_file_count,
        "symlink_count": symlink_count,
        "total_regular_file_bytes": total_regular_file_bytes,
    }


def write_receipt_temp(path: Path, receipt: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.installing")
    if path.exists() or temporary.exists() or path.is_symlink() or temporary.is_symlink():
        raise BuildError("receipt target already exists")
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def verify_replay(target: Path, receipt_path: Path, expected_distributions: list[dict]) -> dict:
    if not target.is_dir() or not receipt_path.is_file():
        raise BuildError("partial prior environment cannot be reused")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("environment_tree") != tree_manifest(target):
        raise BuildError("existing environment tree does not match receipt")
    distributions = distribution_manifest(target / "bin/python")
    if distributions != expected_distributions or receipt.get("distributions") != distributions:
        raise BuildError("existing distribution manifest does not match lock or receipt")
    return {"status": "REUSED_VERIFIED_ENVIRONMENT", "receipt": str(receipt_path)}


def build(admission_path: Path, lock_path: Path, receipt_path: Path, active_python: str) -> dict:
    admission, lock = load_admission(admission_path, lock_path)
    target, staging, scratch = validate_paths(admission, receipt_path)
    expected_distributions = expected_distribution_manifest(lock)
    if target.exists() or receipt_path.exists():
        return verify_replay(target, receipt_path, expected_distributions)
    if staging.exists() or scratch.exists():
        raise BuildError("stale staging or scratch path requires independent disposition")

    base = Path(admission["base_python"]["executable"])
    identity = python_identity(base)
    if identity["version"] != EXPECTED_PYTHON_VERSION or identity["sha256"] != EXPECTED_BASE_PYTHON_SHA256:
        raise BuildError("base Python identity mismatch")
    if run(["uv", "--version"]).split()[:2] != ["uv", EXPECTED_UV_VERSION]:
        raise BuildError("uv version mismatch")
    local_wheels = local_wheel_manifest(admission)
    target.parent.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(target.parent).free
    if free_bytes < admission["resolution"]["minimum_free_bytes"]:
        raise BuildError("insufficient free space for admitted build")
    active_before = distribution_signature(active_python)

    receipt_temp: Path | None = None
    try:
        scratch_tmp = scratch / "tmp"
        scratch_tmp.mkdir(parents=True, exist_ok=False)
        install_environment = {
            "TMPDIR": str(scratch_tmp),
            "UV_CACHE_DIR": str(scratch / "uv-cache"),
            "UV_NO_CACHE": "1",
        }
        run(["uv", "venv", "--python", str(base), str(staging)], environment=install_environment)
        run(
            ["uv", "pip", "sync", "--python", str(staging / "bin/python"), str(lock_path)],
            environment=install_environment,
        )
        run(
            ["uv", "pip", "check", "--python", str(staging / "bin/python")],
            environment=install_environment,
        )
        distributions = distribution_manifest(staging / "bin/python")
        if distributions != expected_distributions:
            raise BuildError("installed distribution manifest does not match runtime lock")
        environment_tree = tree_manifest(staging)
        active_after = distribution_signature(active_python)
        if active_before != active_after:
            raise BuildError("active Python distribution metadata changed")
        shutil.rmtree(scratch)
        receipt = {
            "schema_version": "wave64.aqa.latentsync_python_environment_build_receipt.v1",
            "program_id": "W64-AQA",
            "package_id": EXPECTED_PACKAGE_ID,
            "status": "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING",
            "admission_commit": "bef7fea1",
            "admission_sha256": EXPECTED_ADMISSION_SHA256,
            "lock_sha256": EXPECTED_LOCK_SHA256,
            "environment_root": str(target),
            "python": {
                "version": identity["version"],
                "base_executable": str(base),
                "base_executable_sha256": identity["sha256"],
            },
            "uv_version": EXPECTED_UV_VERSION,
            "free_bytes_before": free_bytes,
            "prior_attempts": [
                {
                    "controller_commit": "a3f3aad6",
                    "result": "FAIL_CLOSED_BEFORE_ENVIRONMENT_PUBLICATION",
                    "reason": "uv used the root-filesystem default cache and exhausted available root space while extracting the hash-bound onnx wheel",
                    "staging_removed": True,
                    "environment_published": False,
                    "receipt_published": False,
                }
            ],
            "distribution_count": len(distributions),
            "distributions": distributions,
            "pip_check": "PASS_149_PACKAGES_COMPATIBLE",
            "local_wheels": local_wheels,
            "environment_tree": environment_tree,
            "active_environment": {
                "python": active_python,
                "metadata_signature_before": active_before,
                "metadata_signature_after": active_after,
                "unchanged": True,
            },
            "storage_authority": {
                "logical_filesystem_free_bytes_is_billing_quota_authority": False,
                "prebuild_reconciled_quota_reserve_gib_estimate": 64.025977,
                "postbuild_quota_reserve_requires_retained_size_measurement": True,
            },
            "runtime_claims": RUNTIME_CLAIMS,
        }
        receipt_temp = write_receipt_temp(receipt_path, receipt)
        os.replace(staging, target)
        os.replace(receipt_temp, receipt_path)
        receipt_temp = None
        return {"status": "CREATED_VERIFIED_ENVIRONMENT", "receipt": str(receipt_path)}
    except Exception:
        if receipt_temp and receipt_temp.exists() and not receipt_temp.is_symlink():
            receipt_temp.unlink()
        if scratch.exists() and not scratch.is_symlink():
            shutil.rmtree(scratch)
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--active-python", default="python3")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.admission, args.lock, args.receipt, args.active_python), sort_keys=True))
    except (BuildError, OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
