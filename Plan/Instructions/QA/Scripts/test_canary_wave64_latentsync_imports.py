from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_latentsync_imports.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_import_canary_admission.json"
SPEC = importlib.util.spec_from_file_location("canary_latentsync_imports", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_authoritative_admission_is_hash_bound() -> None:
    assert MODULE.load_admission(ADMISSION)["code"]["commit"] == MODULE.EXPECTED_COMMIT


def test_changed_admission_fails_closed(tmp_path: Path) -> None:
    changed = tmp_path / "admission.json"
    changed.write_text(json.dumps(load_admission()), encoding="utf-8")
    with pytest.raises(MODULE.CanaryError, match="admission hash mismatch"):
        MODULE.load_admission(changed)


def test_runtime_authority_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    admission = copy.deepcopy(load_admission())
    admission["authority"]["model_construction"] = True
    monkeypatch.setattr(MODULE, "sha256_file", lambda _path: MODULE.EXPECTED_ADMISSION_SHA256)
    monkeypatch.setattr(MODULE.json, "loads", lambda _text: admission)
    with pytest.raises(MODULE.CanaryError, match="exceeds import-only authority"):
        MODULE.load_admission(ADMISSION)


def test_receipt_write_replays_exactly(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    receipt = {"status": "PASS"}
    assert MODULE.write_or_verify_receipt(path, receipt) == "CREATED_VERIFIED_IMPORT_CANARY"
    assert MODULE.write_or_verify_receipt(path, receipt) == "REUSED_VERIFIED_IMPORT_CANARY"
    with pytest.raises(MODULE.CanaryError, match="differs from replay"):
        MODULE.write_or_verify_receipt(path, {"status": "CHANGED"})


def test_source_contains_no_weight_tensor_gpu_or_inference_operations() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = [
        "nvidia-smi", "cuda.is_available", "cuda.get_device", "from_pretrained(",
        "torch.tensor(", ".to(\"cuda", ".generate(", "LipsyncPipeline(",
    ]
    assert all(token not in source for token in forbidden)
