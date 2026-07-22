#!/usr/bin/env python3
"""Run the CUDA-hidden, import-only Qwen3-ASR dependency canary."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time


EXPECTED_ENVIRONMENT_ROOT = Path(
    "/workspace/w64_aqa/environments/Qwen3-ASR-1.7B/"
    "qwen-asr-0.0.6-py3.12.13-cu124/"
    "241dfaab72cea25fe705693ef715e8368d171720ae3dc37e1c17ecc81b18ba22"
)
EXPECTED_DISTRIBUTIONS = {
    "qwen-asr": "0.0.6",
    "qwen-omni-utils": "0.0.9",
    "transformers": "4.57.6",
    "torch": "2.4.1+cu124",
}
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth")


def resident_bytes() -> int:
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("VmRSS is unavailable")


def validate_environment() -> None:
    if Path(sys.prefix).resolve() != EXPECTED_ENVIRONMENT_ROOT.resolve():
        raise RuntimeError("canary must run from the admitted isolated environment")
    required = {
        "CUDA_VISIBLE_DEVICES": "",
        "NVIDIA_VISIBLE_DEVICES": "none",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    mismatches = {
        key: os.environ.get(key)
        for key, expected in required.items()
        if os.environ.get(key) != expected
    }
    if mismatches:
        raise RuntimeError(f"import canary isolation environment mismatch: {sorted(mismatches)}")
    observed = {name: metadata.version(name) for name in EXPECTED_DISTRIBUTIONS}
    if observed != EXPECTED_DISTRIBUTIONS:
        raise RuntimeError("import canary distribution identity mismatch")


def write_json_atomic_no_overwrite(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite canary receipt: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
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


def run_canary() -> dict:
    validate_environment()
    blocked_events: list[str] = []
    weight_open_attempts: list[str] = []

    def audit(event: str, args: tuple) -> None:
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system"}:
            blocked_events.append(event)
            raise RuntimeError(f"blocked import-canary side effect: {event}")
        if event == "open" and args:
            candidate = str(args[0]).lower()
            if candidate.endswith(WEIGHT_SUFFIXES):
                weight_open_attempts.append(candidate)
                raise RuntimeError("blocked model-weight file access during import canary")

    sys.addaudithook(audit)
    rss_before = resident_bytes()
    started = time.perf_counter()
    qwen_asr = importlib.import_module("qwen_asr")
    backend = importlib.import_module("qwen_asr.core.transformers_backend")
    transformers = importlib.import_module("transformers")
    torch = importlib.import_module("torch")
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    rss_after = resident_bytes()

    required_classes = {
        "Qwen3ASRModel": getattr(qwen_asr, "Qwen3ASRModel", None),
        "Qwen3ASRConfig": getattr(backend, "Qwen3ASRConfig", None),
        "Qwen3ASRForConditionalGeneration": getattr(
            backend, "Qwen3ASRForConditionalGeneration", None
        ),
        "Qwen3ASRProcessor": getattr(backend, "Qwen3ASRProcessor", None),
    }
    class_resolution = {
        name: {
            "is_class": isinstance(value, type),
            "module": getattr(value, "__module__", None),
        }
        for name, value in required_classes.items()
    }
    if not all(item["is_class"] for item in class_resolution.values()):
        raise RuntimeError("required Qwen3-ASR class resolution failed")
    if blocked_events or weight_open_attempts:
        raise RuntimeError("import canary attempted a forbidden side effect")

    return {
        "schema_version": "wave64.aqa.qwen3_asr_import_canary.v1",
        "program_id": "W64-AQA",
        "package_id": "W64-AQA-PKG-QWEN3-ASR-17B",
        "status": "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING",
        "environment_root": Path(sys.prefix).as_posix(),
        "python_version": platform.python_version(),
        "distribution_versions": {
            **EXPECTED_DISTRIBUTIONS,
            "transformers_imported": transformers.__version__,
            "torch_imported": torch.__version__,
        },
        "class_resolution": class_resolution,
        "isolation": {
            "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
            "nvidia_visible_devices": os.environ["NVIDIA_VISIBLE_DEVICES"],
            "offline": True,
            "bytecode_writes_disabled": True,
            "blocked_side_effect_events": blocked_events,
            "weight_file_open_attempts": weight_open_attempts,
        },
        "measurements": {
            "import_duration_ms": duration_ms,
            "rss_before_bytes": rss_before,
            "rss_after_bytes": rss_after,
            "rss_delta_bytes": rss_after - rss_before,
        },
        "runtime_claims": {
            "model_library_imported": True,
            "required_classes_resolved": True,
            "model_constructed": False,
            "weights_opened": False,
            "tensor_allocation_requested": False,
            "gpu_or_lease_polled": False,
            "inference_performed": False,
            "service_changed": False,
            "role_activated": False,
            "product_authority": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = run_canary()
    write_json_atomic_no_overwrite(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
