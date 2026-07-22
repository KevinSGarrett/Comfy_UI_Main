from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_qwen3_asr_imports.py"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_asr_import_canary.schema.json"
SPEC = importlib.util.spec_from_file_location("canary_wave64_qwen3_asr_imports", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_atomic_receipt_write_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    MODULE.write_json_atomic_no_overwrite(output, {"ok": True})
    assert json.loads(output.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(FileExistsError, match="overwrite"):
        MODULE.write_json_atomic_no_overwrite(output, {"ok": False})


def test_environment_guard_rejects_visible_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE.sys, "prefix", str(MODULE.EXPECTED_ENVIRONMENT_ROOT))
    monkeypatch.setattr(MODULE.Path, "resolve", lambda self: self)
    for key, value in {
        "CUDA_VISIBLE_DEVICES": "0",
        "NVIDIA_VISIBLE_DEVICES": "none",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match="isolation environment mismatch"):
        MODULE.validate_environment()


def test_schema_accepts_minimal_valid_shape() -> None:
    class_item = {"is_class": True, "module": "qwen_asr.test"}
    receipt = {
        "schema_version": "wave64.aqa.qwen3_asr_import_canary.v1",
        "program_id": "W64-AQA",
        "package_id": "W64-AQA-PKG-QWEN3-ASR-17B",
        "status": "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING",
        "environment_root": MODULE.EXPECTED_ENVIRONMENT_ROOT.as_posix(),
        "python_version": "3.12.13",
        "distribution_versions": {
            "qwen-asr": "0.0.6",
            "qwen-omni-utils": "0.0.9",
            "transformers": "4.57.6",
            "torch": "2.4.1+cu124",
            "transformers_imported": "4.57.6",
            "torch_imported": "2.4.1+cu124",
        },
        "class_resolution": {
            "Qwen3ASRModel": class_item,
            "Qwen3ASRConfig": class_item,
            "Qwen3ASRForConditionalGeneration": class_item,
            "Qwen3ASRProcessor": class_item,
        },
        "isolation": {
            "cuda_visible_devices": "",
            "nvidia_visible_devices": "none",
            "offline": True,
            "bytecode_writes_disabled": True,
            "blocked_side_effect_events": [],
            "weight_file_open_attempts": [],
        },
        "measurements": {
            "import_duration_ms": 1.0,
            "rss_before_bytes": 1,
            "rss_after_bytes": 2,
            "rss_delta_bytes": 1,
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
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(receipt)


def test_source_contains_no_model_construction_inference_or_cuda_api_calls() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden_calls = {
        "from_pretrained",
        "transcribe",
        "align",
        "cuda",
        "tensor",
        "empty",
        "zeros",
        "ones",
    }
    assert not called_attributes.intersection(forbidden_calls)
    assert "Qwen3ASRModel(" not in source


def test_expected_distribution_identity_is_exact() -> None:
    assert MODULE.EXPECTED_DISTRIBUTIONS == {
        "qwen-asr": "0.0.6",
        "qwen-omni-utils": "0.0.9",
        "transformers": "4.57.6",
        "torch": "2.4.1+cu124",
    }
