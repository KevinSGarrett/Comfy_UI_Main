#!/usr/bin/env python3
"""Build a fresh controller environment with the qualified atomic builder."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any


EXPECTED_ADMISSION_SHA256 = "3d9fb161f2801d82e14ace86641501443b804e9a476ccc9b76182825e3058f2f"
EXPECTED_PACKAGE_ID = "W64-AQA-PKG-QWEN36-35B-A3B"
EXPECTED_REVISION = "95a723d08a9490559dae23d0cff1d9466213d989"
EXPECTED_LOCK_SHA256 = "a19d160721dfb74cf89bc70eebec10f45b2e6f58b7a109726d658db7d361277c"
BASE_PATH = Path(__file__).with_name("build_wave64_qwen3_omni_python_environment.py")


def load_base_builder():
    spec = importlib.util.spec_from_file_location("wave64_qualified_atomic_environment_builder", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("qualified atomic environment builder is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.EXPECTED_ADMISSION_SHA256 = EXPECTED_ADMISSION_SHA256
    module.EXPECTED_PACKAGE_ID = EXPECTED_PACKAGE_ID
    module.EXPECTED_LOCK_SHA256 = EXPECTED_LOCK_SHA256
    return module


def controller_write_receipt(base: Any, path: Path, receipt: dict[str, Any]) -> None:
    payload = dict(receipt)
    payload["schema_version"] = "wave64.aqa.qwen36_controller_python_environment_build_receipt.v1"
    payload["source_revision"] = EXPECTED_REVISION
    payload.pop("admission_commit", None)
    payload["authority"] = {
        "environment_installed": True,
        "import_qualified": False,
        "model_constructed": False,
        "weights_opened": False,
        "gpu_or_lease_polled": False,
        "runtime_qualified": False,
        "role_operational": False,
        "product_authority": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.installing")
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise base.BuildError("receipt target already exists")
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def configure_builder(base: Any) -> Any:
    original_write_receipt = base.write_receipt
    original_run = base.run

    def controller_run(
        command: list[str], *, input_text: str | None = None
    ) -> str:
        bounded = list(command)
        if bounded[:3] == ["uv", "pip", "sync"] and "--no-cache" not in bounded:
            bounded.insert(3, "--no-cache")
        return original_run(bounded, input_text=input_text)

    base.run = controller_run
    base.write_receipt = lambda path, receipt: controller_write_receipt(
        base, path, receipt
    )
    base._controller_original_write_receipt = original_write_receipt
    base._controller_original_run = original_run
    return base


def build(admission: Path, lock: Path, receipt: Path, active_python: str) -> dict[str, Any]:
    base = configure_builder(load_base_builder())
    result = base.build(admission, lock, receipt, active_python)
    if result["status"] not in {"CREATED_VERIFIED_ENVIRONMENT", "REUSED_VERIFIED_ENVIRONMENT"}:
        raise base.BuildError("unexpected controller environment build disposition")
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--active-python", default="python3")
    args = parser.parse_args()
    if sha256_file(args.admission) != EXPECTED_ADMISSION_SHA256:
        parser.error("controller environment admission hash mismatch")
    try:
        print(json.dumps(build(args.admission, args.lock, args.receipt, args.active_python), sort_keys=True))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
