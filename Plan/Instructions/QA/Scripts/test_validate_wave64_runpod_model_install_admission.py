from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_model_install_admission.py"
MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_runpod_qwen3_asr_17b_install_admission.json"
SPEC = importlib.util.spec_from_file_location("model_install_admission_validator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_is_valid_and_storage_only() -> None:
    data = load_manifest()
    assert MODULE.validate(data) == []
    assert "model_load" in data["authority"]["forbidden"]
    assert "lease_poll" in data["authority"]["forbidden"]


def test_revision_and_weight_hash_drift_fail() -> None:
    data = copy.deepcopy(load_manifest())
    data["source"]["revision"] = "0" * 40
    assert "source repository or revision mismatch" in MODULE.validate(data)
    data = copy.deepcopy(load_manifest())
    data["files"][6]["identity"] = "f" * 64
    assert "exact source file inventory mismatch" in MODULE.validate(data)


def test_runtime_authority_cannot_be_removed_from_forbidden_set() -> None:
    data = copy.deepcopy(load_manifest())
    data["authority"]["forbidden"].remove("model_load")
    assert "forbidden runtime authority is incomplete" in MODULE.validate(data)


def test_target_root_and_no_overwrite_are_exact() -> None:
    data = copy.deepcopy(load_manifest())
    data["storage"]["target_root"] = "/workspace/models/latest"
    data["storage"]["overwrite_forbidden"] = False
    errors = MODULE.validate(data)
    assert "target root mismatch" in errors
    assert "storage publish controls must fail closed" in errors
