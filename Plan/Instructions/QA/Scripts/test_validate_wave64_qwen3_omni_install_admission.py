from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_qwen3_omni_install_admission.py"
MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_runpod_qwen3_omni_30b_a3b_thinking_install_admission.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_omni_install_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("qwen3_omni_install_admission", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_is_schema_valid_exact_and_storage_only() -> None:
    data = load_manifest()
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(data)
    assert MODULE.validate(data) == []
    assert len(data["files"]) == 26
    assert sum(item["identity_kind"] == "sha256" for item in data["files"]) == 16
    assert "gpu_probe" in data["authority"]["forbidden"]
    assert "lease_poll" in data["authority"]["forbidden"]


def test_any_shard_hash_or_revision_drift_fails() -> None:
    data = copy.deepcopy(load_manifest())
    shard = next(item for item in data["files"] if item["identity_kind"] == "sha256")
    shard["identity"] = "f" * 64
    assert "canonical admission manifest identity mismatch" in MODULE.validate(data)
    data = copy.deepcopy(load_manifest())
    data["source"]["revision"] = "0" * 40
    errors = MODULE.validate(data)
    assert "canonical admission manifest identity mismatch" in errors
    assert "source repository or revision mismatch" in errors


def test_runtime_authority_and_storage_controls_fail_closed() -> None:
    data = copy.deepcopy(load_manifest())
    data["authority"]["forbidden"].remove("model_load")
    data["storage"]["overwrite_forbidden"] = False
    errors = MODULE.validate(data)
    assert "forbidden runtime authority is incomplete" in errors
    assert "storage publish controls must fail closed" in errors
