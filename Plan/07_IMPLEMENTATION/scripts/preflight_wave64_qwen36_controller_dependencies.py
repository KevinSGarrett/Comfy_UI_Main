#!/usr/bin/env python3
"""Run the Qwen3.6 controller metadata preflight without imports or weight access."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
from typing import Any


PROGRAM_ID = "W64-AQA"
PACKAGE_ID = "W64-AQA-PKG-QWEN36-35B-A3B"
EXPECTED_REVISION = "95a723d08a9490559dae23d0cff1d9466213d989"
EXPECTED_ADMISSION_DIGEST = "89dd14c6054e3f8f15882d59480cb0b3972b497d4825302c9749346291ae397c"
OMNI_LOCK_SHA256 = "a19d160721dfb74cf89bc70eebec10f45b2e6f58b7a109726d658db7d361277c"
METADATA_FILES = {
    "config.json": (37000, "c8df3b893d8070130c2b59497ddb508f41cf9168"),
    "generation_config.json": (202, "023756cfadf88e5bf69eefeee3e172f38c448d64"),
    "tokenizer_config.json": (16718, "28d96ff303d1d20350185caf4bf037045916ed35"),
    "model.safetensors.index.json": (6329223, "3a6440878f2f2564e214496bb35fcc37cbbf7d8b"),
}
CHECKED_DISTRIBUTIONS = ("transformers", "torch", "accelerate", "tokenizers", "safetensors")


def install_safety_audit_hook(model_root: Path) -> None:
    root = model_root.resolve()

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event.startswith(("socket.", "subprocess.", "os.system", "os.exec", "os.spawn")):
            raise PermissionError(f"forbidden preflight operation: {event}")
        if event == "open" and args:
            candidate = Path(os.fspath(args[0])) if isinstance(args[0], (str, bytes, os.PathLike)) else None
            if candidate and candidate.suffix == ".safetensors":
                try:
                    candidate.resolve().relative_to(root)
                except (OSError, ValueError):
                    return
                raise PermissionError("weight-file access is forbidden during metadata preflight")

    sys.addaudithook(audit)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()  # noqa: S324


def load_admitted_json(model_root: Path, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = model_root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular metadata file is missing or symlinked: {path}")
    data = path.read_bytes()
    expected_bytes, expected_identity = METADATA_FILES[name]
    if len(data) != expected_bytes or git_blob_sha1(data) != expected_identity:
        raise ValueError(f"admitted metadata identity mismatch: {name}")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value, {
        "bytes": len(data),
        "git_blob_sha1": expected_identity,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def transformers_support_paths(model_type: str | None) -> list[str]:
    if not model_type:
        return []
    try:
        distribution = metadata.distribution("transformers")
    except metadata.PackageNotFoundError:
        return []
    normalized = model_type.lower().replace(".", "_").replace("-", "_")
    return sorted(
        str(path).replace("\\", "/")
        for path in (distribution.files or [])
        if normalized in str(path).lower().replace("-", "_")
    )


def build_receipt(model_root: Path, candidate_lock_sha256: str | None) -> dict[str, Any]:
    if model_root.is_symlink() or not model_root.is_dir():
        raise ValueError("model root must be a non-symlink directory")
    if model_root.name != EXPECTED_REVISION:
        raise ValueError("model root must end in the admitted source revision")
    install_safety_audit_hook(model_root)
    loaded = {name: load_admitted_json(model_root, name) for name in METADATA_FILES}
    config, _ = loaded["config.json"]
    generation, _ = loaded["generation_config.json"]
    tokenizer, _ = loaded["tokenizer_config.json"]
    index, _ = loaded["model.safetensors.index.json"]
    model_type = config.get("model_type")
    architectures = config.get("architectures")
    recorded_transformers = config.get("transformers_version")
    versions = {name: distribution_version(name) for name in CHECKED_DISTRIBUTIONS}
    support_paths = transformers_support_paths(model_type if isinstance(model_type, str) else None)
    identity_pass = bool(model_type) and isinstance(architectures, list) and bool(architectures)
    candidate_metadata_support = bool(versions["transformers"] and support_paths)
    compatible_lock = candidate_lock_sha256 if candidate_metadata_support else None
    if not identity_pass:
        disposition = "BLOCKED_MODEL_METADATA_IDENTITY"
    elif compatible_lock:
        disposition = "COMPATIBLE_WITH_CANDIDATE_LOCK_METADATA_ONLY"
    else:
        disposition = "NEW_LOCK_RESOLUTION_REQUIRED"
    weight_map = index.get("weight_map")
    shards = sorted(set(weight_map.values())) if isinstance(weight_map, dict) else []
    return {
        "schema_version": "wave64.aqa.qwen36_controller_dependency_preflight.v1",
        "program_id": PROGRAM_ID,
        "package_id": PACKAGE_ID,
        "admission_digest": EXPECTED_ADMISSION_DIGEST,
        "source_revision": EXPECTED_REVISION,
        "model_root": model_root.as_posix(),
        "disposition": disposition,
        "candidate_lock_sha256": candidate_lock_sha256,
        "compatible_lock_sha256": compatible_lock,
        "candidate_is_existing_omni_lock": candidate_lock_sha256 == OMNI_LOCK_SHA256,
        "python_version": platform.python_version(),
        "metadata_files": {name: receipt for name, (_, receipt) in loaded.items()},
        "observed": {
            "model_type": model_type,
            "architectures": architectures,
            "transformers_version_recorded": recorded_transformers,
            "generation_config_model_type": generation.get("model_type"),
            "tokenizer_class": tokenizer.get("tokenizer_class"),
            "weight_map_entries": len(weight_map) if isinstance(weight_map, dict) else 0,
            "weight_shards_referenced": len(shards),
        },
        "distribution_versions": versions,
        "transformers_support_paths": support_paths,
        "assertions": {
            "revision_path_exact": True,
            "all_admitted_metadata_bytes_exact": True,
            "embedded_model_identity_present": identity_pass,
            "candidate_transformers_metadata_support_present": candidate_metadata_support,
        },
        "next_action": (
            "Issue a package-specific reuse admission, then run a separate import-only canary; weight load remains forbidden."
            if compatible_lock
            else "Resolve and admit a new immutable controller-specific dependency lock; do not mutate the Omni environment."
        ),
        "runtime_claims": {
            "model_library_imported": False,
            "model_constructed": False,
            "weights_opened": False,
            "weights_loaded": False,
            "tensor_allocated": False,
            "network_accessed": False,
            "subprocess_started": False,
            "gpu_or_lease_polled": False,
            "role_activated": False,
            "product_authority": False,
        },
    }


def write_json_atomic_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite receipt: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate-lock-sha256")
    args = parser.parse_args()
    if args.candidate_lock_sha256 and (
        len(args.candidate_lock_sha256) != 64
        or any(character not in "0123456789abcdef" for character in args.candidate_lock_sha256)
    ):
        parser.error("--candidate-lock-sha256 must be 64 lowercase hexadecimal characters")
    receipt = build_receipt(args.model_root, args.candidate_lock_sha256)
    write_json_atomic_no_overwrite(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
