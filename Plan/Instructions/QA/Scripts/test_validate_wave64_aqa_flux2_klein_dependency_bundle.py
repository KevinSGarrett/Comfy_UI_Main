from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_dependency_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_flux2_dependencies", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def value(module):
    return json.loads((ROOT / module.BUNDLE_PATH).read_text(encoding="utf-8"))


def resign(module, candidate):
    candidate["bundle_id"] = module.bundle_id(candidate)
    return candidate


def test_exact_bundle_is_identity_complete_but_current_pod_incomplete() -> None:
    module = load_module()
    candidate = value(module)
    module.validate_bundle(ROOT, candidate)
    assert candidate["authority"]["component_identity"] is True
    assert candidate["authority"]["current_pod_complete"] is False
    assert [item["current_pod_state"] for item in candidate["components"]] == [
        "PROMOTED_HASH_VERIFIED", "NOT_IN_ACCEPTED_PROMOTED_LEDGER", "NOT_IN_ACCEPTED_PROMOTED_LEDGER"
    ]


def test_bundle_identity_drift_is_rejected() -> None:
    module = load_module()
    candidate = value(module)
    candidate["components"][1]["bytes"] += 1
    with pytest.raises(module.DependencyBundleError, match="identity drift"):
        module.validate_bundle(ROOT, candidate)


def test_dev_vae_cannot_substitute_for_klein_companion() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["components"][2]["sha256"] = candidate["components"][2]["local_source"]["sha256"]
    candidate = resign(module, candidate)
    with pytest.raises(module.DependencyBundleError, match="Dev VAE"):
        module.validate_bundle(ROOT, candidate)


def test_schema_rejects_runtime_or_promotion_authority() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["authority"]["model_load"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_bundle(ROOT, candidate)
