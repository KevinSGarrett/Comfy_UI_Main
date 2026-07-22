from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_dependency_overlay_admission.py"


def load_module():
    spec = importlib.util.spec_from_file_location("flux2_overlay_admission", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def value(module):
    return json.loads((ROOT / module.ADMISSION_PATH).read_text(encoding="utf-8"))


def resign(module, candidate):
    candidate["admission_id"] = module.admission_id(candidate)
    return candidate


def test_exact_overlay_is_built_and_cpu_import_qualified() -> None:
    module = load_module()
    candidate = value(module)
    module.validate_admission(ROOT, candidate)
    assert candidate["authority"]["exact_resolution_prepared"] is True
    assert candidate["authority"]["overlay_built"] is True
    assert candidate["authority"]["dependency_import_compatibility"] is True
    assert candidate["authority"]["live_service_mutation"] is False


def test_wheel_hash_drift_is_rejected() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["overlay"]["packages"][0]["sha256"] = "0" * 64
    candidate = resign(module, candidate)
    with pytest.raises(module.OverlayAdmissionError, match="resolution drift"):
        module.validate_admission(ROOT, candidate)


def test_runtime_authority_cannot_be_granted() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["authority"]["runtime"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_admission(ROOT, candidate)
