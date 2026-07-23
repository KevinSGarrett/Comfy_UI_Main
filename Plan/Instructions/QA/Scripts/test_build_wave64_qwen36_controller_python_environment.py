from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_qwen36_controller_python_environment.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_qwen36_controller_python_environment_admission.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_python_environment_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("qwen36_controller_environment_builder", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_admission_is_schema_valid_and_fresh_controller_scoped() -> None:
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(admission)
    assert admission["package_id"] == MODULE.EXPECTED_PACKAGE_ID
    assert "/Qwen3.6-35B-A3B-FP8/" in admission["targets"]["environment_root"]
    assert admission["targets"]["existing_omni_environment_mutable"] is False
    assert admission["authority"]["gpu_or_lease_poll"] is False


def test_base_builder_is_rebound_to_controller_identity() -> None:
    base = MODULE.load_base_builder()
    assert base.EXPECTED_PACKAGE_ID == MODULE.EXPECTED_PACKAGE_ID
    assert base.EXPECTED_LOCK_SHA256 == MODULE.EXPECTED_LOCK_SHA256
    assert base.EXPECTED_ADMISSION_SHA256 == MODULE.EXPECTED_ADMISSION_SHA256


def test_controller_receipt_adapter_preserves_fail_closed_authority(tmp_path: Path) -> None:
    base = SimpleNamespace(BuildError=RuntimeError)
    target = tmp_path / "receipt.json"
    MODULE.controller_write_receipt(base, target, {"schema_version": "old", "admission_commit": "old", "status": "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING"})
    receipt = json.loads(target.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "wave64.aqa.qwen36_controller_python_environment_build_receipt.v1"
    assert "admission_commit" not in receipt
    assert receipt["authority"]["environment_installed"] is True
    assert receipt["authority"]["import_qualified"] is False
    assert receipt["authority"]["runtime_qualified"] is False


def test_controller_builder_disables_duplicate_uv_cache_storage() -> None:
    calls = []

    def run(command: list[str], *, input_text: str | None = None) -> str:
        calls.append((command, input_text, os.environ.get("UV_CONCURRENT_INSTALLS")))
        return "ok"

    base = SimpleNamespace(run=run, write_receipt=lambda *_: None)
    configured = MODULE.configure_builder(base)
    configured.run(
        ["uv", "pip", "sync", "--python", "/staging/bin/python", "lock.toml"]
    )
    configured.run(["uv", "pip", "check", "--python", "/staging/bin/python"])
    assert calls[0][0] == [
        "uv",
        "pip",
        "sync",
        "--no-cache",
        "--link-mode=copy",
        "--python",
        "/staging/bin/python",
        "lock.toml",
    ]
    assert calls[0][2] == "1"
    assert "--no-cache" not in calls[1][0]
    assert "--link-mode=copy" not in calls[1][0]


def test_non_pep751_canonical_lock_gets_hash_exact_transient_alias(
    tmp_path: Path,
) -> None:
    source = tmp_path / "wave64_controller_lock.pylock.toml"
    source.write_bytes(b"qualified lock bytes")
    original = MODULE.EXPECTED_LOCK_SHA256
    MODULE.EXPECTED_LOCK_SHA256 = MODULE.sha256_file(source)
    try:
        with MODULE.pep751_lock_alias(source) as alias:
            assert alias.name == "pylock.qwen36.toml"
            assert alias.read_bytes() == source.read_bytes()
        assert not alias.exists()
        assert source.read_bytes() == b"qualified lock bytes"
    finally:
        MODULE.EXPECTED_LOCK_SHA256 = original
