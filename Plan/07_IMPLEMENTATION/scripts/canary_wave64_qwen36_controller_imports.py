#!/usr/bin/env python3
"""Run the admitted offline import-only Qwen3.6 controller canary."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
from typing import Any


EXPECTED_ADMISSION_SHA256 = "a36dc6c5a5c9cbd9fc65c3dff4722b149da2738cbe0f8a7e490baeb37cc65cbc"
REQUIRED_DISTRIBUTIONS = {
    "transformers": "5.2.0",
    "torch": "2.4.1+cu124",
    "accelerate": "1.14.0",
    "tokenizers": "0.22.2",
    "safetensors": "0.8.0",
}
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".gguf")
BLOCKED_EVENTS = ("socket.", "subprocess.", "os.system", "os.exec", "os.spawn")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_admission(path: Path) -> dict[str, Any]:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise RuntimeError("controller environment reuse admission hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    if admission.get("status") != "ADMITTED_FOR_IMPORT_ONLY_CANARY":
        raise RuntimeError("controller import-only canary is not admitted")
    authority = admission.get("authority", {})
    if authority != {
        "environment_reuse_admitted": True,
        "import_qualified": False,
        "runtime_qualified": False,
        "role_operational": False,
    }:
        raise RuntimeError("controller admission authority is invalid")
    return admission


def validate_environment(admission: dict[str, Any], output: Path) -> None:
    if Path(sys.prefix).resolve() != Path(admission["environment"]["root"]).resolve():
        raise RuntimeError("canary must run from the admitted immutable environment")
    required_environment = {
        "CUDA_VISIBLE_DEVICES": "",
        "NVIDIA_VISIBLE_DEVICES": "",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    mismatches = {key: os.environ.get(key) for key, expected in required_environment.items() if os.environ.get(key) != expected}
    if mismatches:
        raise RuntimeError(f"import canary isolation environment mismatch: {sorted(mismatches)}")
    observed = {name: metadata.version(name) for name in REQUIRED_DISTRIBUTIONS}
    if observed != REQUIRED_DISTRIBUTIONS:
        raise RuntimeError("controller import canary distribution identity mismatch")
    if not output.as_posix().startswith("/tmp/w64_aqa_qwen36_controller_import_"):
        raise RuntimeError("controller import receipt is outside admitted temporary root")


def run_canary(admission: dict[str, Any]) -> dict[str, Any]:
    blocked_events: list[str] = []
    weight_open_attempts: list[str] = []

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event.startswith(BLOCKED_EVENTS):
            blocked_events.append(event)
            raise RuntimeError(f"blocked import-canary side effect: {event}")
        if event == "open" and args and str(args[0]).lower().endswith(WEIGHT_SUFFIXES):
            weight_open_attempts.append(str(args[0]))
            raise RuntimeError("blocked model-weight file access during import canary")

    sys.addaudithook(audit)
    started = time.perf_counter()
    transformers = importlib.import_module("transformers")
    backend = importlib.import_module("transformers.models.qwen3_5_moe")
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    class_names = ("Qwen3_5MoeConfig", "Qwen3_5MoeForConditionalGeneration")
    class_resolution = {
        name: {
            "is_class": isinstance(getattr(backend, name, None), type),
            "module": getattr(getattr(backend, name, None), "__module__", None),
        }
        for name in class_names
    }
    if not all(value["is_class"] for value in class_resolution.values()):
        raise RuntimeError("required Qwen3.5-MoE classes did not resolve")
    return {
        "schema_version": "wave64.aqa.qwen36_controller_import_canary.v1",
        "program_id": "W64-AQA",
        "package_id": admission["package_id"],
        "status": "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING",
        "environment_root": Path(sys.prefix).as_posix(),
        "environment_lock_sha256": admission["environment"]["lock_sha256"],
        "python_version": platform.python_version(),
        "distribution_versions": REQUIRED_DISTRIBUTIONS,
        "transformers_imported_version": transformers.__version__,
        "class_resolution": class_resolution,
        "measurements": {"import_duration_ms": duration_ms},
        "isolation": {
            "offline": True,
            "cuda_hidden": True,
            "blocked_side_effect_events": blocked_events,
            "weight_file_open_attempts": weight_open_attempts,
        },
        "runtime_claims": {
            "model_library_imported": True,
            "required_classes_resolved": True,
            "model_constructed": False,
            "weights_opened": False,
            "tensor_allocation_requested": False,
            "gpu_or_lease_polled": False,
            "inference_performed": False,
            "environment_mutated": False,
            "role_activated": False,
            "product_authority": False,
        },
    }


def write_json_atomic_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite canary receipt: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    admission = load_admission(args.admission)
    validate_environment(admission, args.output)
    receipt = run_canary(admission)
    write_json_atomic_no_overwrite(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
