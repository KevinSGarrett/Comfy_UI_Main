#!/usr/bin/env python3
"""Run the admitted LatentSync import-only canary without runtime authority."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys


EXPECTED_ADMISSION_SHA256 = "62d2eed99f8ea586ec5709ccf3c9f29a911bf6f7dbc99f87a90315c09813f1b0"
EXPECTED_ENVIRONMENT_RECEIPT_SHA256 = "a13ba52cb63e871ada18550db06544fee51c58341d546edb276b3ecdf4c3f68e"
EXPECTED_COMMIT = "a229c3948406bc2cf6eaf4873e662e70c6a04746"
EXPECTED_TREE = "51f62bc8aea02da92b1a349077cfb78d0456f742"
EXPECTED_DECORD_BINARY_SHA256 = "98b260c5812106648ba299279916fbe98439893e346d4efdcf5cde66ba8973da"
ALLOWED_TRUE = {
    "package_import",
    "project_code_import",
    "module_origin_inspection",
    "decord_binary_hash_read",
}
RUNTIME_CLAIMS = {
    "package_imported": True,
    "project_code_imported": True,
    "model_config_read": False,
    "weights_accessed": False,
    "model_constructed": False,
    "tensor_allocated": False,
    "gpu_or_lease_polled": False,
    "inference_performed": False,
    "service_changed": False,
    "role_activated": False,
    "audio_visual_authority": False,
    "product_authority": False,
}


class CanaryError(RuntimeError):
    """A fail-closed import-canary error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise CanaryError(f"identity command failed: {command!r}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def load_admission(path: Path) -> dict:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise CanaryError("admission hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    if admission.get("status") != "PACKAGE_AND_PROJECT_IMPORT_CANARY_ADMITTED_EXECUTION_PENDING":
        raise CanaryError("import canary is not admitted")
    authority = admission.get("authority", {})
    if any(authority.get(name) is not True for name in ALLOWED_TRUE):
        raise CanaryError("required import authority missing")
    if any(value is not False for name, value in authority.items() if name not in ALLOWED_TRUE):
        raise CanaryError("admission exceeds import-only authority")
    return admission


def validate_environment(admission: dict) -> tuple[Path, Path]:
    environment = admission["environment"]
    environment_root = Path(environment["root"])
    code_root = Path(admission["code"]["root"])
    if Path(sys.prefix).absolute() != environment_root:
        raise CanaryError("canary must run from the admitted isolated environment")
    if sys.version.split()[0] != environment["python_version"]:
        raise CanaryError("canary Python version mismatch")
    receipt_path = Path(environment["receipt_path"])
    if sha256_file(receipt_path) != EXPECTED_ENVIRONMENT_RECEIPT_SHA256:
        raise CanaryError("environment receipt hash mismatch")
    if not code_root.is_dir() or code_root.is_symlink():
        raise CanaryError("LatentSync code root is missing or unsafe")
    if run(["git", "-C", str(code_root), "rev-parse", "HEAD"]) != EXPECTED_COMMIT:
        raise CanaryError("LatentSync checkout commit mismatch")
    if run(["git", "-C", str(code_root), "rev-parse", "HEAD^{tree}"]) != EXPECTED_TREE:
        raise CanaryError("LatentSync checkout tree mismatch")
    if run(["git", "-C", str(code_root), "status", "--porcelain", "--untracked-files=all"]):
        raise CanaryError("LatentSync checkout is dirty")
    return environment_root, code_root


def module_origin(module: object) -> Path:
    value = getattr(module, "__file__", None)
    if not value:
        raise CanaryError(f"imported module has no file origin: {getattr(module, '__name__', '?')}")
    return Path(value).resolve()


def write_or_verify_receipt(path: Path, receipt: dict) -> str:
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_text(encoding="utf-8") != payload:
            raise CanaryError("existing import receipt differs from replay")
        return "REUSED_VERIFIED_IMPORT_CANARY"
    temporary = path.with_name(f".{path.name}.installing")
    if temporary.exists() or temporary.is_symlink():
        raise CanaryError("stale import receipt staging path")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return "CREATED_VERIFIED_IMPORT_CANARY"


def canary(admission_path: Path) -> dict:
    admission = load_admission(admission_path)
    for name, value in admission["environment_controls"].items():
        os.environ[name] = value
    environment_root, code_root = validate_environment(admission)
    sys.path.insert(0, str(code_root))
    allowed_roots = (environment_root.resolve(), code_root.resolve())
    imported = []
    modules: dict[str, object] = {}
    for name in admission["imports"]:
        module = importlib.import_module(name)
        origin = module_origin(module)
        if not any(origin.is_relative_to(root) for root in allowed_roots):
            raise CanaryError(f"module origin is outside admitted roots: {name}: {origin}")
        modules[name] = module
        imported.append({"name": name, "origin": str(origin)})

    decord_module = modules["decord"]
    binary = module_origin(decord_module).parent / "libdecord.so"
    if not binary.is_file() or binary.is_symlink():
        raise CanaryError("decord shared library is missing or unsafe")
    binary_binding = {
        "path": str(binary),
        "bytes": binary.stat().st_size,
        "sha256": sha256_file(binary),
    }
    if binary_binding["bytes"] != 12465984 or binary_binding["sha256"] != EXPECTED_DECORD_BINARY_SHA256:
        raise CanaryError("decord shared library identity mismatch after import")

    receipt = {
        "schema_version": "wave64.aqa.latentsync_import_canary_receipt.v1",
        "program_id": "W64-AQA",
        "package_id": "W64-AQA-PKG-LATENTSYNC-1.6",
        "status": "PACKAGE_AND_PROJECT_IMPORTS_PASS_MODEL_LOAD_PENDING",
        "admission_commit": "326c11ef",
        "admission_sha256": EXPECTED_ADMISSION_SHA256,
        "environment_receipt_sha256": EXPECTED_ENVIRONMENT_RECEIPT_SHA256,
        "environment_root": str(environment_root),
        "code": {"root": str(code_root), "commit": EXPECTED_COMMIT, "tree": EXPECTED_TREE, "clean": True},
        "environment_controls": admission["environment_controls"],
        "imports": imported,
        "import_count": len(imported),
        "decord_binary": binary_binding,
        "runtime_claims": RUNTIME_CLAIMS,
    }
    result = write_or_verify_receipt(Path(admission["target_receipt"]), receipt)
    return {"status": result, "receipt": admission["target_receipt"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(canary(args.admission), sort_keys=True))
    except (CanaryError, OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
