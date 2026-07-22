#!/usr/bin/env python3
"""Run a metadata-only Qwen3-ASR dependency preflight.

This command deliberately does not import torch, transformers, qwen-asr, or any
model module. It reads immutable model configuration and Python distribution
metadata only. A successful command means the receipt is trustworthy; it does
not mean that the model is ready to load.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import tempfile


PROGRAM_ID = "W64-AQA"
PACKAGE_ID = "W64-AQA-PKG-QWEN3-ASR-17B"
EXPECTED_REVISION = "7278e1e70fe206f11671096ffdd38061171dd6e5"
EXPECTED_MODEL_TYPE = "qwen3_asr"
EXPECTED_ARCHITECTURE = "Qwen3ASRForConditionalGeneration"
EXPECTED_PROCESSOR = "Qwen3ASRProcessor"
CHECKED_DISTRIBUTIONS = (
    "qwen-asr",
    "transformers",
    "torch",
    "accelerate",
    "librosa",
    "soundfile",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def transformers_support_paths() -> list[str]:
    try:
        distribution = metadata.distribution("transformers")
    except metadata.PackageNotFoundError:
        return []
    return sorted(
        str(path).replace("\\", "/")
        for path in (distribution.files or [])
        if "qwen3_asr" in str(path).lower()
    )


def load_json_object(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular file is missing or symlinked: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build_receipt(model_root: Path) -> dict:
    if model_root.is_symlink() or not model_root.is_dir():
        raise ValueError("model root must be a non-symlink directory")
    if model_root.name != EXPECTED_REVISION:
        raise ValueError("model root must end in the admitted source revision")

    config_path = model_root / "config.json"
    preprocessor_path = model_root / "preprocessor_config.json"
    config = load_json_object(config_path)
    preprocessor = load_json_object(preprocessor_path)
    architectures = config.get("architectures")
    assertions = {
        "model_type_exact": config.get("model_type") == EXPECTED_MODEL_TYPE,
        "architecture_exact": architectures == [EXPECTED_ARCHITECTURE],
        "processor_class_exact": preprocessor.get("processor_class") == EXPECTED_PROCESSOR,
        "revision_path_exact": model_root.name == EXPECTED_REVISION,
    }
    versions = {name: distribution_version(name) for name in CHECKED_DISTRIBUTIONS}
    support_paths = transformers_support_paths()
    gaps: list[str] = []
    if not all(assertions.values()):
        gaps.append("MODEL_CONFIG_IDENTITY_MISMATCH")
    if versions["qwen-asr"] is None:
        gaps.append("QWEN_ASR_DISTRIBUTION_MISSING")
    if versions["transformers"] is None:
        gaps.append("TRANSFORMERS_DISTRIBUTION_MISSING")
    elif not support_paths:
        gaps.append("INSTALLED_TRANSFORMERS_LACKS_QWEN3_ASR_SUPPORT")

    config_identity_pass = all(assertions.values())
    dependency_metadata_pass = (
        versions["qwen-asr"] is not None
        and versions["transformers"] is not None
        and bool(support_paths)
    )
    if not config_identity_pass:
        classification = "MODEL_CONFIG_IDENTITY_FAIL"
    elif dependency_metadata_pass:
        classification = "METADATA_DEPENDENCIES_PRESENT_IMPORT_AND_LOAD_UNQUALIFIED"
    else:
        classification = "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED"

    return {
        "schema_version": "wave64.aqa.qwen3_asr_dependency_preflight.v1",
        "program_id": PROGRAM_ID,
        "package_id": PACKAGE_ID,
        "classification": classification,
        "model_root": model_root.as_posix(),
        "source_revision": EXPECTED_REVISION,
        "python_version": platform.python_version(),
        "config": {
            "sha256": sha256_file(config_path),
            "model_type": config.get("model_type"),
            "architectures": architectures,
            "transformers_version_recorded": config.get("transformers_version"),
        },
        "preprocessor": {
            "sha256": sha256_file(preprocessor_path),
            "processor_class": preprocessor.get("processor_class"),
        },
        "assertions": assertions,
        "distribution_versions": versions,
        "transformers_qwen3_asr_support_paths": support_paths,
        "dependency_gaps": gaps,
        "next_action": (
            "Build an immutable isolated Python environment from a separately admitted "
            "official qwen-asr dependency lock; do not modify the active ComfyUI environment."
            if gaps
            else "Run a separate import-only canary; model construction and weight load remain forbidden."
        ),
        "runtime_claims": {
            "model_library_imported": False,
            "model_constructed": False,
            "weights_loaded": False,
            "tensor_allocated": False,
            "gpu_or_lease_polled": False,
            "inference_performed": False,
            "role_activated": False,
            "product_authority": False,
        },
    }


def write_json_atomic_no_overwrite(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite receipt: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = build_receipt(args.model_root)
    if args.output is not None:
        write_json_atomic_no_overwrite(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
