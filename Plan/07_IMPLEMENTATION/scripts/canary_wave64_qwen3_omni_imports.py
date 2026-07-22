#!/usr/bin/env python3
"""Run the admitted CUDA-hidden, offline, import-only Qwen3-Omni canary."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import ipaddress
import json
import os
from pathlib import Path
import platform
import socket
import sys
import tempfile
import time


EXPECTED_ADMISSION_SHA256 = "c25935363d2e641d584a7a0fa56e45be3048a1404be315f8c93bda3cf191d2c0"
WEIGHT_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".gguf")
RECORDED_NON_IO_AUDIT_EVENTS = {"socket.__new__"}
BLOCKED_AUDIT_EVENTS = {
    "socket.bind",
    "socket.connect",
    "socket.connect_ex",
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.listen",
    "socket.sendto",
    "subprocess.Popen",
    "os.system",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_admission(path: Path) -> dict:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise RuntimeError("Omni import canary admission hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    if admission.get("status") != "IMPORT_ONLY_CANARY_ADMITTED_EXECUTION_PENDING":
        raise RuntimeError("Omni import canary is not admitted")
    authority = admission.get("authority", {})
    if authority.get("model_library_import") is not True or authority.get(
        "required_class_resolution"
    ) is not True:
        raise RuntimeError("Omni import authority is missing")
    forbidden = set(authority) - {"model_library_import", "required_class_resolution"}
    if any(authority.get(key) for key in forbidden):
        raise RuntimeError("Omni import admission exceeds import-only authority")
    return admission


def is_loopback_ephemeral_bind_probe(args: tuple) -> bool:
    if len(args) < 2:
        return False
    candidate_socket, address = args[0], args[1]
    if not isinstance(address, tuple) or len(address) < 2:
        return False
    try:
        host = ipaddress.ip_address(address[0])
        port = int(address[1])
    except (TypeError, ValueError):
        return False
    return (
        host.is_loopback
        and port == 0
        and getattr(candidate_socket, "family", None) in {socket.AF_INET, socket.AF_INET6}
    )


def resident_bytes() -> int:
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("VmRSS is unavailable")


def validate_environment(admission: dict, output: Path) -> None:
    expected_root = Path(admission["environment_root"])
    if Path(sys.prefix).resolve() != expected_root.resolve():
        raise RuntimeError("canary must run from the admitted isolated environment")
    mismatches = {
        key: os.environ.get(key)
        for key, expected in admission["isolation_environment"].items()
        if os.environ.get(key) != expected
    }
    if mismatches:
        raise RuntimeError(f"import canary isolation environment mismatch: {sorted(mismatches)}")
    observed = {
        name: metadata.version(name) for name in admission["distribution_versions"]
    }
    if observed != admission["distribution_versions"]:
        raise RuntimeError("import canary distribution identity mismatch")
    if not output.as_posix().startswith(admission["receipt_root_prefix"]):
        raise RuntimeError("import canary receipt is outside admitted control root")


def write_json_atomic_no_overwrite(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def run_canary(admission: dict) -> dict:
    blocked_events: list[str] = []
    socket_create_events: list[str] = []
    loopback_ephemeral_bind_probes: list[str] = []
    weight_open_attempts: list[str] = []

    def audit(event: str, args: tuple) -> None:
        if event in RECORDED_NON_IO_AUDIT_EVENTS:
            socket_create_events.append(event)
            return
        if event == "socket.bind" and is_loopback_ephemeral_bind_probe(args):
            loopback_ephemeral_bind_probes.append(event)
            return
        if event in BLOCKED_AUDIT_EVENTS:
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
    imported = {
        name: importlib.import_module(name) for name in admission["allowed_imports"]
    }
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    rss_after = resident_bytes()
    backend = imported["transformers.models.qwen3_omni_moe"]
    class_resolution = {
        name: {
            "is_class": isinstance(getattr(backend, name, None), type),
            "module": getattr(getattr(backend, name, None), "__module__", None),
        }
        for name in admission["required_classes"]
    }
    if not all(item["is_class"] for item in class_resolution.values()):
        raise RuntimeError("required Qwen3-Omni class resolution failed")
    if blocked_events or weight_open_attempts:
        raise RuntimeError("Omni import canary attempted a forbidden side effect")
    return {
        "schema_version": "wave64.aqa.qwen3_omni_import_canary.v1",
        "program_id": "W64-AQA",
        "package_id": admission["package_id"],
        "status": "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING",
        "environment_root": Path(sys.prefix).as_posix(),
        "python_version": platform.python_version(),
        "distribution_versions": admission["distribution_versions"],
        "imported_versions": {
            "transformers": imported["transformers"].__version__,
            "torch": imported["torch"].__version__,
            "torchvision": imported["torchvision"].__version__,
        },
        "class_resolution": class_resolution,
        "isolation": {
            "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
            "nvidia_visible_devices": os.environ["NVIDIA_VISIBLE_DEVICES"],
            "offline": True,
            "bytecode_writes_disabled": True,
            "blocked_side_effect_events": blocked_events,
            "socket_create_event_count": len(socket_create_events),
            "loopback_ephemeral_bind_probe_count": len(loopback_ephemeral_bind_probes),
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
            "audio_or_av_authority": False,
            "product_authority": False,
        },
    }


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
