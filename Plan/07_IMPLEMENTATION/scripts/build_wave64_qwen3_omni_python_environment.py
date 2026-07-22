#!/usr/bin/env python3
"""Build the admitted Qwen3-Omni Python environment without runtime authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


EXPECTED_ADMISSION_SHA256 = "71417720fc542cb0581182a326b672a7e073bf31eeb8a9e37ab8b8314b92b1a0"
EXPECTED_LOCK_SHA256 = "ddd947030a1815dc668d5b94e2e64f375351e846668bcf8bbd0c5e08b527d95a"
EXPECTED_PACKAGE_ID = "W64-AQA-PKG-QWEN3-OMNI-30B-A3B"
EXPECTED_UV_VERSION = "0.11.30"
EXPECTED_PYTHON_VERSION = "3.12.13"
EXPECTED_BASE_PYTHON_SHA256 = "7d43f6e86a6c6dd12005ec77eb2055f1be3f1bb3adedf8afe0a87973fa7371ce"
EXPECTED_DISTRIBUTION_COUNT = 75
EXPECTED_KEY_DISTRIBUTIONS = {
    "accelerate": "1.14.0",
    "av": "18.0.0",
    "decord": "0.6.0",
    "librosa": "0.11.0",
    "pillow": "12.3.0",
    "qwen-omni-utils": "0.0.9",
    "soundfile": "0.14.0",
    "torch": "2.4.1+cu124",
    "transformers": "5.2.0",
}
RUNTIME_CLAIMS = {
    "model_library_imported": False,
    "model_constructed": False,
    "weights_loaded": False,
    "tensor_allocated": False,
    "gpu_or_lease_polled": False,
    "inference_performed": False,
    "service_changed": False,
    "role_activated": False,
    "audio_or_av_authority": False,
    "product_authority": False,
}


class BuildError(RuntimeError):
    """A fail-closed admission or build error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, input_text: str | None = None) -> str:
    completed = subprocess.run(
        command,
        input=input_text,
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


def load_admission(path: Path) -> dict:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise BuildError("admission hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    if admission.get("package_id") != EXPECTED_PACKAGE_ID:
        raise BuildError("admission package mismatch")
    if admission.get("status") != "DEPENDENCY_ENVIRONMENT_BUILD_ADMITTED_EXECUTION_PENDING":
        raise BuildError("environment build is not admitted")
    if admission.get("resolution", {}).get("lock_sha256") != EXPECTED_LOCK_SHA256:
        raise BuildError("admission lock binding mismatch")
    if admission.get("authority", {}).get("environment_create") is not True:
        raise BuildError("environment creation authority missing")
    forbidden = set(admission.get("authority", {})) - {"environment_create", "locked_wheel_install"}
    if any(admission["authority"].get(name) for name in forbidden):
        raise BuildError("admission contains forbidden runtime authority")
    return admission


def validate_paths(admission: dict, lock_path: Path, receipt_path: Path) -> tuple[Path, Path]:
    target_text = admission["targets"]["environment_root"]
    target = Path(target_text)
    if not target_text.startswith("/workspace/w64_aqa/environments/"):
        raise BuildError("unsafe environment target")
    if target.name != EXPECTED_LOCK_SHA256:
        raise BuildError("environment target is not lock-addressed")
    staging = target.with_name(f".{target.name}.installing")
    if target.is_symlink() or staging.is_symlink():
        raise BuildError("environment target or staging path is a symlink")
    receipt_text = receipt_path.as_posix()
    if not receipt_text.startswith("/workspace/w64_aqa/control/"):
        raise BuildError("unsafe receipt target")
    if sha256_file(lock_path) != EXPECTED_LOCK_SHA256:
        raise BuildError("lock hash mismatch")
    return target, staging


def python_identity(executable: Path) -> dict:
    version = run([str(executable), "-c", "import platform; print(platform.python_version())"])
    return {"version": version, "executable": str(executable), "sha256": sha256_file(executable)}


def distribution_manifest(executable: str) -> list[dict[str, str]]:
    source = (
        "import importlib.metadata as m,json\n"
        "rows=[]\n"
        "for d in m.distributions():\n"
        " n=(d.metadata.get('Name') or '').strip().lower().replace('_','-')\n"
        " if n: rows.append({'name':n,'version':d.version})\n"
        "print(json.dumps(sorted(rows,key=lambda x:(x['name'],x['version'])),separators=(',',':')))\n"
    )
    rows = json.loads(run([executable, "-c", source]))
    if len({item["name"] for item in rows}) != len(rows):
        raise BuildError("installed distribution identity is duplicated")
    return rows


def manifest_signature(executable: str) -> str:
    payload = json.dumps(distribution_manifest(executable), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def tree_manifest(root: Path) -> dict:
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


def validate_distributions(distributions: list[dict[str, str]]) -> None:
    observed = {item["name"]: item["version"] for item in distributions}
    if len(distributions) != EXPECTED_DISTRIBUTION_COUNT:
        raise BuildError(f"installed distribution count mismatch: {len(distributions)}")
    for name, version in EXPECTED_KEY_DISTRIBUTIONS.items():
        if observed.get(name) != version:
            raise BuildError(f"installed {name} version mismatch")


def write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.installing")
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise BuildError("receipt target already exists")
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def verify_replay(target: Path, receipt_path: Path) -> dict:
    if not target.is_dir() or not receipt_path.is_file():
        raise BuildError("partial prior build cannot be reused")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("environment_tree") != tree_manifest(target):
        raise BuildError("existing environment tree does not match receipt")
    distributions = distribution_manifest(str(target / "bin/python"))
    validate_distributions(distributions)
    if receipt.get("distributions") != distributions:
        raise BuildError("existing distribution manifest does not match receipt")
    return {"status": "REUSED_VERIFIED_ENVIRONMENT", "receipt": str(receipt_path)}


def build(admission_path: Path, lock_path: Path, receipt_path: Path, active_python: str) -> dict:
    admission = load_admission(admission_path)
    target, staging = validate_paths(admission, lock_path, receipt_path)
    if target.exists() or receipt_path.exists():
        return verify_replay(target, receipt_path)
    if staging.exists():
        raise BuildError("stale staging environment requires independent disposition")

    base = Path(admission["base_python"]["executable"])
    identity = python_identity(base)
    if identity["version"] != EXPECTED_PYTHON_VERSION or identity["sha256"] != EXPECTED_BASE_PYTHON_SHA256:
        raise BuildError("base Python identity mismatch")
    uv_version = run(["uv", "--version"])
    if uv_version != f"uv {EXPECTED_UV_VERSION}":
        raise BuildError("uv version mismatch")
    free_bytes = shutil.disk_usage(target.parent).free
    if free_bytes < admission["resolution"]["minimum_free_bytes"]:
        raise BuildError("insufficient free space for admitted build")
    active_before = manifest_signature(active_python)

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        run(["uv", "venv", "--python", str(base), str(staging)])
        run(["uv", "pip", "sync", "--python", str(staging / "bin/python"), str(lock_path)])
        run(["uv", "pip", "check", "--python", str(staging / "bin/python")])
        distributions = distribution_manifest(str(staging / "bin/python"))
        validate_distributions(distributions)
        environment_tree = tree_manifest(staging)
        active_after = manifest_signature(active_python)
        if active_before != active_after:
            raise BuildError("active Python environment metadata changed")
        os.replace(staging, target)
        receipt = {
            "schema_version": "wave64.aqa.qwen3_omni_python_environment_build_receipt.v1",
            "program_id": "W64-AQA",
            "package_id": EXPECTED_PACKAGE_ID,
            "status": "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING",
            "admission_commit": "b15592a3d01915038b8836293d3f80fbbe5a5278",
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
            "distribution_count": len(distributions),
            "distributions": distributions,
            "pip_check": "PASS_75_PACKAGES_COMPATIBLE",
            "environment_tree": environment_tree,
            "active_environment": {
                "python": active_python,
                "metadata_signature_before": active_before,
                "metadata_signature_after": active_after,
                "unchanged": True,
            },
            "runtime_claims": RUNTIME_CLAIMS,
        }
        write_receipt(receipt_path, receipt)
        return {"status": "CREATED_VERIFIED_ENVIRONMENT", "receipt": str(receipt_path)}
    except Exception:
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
    except (BuildError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
