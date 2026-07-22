from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_current_pod_reconciliation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_flux2_current_pod", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def value(module):
    return json.loads((ROOT / module.RECONCILIATION_PATH).read_text(encoding="utf-8"))


def resign(module, candidate):
    candidate["reconciliation_id"] = module.reconciliation_id(candidate)
    return candidate


def test_current_pod_reconciliation_accepts_only_observed_scope() -> None:
    module = load_module()
    candidate = value(module)
    module.validate_reconciliation(ROOT, candidate)
    assert candidate["authority"]["current_pod_object_info"] is True
    assert candidate["authority"]["text_encoder_identity"] is True
    assert candidate["authority"]["exact_klein_vae_identity"] is False
    assert candidate["authority"]["runtime"] is False


def test_wrong_vae_cannot_be_marked_exact() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["components"][2]["match"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_reconciliation(ROOT, candidate)


def test_runtime_authority_cannot_be_self_granted() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["authority"]["runtime"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_reconciliation(ROOT, candidate)


def test_text_encoder_identity_drift_is_rejected() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["components"][1]["observed"]["sha256"] = "0" * 64
    candidate = resign(module, candidate)
    with pytest.raises(module.CurrentPodReconciliationError, match="text_encoder"):
        module.validate_reconciliation(ROOT, candidate)
