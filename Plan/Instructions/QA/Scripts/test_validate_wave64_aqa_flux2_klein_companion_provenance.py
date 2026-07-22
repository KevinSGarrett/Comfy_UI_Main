from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_companion_provenance.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_flux2_companion_provenance", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def value(module):
    return json.loads((ROOT / module.DECISION_PATH).read_text(encoding="utf-8"))


def resign(module, candidate):
    candidate["decision_id"] = module.content_id(candidate)
    return candidate


def test_exact_decision_is_fail_closed() -> None:
    module = load_module()
    candidate = value(module)
    module.validate_decision(ROOT, candidate)
    assert candidate["authority"]["upstream_family_license_observed"] is True
    assert candidate["authority"]["exact_companion_redistribution"] is False
    assert candidate["decision"].endswith("NOT_ESTABLISHED")


def test_byte_distinct_text_encoder_cannot_be_declared_equivalent() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["upstream_family"]["text_encoder_distribution"]["total_file_bytes"] = candidate["selected_companions"][0]["bytes"]
    candidate = resign(module, candidate)
    with pytest.raises(module.CompanionProvenanceError, match="byte-equal"):
        module.validate_decision(ROOT, candidate)


def test_byte_distinct_vae_cannot_be_declared_equivalent() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["byte_equivalence"]["vae"] = True
    candidate = resign(module, candidate)
    with pytest.raises((module.CompanionProvenanceError, Exception)):
        module.validate_decision(ROOT, candidate)


def test_redistribution_authority_cannot_be_self_granted() -> None:
    module = load_module()
    candidate = copy.deepcopy(value(module))
    candidate["authority"]["exact_companion_redistribution"] = True
    candidate = resign(module, candidate)
    with pytest.raises(Exception):
        module.validate_decision(ROOT, candidate)
