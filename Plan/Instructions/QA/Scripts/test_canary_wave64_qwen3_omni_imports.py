from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_qwen3_omni_imports.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_qwen3_omni_import_canary_admission.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_omni_import_canary.schema.json"
RECEIPT = ROOT / "Plan/Tracker/Evidence/W64_AQA_QWEN3_OMNI_IMPORT_CANARY_20260722T025500Z/remote_import_canary.receipt.json"
SPEC = importlib.util.spec_from_file_location("canary_qwen3_omni_imports", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_real_admission_is_hash_bound_and_import_only() -> None:
    admission = MODULE.load_admission(ADMISSION)
    assert admission["authority"]["model_library_import"] is True
    assert not any(
        value
        for key, value in admission["authority"].items()
        if key not in {"model_library_import", "required_class_resolution"}
    )


def test_changed_admission_fails_closed(tmp_path: Path) -> None:
    changed = tmp_path / "admission.json"
    changed.write_bytes(ADMISSION.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="admission hash mismatch"):
        MODULE.load_admission(changed)


def test_atomic_receipt_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    MODULE.write_json_atomic_no_overwrite(output, {"ok": True})
    with pytest.raises(FileExistsError, match="overwrite"):
        MODULE.write_json_atomic_no_overwrite(output, {"ok": False})


def test_visible_cuda_and_outside_receipt_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    monkeypatch.setattr(MODULE.sys, "prefix", admission["environment_root"])
    monkeypatch.setattr(MODULE.Path, "resolve", lambda self: self)
    for key, value in admission["isolation_environment"].items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    with pytest.raises(RuntimeError, match="isolation environment mismatch"):
        MODULE.validate_environment(admission, Path("/workspace/w64_aqa/import_canary_control/x/r.json"))


def test_schema_and_required_classes_are_exact() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    assert admission["required_classes"] == [
        "Qwen3OmniMoeConfig",
        "Qwen3OmniMoeProcessor",
        "Qwen3OmniMoeForConditionalGeneration",
    ]


def test_real_receipt_passes_schema_and_retains_fail_closed_claims() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(receipt)
    assert receipt["runtime_claims"]["model_library_imported"] is True
    assert receipt["runtime_claims"]["required_classes_resolved"] is True
    assert not any(
        value
        for key, value in receipt["runtime_claims"].items()
        if key not in {"model_library_imported", "required_classes_resolved"}
    )


def test_source_has_no_model_construction_inference_or_cuda_api_calls() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not called.intersection(
        {"from_pretrained", "generate", "cuda", "tensor", "empty", "zeros", "ones"}
    )
    assert "nvidia-smi" not in source


def test_network_and_weight_operations_are_blocked() -> None:
    assert {"socket.connect", "socket.getaddrinfo", "socket.listen", "subprocess.Popen"}.issubset(
        MODULE.BLOCKED_AUDIT_EVENTS
    )
    assert ".safetensors" in MODULE.WEIGHT_SUFFIXES
