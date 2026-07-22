from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_qwen36_controller_imports.py"
SPEC = importlib.util.spec_from_file_location("qwen36_import_canary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def admission() -> dict:
    return {"package_id": "W64-AQA-PKG-QWEN36-35B-A3B", "environment": {"lock_sha256": "a" * 64}}


def test_class_resolution_passes_without_runtime_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    class Config:
        pass

    class Model:
        pass

    modules = {
        "transformers": SimpleNamespace(__version__="5.2.0"),
        "transformers.models.qwen3_5_moe": SimpleNamespace(Qwen3_5MoeConfig=Config, Qwen3_5MoeForConditionalGeneration=Model),
    }
    monkeypatch.setattr(MODULE.importlib, "import_module", lambda name: modules[name])
    receipt = MODULE.run_canary(admission())
    assert receipt["status"] == "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING"
    assert receipt["runtime_claims"]["model_library_imported"] is True
    assert receipt["runtime_claims"]["model_constructed"] is False
    assert receipt["runtime_claims"]["weights_opened"] is False


def test_missing_class_fails_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    modules = {"transformers": SimpleNamespace(__version__="5.2.0"), "transformers.models.qwen3_5_moe": SimpleNamespace()}
    monkeypatch.setattr(MODULE.importlib, "import_module", lambda name: modules[name])
    with pytest.raises(RuntimeError, match="required Qwen3.5-MoE classes did not resolve"):
        MODULE.run_canary(admission())


def test_admission_hash_mismatch_fails(tmp_path: Path) -> None:
    path = tmp_path / "admission.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="admission hash mismatch"):
        MODULE.load_admission(path)


def test_source_has_no_model_construction_or_process_calls() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower()
    ast.parse(source)
    assert "from_pretrained" not in source
    assert "subprocess.run" not in source
    assert "torch.cuda" not in source
