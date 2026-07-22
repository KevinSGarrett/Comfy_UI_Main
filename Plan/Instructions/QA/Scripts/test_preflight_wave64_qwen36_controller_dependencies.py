from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/preflight_wave64_qwen36_controller_dependencies.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_dependency_preflight.schema.json"
SPEC = importlib.util.spec_from_file_location("qwen36_controller_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()  # noqa: S324


def make_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "Qwen3.6-35B-A3B-FP8" / MODULE.EXPECTED_REVISION
    root.mkdir(parents=True)
    values = {
        "config.json": {"model_type": "qwen3_6_moe", "architectures": ["Qwen3_6MoeForCausalLM"], "transformers_version": "5.2.0"},
        "generation_config.json": {"model_type": "qwen3_6_moe"},
        "tokenizer_config.json": {"tokenizer_class": "Qwen2Tokenizer"},
        "model.safetensors.index.json": {"weight_map": {"a": "model-00001-of-00002.safetensors", "b": "model-00002-of-00002.safetensors"}},
    }
    identities = {}
    for name, value in values.items():
        data = json.dumps(value, separators=(",", ":")).encode()
        (root / name).write_bytes(data)
        identities[name] = (len(data), git_blob(data))
    monkeypatch.setattr(MODULE, "METADATA_FILES", identities)
    return root


def test_missing_candidate_support_requires_new_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path, monkeypatch)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: None)
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda _model_type: [])
    receipt = MODULE.build_receipt(root, MODULE.OMNI_LOCK_SHA256)
    assert receipt["disposition"] == "NEW_LOCK_RESOLUTION_REQUIRED"
    assert receipt["compatible_lock_sha256"] is None
    assert not any(receipt["runtime_claims"].values())


def test_candidate_support_is_metadata_only_not_runtime_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path, monkeypatch)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: "5.2.0")
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda _model_type: ["transformers/models/qwen3_6_moe/configuration.py"])
    receipt = MODULE.build_receipt(root, MODULE.OMNI_LOCK_SHA256)
    assert receipt["disposition"] == "COMPATIBLE_WITH_CANDIDATE_LOCK_METADATA_ONLY"
    assert receipt["compatible_lock_sha256"] == MODULE.OMNI_LOCK_SHA256
    assert not any(receipt["runtime_claims"].values())


def test_admitted_metadata_mismatch_is_exact_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path, monkeypatch)
    (root / "config.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="admitted metadata identity mismatch: config.json"):
        MODULE.build_receipt(root, None)


def test_schema_accepts_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path, monkeypatch)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: None)
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda _model_type: [])
    receipt = MODULE.build_receipt(root, None)
    receipt["model_root"] = "/workspace/w64_aqa/models/controller/Qwen3.6-35B-A3B-FP8/" + MODULE.EXPECTED_REVISION
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(receipt)


def test_no_overwrite_and_no_forbidden_imports(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    MODULE.write_json_atomic_no_overwrite(output, {"ok": True})
    with pytest.raises(FileExistsError, match="overwrite"):
        MODULE.write_json_atomic_no_overwrite(output, {"ok": False})
    source = SCRIPT.read_text(encoding="utf-8").lower()
    tree = ast.parse(source)
    imported = {alias.name.split(".", 1)[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not imported.intersection({"torch", "transformers", "accelerate", "safetensors", "requests", "socket", "subprocess"})
    assert "from_pretrained" not in source
