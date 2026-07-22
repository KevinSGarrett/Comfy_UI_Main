#!/usr/bin/env python3
"""Run a metadata-only Qwen3-Omni dependency preflight."""

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
PACKAGE_ID = "W64-AQA-PKG-QWEN3-OMNI-30B-A3B"
EXPECTED_REVISION = "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b"
EXPECTED_MODEL_TYPE = "qwen3_omni_moe"
EXPECTED_ARCHITECTURE = "Qwen3OmniMoeForConditionalGeneration"
EXPECTED_PROCESSOR = "Qwen3OmniMoeProcessor"
EXPECTED_COMPONENT_TYPES = {
    "thinker": "qwen3_omni_moe_thinker",
    "audio": "qwen3_omni_moe_audio_encoder",
    "vision": "qwen3_omni_moe_vision_encoder",
    "text": "qwen3_omni_moe_text",
}
CHECKED_DISTRIBUTIONS = (
    "transformers",
    "torch",
    "accelerate",
    "qwen-omni-utils",
    "av",
    "librosa",
    "Pillow",
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
        if "qwen3_omni_moe" in str(path).lower()
    )


def load_json_object(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular file is missing or symlinked: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def observed_component_types(config: dict) -> dict[str, str | None]:
    thinker = config.get("thinker_config") or {}
    return {
        "thinker": thinker.get("model_type"),
        "audio": (thinker.get("audio_config") or {}).get("model_type"),
        "vision": (thinker.get("vision_config") or {}).get("model_type"),
        "text": (thinker.get("text_config") or {}).get("model_type"),
    }


def build_receipt(model_root: Path) -> dict:
    if model_root.is_symlink() or not model_root.is_dir():
        raise ValueError("model root must be a non-symlink directory")
    if model_root.name != EXPECTED_REVISION:
        raise ValueError("model root must end in the admitted source revision")
    config_path = model_root / "config.json"
    preprocessor_path = model_root / "preprocessor_config.json"
    config = load_json_object(config_path)
    preprocessor = load_json_object(preprocessor_path)
    components = observed_component_types(config)
    assertions = {
        "model_type_exact": config.get("model_type") == EXPECTED_MODEL_TYPE,
        "architecture_exact": config.get("architectures") == [EXPECTED_ARCHITECTURE],
        "processor_class_exact": preprocessor.get("processor_class") == EXPECTED_PROCESSOR,
        "component_types_exact": components == EXPECTED_COMPONENT_TYPES,
        "revision_path_exact": model_root.name == EXPECTED_REVISION,
    }
    versions = {name: distribution_version(name) for name in CHECKED_DISTRIBUTIONS}
    support_paths = transformers_support_paths()
    gaps: list[str] = []
    if not all(assertions.values()):
        gaps.append("MODEL_CONFIG_IDENTITY_MISMATCH")
    if versions["qwen-omni-utils"] is None:
        gaps.append("QWEN_OMNI_UTILS_DISTRIBUTION_MISSING")
    if versions["transformers"] is None:
        gaps.append("TRANSFORMERS_DISTRIBUTION_MISSING")
    elif not support_paths:
        gaps.append("INSTALLED_TRANSFORMERS_LACKS_QWEN3_OMNI_SUPPORT")
    config_pass = all(assertions.values())
    dependency_pass = (
        versions["qwen-omni-utils"] is not None
        and versions["transformers"] is not None
        and bool(support_paths)
    )
    if not config_pass:
        classification = "MODEL_CONFIG_IDENTITY_FAIL"
    elif dependency_pass:
        classification = "METADATA_DEPENDENCIES_PRESENT_IMPORT_AND_LOAD_UNQUALIFIED"
    else:
        classification = "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED"
    return {
        "schema_version": "wave64.aqa.qwen3_omni_dependency_preflight.v1",
        "program_id": PROGRAM_ID,
        "package_id": PACKAGE_ID,
        "classification": classification,
        "model_root": model_root.as_posix(),
        "source_revision": EXPECTED_REVISION,
        "python_version": platform.python_version(),
        "config": {
            "sha256": sha256_file(config_path),
            "model_type": config.get("model_type"),
            "architectures": config.get("architectures"),
            "transformers_version_recorded": config.get("transformers_version"),
            "component_types": components,
        },
        "preprocessor": {
            "sha256": sha256_file(preprocessor_path),
            "processor_class": preprocessor.get("processor_class"),
        },
        "assertions": assertions,
        "distribution_versions": versions,
        "transformers_qwen3_omni_support_paths": support_paths,
        "dependency_gaps": gaps,
        "next_action": (
            "Build an immutable isolated environment from a separately admitted "
            "Transformers 5.2-plus dependency lock; do not modify active ComfyUI."
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
            "audio_or_av_authority": False,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipt = build_receipt(args.model_root)
    write_json_atomic_no_overwrite(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
