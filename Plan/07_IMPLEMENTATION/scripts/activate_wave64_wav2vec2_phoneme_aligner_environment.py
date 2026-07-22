#!/usr/bin/env python3
"""Validate and activate the exact isolated Wave64 phoneme dependency environment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


LOCK_SHA256 = "7abfff8a8d3252776a10556648f4b9fb37f6cf734eebf4333004b57ccd2c484a"
ENVIRONMENT_ROOT = Path(
    "/workspace/w64_aqa/environments/wav2vec2-phoneme-aligner/"
    "phonemizer-fork-3.3.2_espeakng-loader-0.2.4_py311/"
    f"{LOCK_SHA256}"
)
ALLOWED_PARENT = Path("/workspace/w64_aqa/environments/wav2vec2-phoneme-aligner")
EMBEDDED_DATA_BINDING = Path(
    "/home/runner/work/espeakng-loader/espeakng-loader/espeak-ng/"
    "_dynamic/share/espeak-ng-data"
)
EXPECTED_VERSIONS = {"phonemizer-fork": "3.3.2", "espeakng-loader": "0.2.4"}
CANARY_TEXT = "We hold the frame steady and move on the beat."


class ActivationError(RuntimeError):
    """Raised when the exact environment or support binding is unsafe."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_environment_root(root: Path, allowed_parent: Path = ALLOWED_PARENT) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise ActivationError("environment root is absent or is a symlink")
    resolved = root.resolve(strict=True)
    parent = allowed_parent.resolve(strict=True)
    if resolved == parent or parent not in resolved.parents:
        raise ActivationError("environment root escapes the allowed parent")
    if resolved.name != LOCK_SHA256:
        raise ActivationError("environment root is not bound to the admitted lock hash")
    return resolved


def ensure_exact_binding(binding: Path, data_path: Path) -> str:
    resolved_data = data_path.resolve(strict=True)
    if not resolved_data.is_dir():
        raise ActivationError("eSpeak data path is not a directory")
    if binding.exists() or binding.is_symlink():
        if not binding.is_symlink():
            raise ActivationError("embedded eSpeak data binding is occupied by a non-symlink")
        if binding.resolve(strict=True) != resolved_data:
            raise ActivationError("embedded eSpeak data binding points to another target")
        return "REUSED_EXACT_BINDING"
    binding.parent.mkdir(parents=True, exist_ok=True)
    binding.symlink_to(resolved_data, target_is_directory=True)
    if binding.resolve(strict=True) != resolved_data:
        raise ActivationError("embedded eSpeak data binding verification failed")
    return "CREATED_EXACT_BINDING"


def tree_summary(root: Path) -> dict[str, Any]:
    members: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ActivationError(f"environment member symlink is forbidden: {path}")
        if path.is_file():
            members.append(
                (path.relative_to(root).as_posix(), path.stat().st_size, sha256_file(path))
            )
    manifest = "".join(
        f"{digest}  {relative_path}\n"
        for relative_path, _size, digest in members
    ).encode("utf-8")
    return {
        "file_count": len(members),
        "total_bytes": sum(size for _path, size, _digest in members),
        "tree_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
    }


def global_freeze_sha256() -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--all"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()


def run_canary(root: Path, binding: Path = EMBEDDED_DATA_BINDING) -> dict[str, Any]:
    global_freeze_before = global_freeze_sha256()
    resolved_root = validate_environment_root(root)
    sys.path.insert(0, str(resolved_root))
    import espeakng_loader  # type: ignore[import-not-found]
    from phonemizer.backend import EspeakBackend  # type: ignore[import-not-found]
    from phonemizer.backend.espeak.wrapper import (  # type: ignore[import-not-found]
        EspeakWrapper,
    )

    observed_versions = {
        name: metadata.version(name) for name in sorted(EXPECTED_VERSIONS)
    }
    if observed_versions != EXPECTED_VERSIONS:
        raise ActivationError("dependency version mismatch")
    library_path = Path(espeakng_loader.get_library_path()).resolve(strict=True)
    data_path = Path(espeakng_loader.get_data_path()).resolve(strict=True)
    if resolved_root not in library_path.parents or resolved_root not in data_path.parents:
        raise ActivationError("eSpeak library or data escaped the exact environment")
    binding_status = ensure_exact_binding(binding, data_path)
    EspeakWrapper.set_library(str(library_path))
    EspeakWrapper.set_data_path(str(data_path))
    if not EspeakBackend.is_available():
        raise ActivationError("eSpeak backend is unavailable")
    backend = EspeakBackend(
        "en-us", preserve_punctuation=True, with_stress=True
    )
    first = backend.phonemize([CANARY_TEXT], strip=True)
    second = backend.phonemize([CANARY_TEXT], strip=True)
    if first != second or len(first) != 1 or not first[0].strip():
        raise ActivationError("deterministic phonemization canary failed")
    global_freeze_after = global_freeze_sha256()
    if global_freeze_after != global_freeze_before:
        raise ActivationError("global Python environment changed during activation")
    return {
        "schema_version": "wave64.aqa.phoneme_dependency_activation.v1",
        "status": "PASS_EXACT_ISOLATED_DEPENDENCY_AND_PHONEMIZATION_CANARY",
        "lock_sha256": LOCK_SHA256,
        "environment_root": str(resolved_root),
        "environment": tree_summary(resolved_root),
        "global_environment_mutated": False,
        "global_freeze_sha256_before": global_freeze_before,
        "global_freeze_sha256_after": global_freeze_after,
        "python": sys.version.split()[0],
        "versions": observed_versions,
        "espeak": {
            "library_path": str(library_path),
            "library_sha256": sha256_file(library_path),
            "data_path": str(data_path),
            "data_file_count": sum(1 for path in data_path.rglob("*") if path.is_file()),
            "embedded_data_binding": str(binding),
            "binding_status": binding_status,
            "backend_version": list(backend.version()),
            "backend_data_path": str(backend._espeak.data_path),
        },
        "canary": {
            "language": "en-us",
            "with_stress": True,
            "input_text": CANARY_TEXT,
            "phonemes": first[0],
            "repeat_equal": True,
        },
        "authority": {
            "dependency_environment": True,
            "deterministic_text_phonemization": True,
            "model_load": False,
            "audio_inference": False,
            "forced_alignment": False,
            "negative_control_refusal": False,
            "operational_activation": False,
            "product_promotion": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-root", type=Path, default=ENVIRONMENT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; activation evidence is immutable")
    try:
        evidence = run_canary(args.environment_root)
    except (ActivationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(args.output)
    print(json.dumps({"status": evidence["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
