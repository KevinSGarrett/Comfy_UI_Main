from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_internvl_import_canary.py"


def _module():
    spec = importlib.util.spec_from_file_location("internvl_import_canary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path):
    module = _module()
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "model"
    overlay = tmp_path / "overlay"
    source.mkdir()
    (overlay / "site_packages").mkdir(parents=True)
    code = source / "code.py"
    code.write_text("VALUE = 1\n", encoding="utf-8")
    manifest = overlay / "OVERLAY_MANIFEST.json"
    manifest.write_text("{}\n", encoding="utf-8")
    expected = {
        "resolved_classes": {"InternVLChatConfig": "pkg.Config", "InternVisionModel": "pkg.Vision", "InternVLChatModel": "pkg.Chat", "Qwen3ForCausalLM": "pkg.Qwen3"},
        "versions": {"python": "test", "torch": "test", "transformers": "test"},
        "stdout_lines": ["FlashAttention2 is not installed."],
    }
    material = {
        "source_root": str(source.resolve()),
        "custom_code_files": [{"filename": code.name, "bytes": code.stat().st_size, "sha256": module._sha256(code)}],
        "environment": {"root": str(overlay.resolve()), "manifest_sha256": module._sha256(manifest), "python": str(Path(sys.executable).resolve())},
        "expected_result": expected,
    }
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps({"lock_material": material, "lock_sha256": module._canonical_sha256(material)}), encoding="utf-8")
    result = {**expected, "has_flash_attn": False, "cuda_initialized_before": False, "cuda_initialized_after": False, "stderr_lines": []}
    return module, admission, source, result


def test_canary_enforces_exact_import_only_result_and_no_source_mutation(tmp_path: Path) -> None:
    module, admission, source, result = _fixture(tmp_path)
    receipt = module.run_canary(admission, lambda package: result if package == source.name else {})
    assert receipt["result"] == "PASS"
    assert receipt["authority"] == {"custom_code_import": True, "class_resolution": True, "config_instantiation": False, "model_instantiation": False, "weight_access": False, "model_load": False, "gpu_use": False, "inference": False}


def test_canary_rejects_drift_cuda_or_unexpected_output(tmp_path: Path) -> None:
    module, admission, _source, result = _fixture(tmp_path)
    data = json.loads(admission.read_text(encoding="utf-8"))
    data["lock_material"]["custom_code_files"][0]["bytes"] += 1
    admission.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(module.ImportCanaryError, match="lock digest"):
        module.run_canary(admission, lambda _: result)
    data["lock_sha256"] = module._canonical_sha256(data["lock_material"])
    admission.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(module.ImportCanaryError, match="custom code identity"):
        module.run_canary(admission, lambda _: result)
    module, admission, source, result = _fixture(tmp_path / "mutation")

    def mutating_executor(_package: str):
        cache = source / "__pycache__"
        cache.mkdir()
        (cache / "code.pyc").write_bytes(b"mutation")
        return result

    with pytest.raises(module.ImportCanaryError, match="bytecode mutation"):
        module.run_canary(admission, mutating_executor)
    module, admission, _source, result = _fixture(tmp_path / "fresh")
    result["cuda_initialized_after"] = True
    with pytest.raises(module.ImportCanaryError, match="CUDA initialized"):
        module.run_canary(admission, lambda _: result)
