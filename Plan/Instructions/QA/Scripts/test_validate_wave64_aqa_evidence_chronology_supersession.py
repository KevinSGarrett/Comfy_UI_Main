from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_evidence_chronology_supersession.py"
EVIDENCE = ROOT / "Plan/Tracker/Evidence/W64_AQA_EVIDENCE_CHRONOLOGY_SUPERSESSION_20260722T182334Z.json"
SPEC = importlib.util.spec_from_file_location("chronology_validator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_supersession_is_valid() -> None:
    assert MODULE.validate(ROOT, load()) == []


def test_source_hash_drift_fails() -> None:
    value = copy.deepcopy(load())
    value["records"][0]["sha256"] = "0" * 64
    assert any("source hash mismatch" in error for error in MODULE.validate(ROOT, value))


def test_false_chronology_claim_fails() -> None:
    value = copy.deepcopy(load())
    value["records"][0]["invalid_recorded_at_utc"] = "2026-07-22T17:00:00Z"
    assert any("source chronology was not invalid" in error for error in MODULE.validate(ROOT, value))
