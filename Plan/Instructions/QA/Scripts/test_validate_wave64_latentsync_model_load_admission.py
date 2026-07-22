from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_model_load_admission.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_model_load_admission.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_model_load", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def value() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_real_admission_is_valid() -> None:
    assert MODULE.validate(value()) == []


def test_inference_authority_fails_closed() -> None:
    changed = copy.deepcopy(value())
    changed["authority"]["forward_inference"] = True
    assert "model-load admission exceeds load-only authority" in MODULE.validate(changed)


def test_fixture_consumption_fails_closed() -> None:
    changed = copy.deepcopy(value())
    changed["execution"]["fixture_consumption"] = True
    assert "model-load admission exceeds load-only execution" in MODULE.validate(changed)


def test_undersized_lease_fails_closed() -> None:
    changed = copy.deepcopy(value())
    changed["lease"]["minimum_reserved_peak_gib"] = 4
    assert "model-load lease capacity mismatch" in MODULE.validate(changed)
