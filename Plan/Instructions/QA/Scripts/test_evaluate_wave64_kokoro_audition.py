from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/evaluate_wave64_kokoro_audition.py"
SPEC = importlib.util.spec_from_file_location("wave64_kokoro_evaluator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_metric_gate_requires_all_automated_checks() -> None:
    gates = MODULE.metric_gate(
        wer=0.1,
        dnsmos_ovrl=2.5,
        dnsmos_floor=1.9,
        continuity_similarity=0.9,
        continuity_threshold=0.33,
        timing_pass=True,
        max_wer=0.2,
    )
    assert all(gates.values())
    assert MODULE.metric_gate(
        wer=0.21,
        dnsmos_ovrl=2.5,
        dnsmos_floor=1.9,
        continuity_similarity=0.9,
        continuity_threshold=0.33,
        timing_pass=True,
        max_wer=0.2,
    )["asr_wer_pass"] is False


def test_selection_uses_dns_mos_then_ordinal() -> None:
    rows = [
        {"ordinal": 2, "gates": {"a": True}, "metrics": {"dnsmos": {"OVRL": 3.0}}},
        {"ordinal": 1, "gates": {"a": True}, "metrics": {"dnsmos": {"OVRL": 3.0}}},
        {"ordinal": 3, "gates": {"a": False}, "metrics": {"dnsmos": {"OVRL": 4.0}}},
    ]
    assert MODULE.select_candidate(rows)["ordinal"] == 1


def test_selection_returns_none_when_no_candidate_is_eligible() -> None:
    rows = [{"ordinal": 1, "gates": {"a": False}, "metrics": {"dnsmos": {"OVRL": 5.0}}}]
    assert MODULE.select_candidate(rows) is None


def test_unvalidated_speaker_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="not validated"):
        MODULE.speaker_threshold(
            {"threshold_validation": {"speaker_disjoint_validation_pass": False, "threshold": 0.3}}
        )


def test_speaker_threshold_requires_deployment_permission() -> None:
    with pytest.raises(ValueError, match="deployment is not allowed"):
        MODULE.speaker_threshold(
            {
                "threshold_validation": {
                    "speaker_disjoint_validation_pass": True,
                    "threshold_deployment_allowed_for_chain_specific_evaluation": False,
                    "threshold": 0.3,
                }
            }
        )


def test_manifest_verifier_accepts_immutable_batch_and_rejects_retry_flag() -> None:
    path = (
        SCRIPT.parents[3]
        / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
        / "w64_kokoro_audition_20260715T131034-0500/kokoro_audition_manifest.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(MODULE.verify_manifest(payload, path)) == 3
    drifted = deepcopy(payload)
    drifted["candidates"][1]["retry_count"] = 1
    with pytest.raises(ValueError, match="retry count mismatch"):
        MODULE.verify_manifest(drifted, path)


def test_focused_delivery_is_not_an_emotion_gate() -> None:
    assert "emotion" not in MODULE.metric_gate(
        wer=0.0,
        dnsmos_ovrl=3.0,
        dnsmos_floor=2.0,
        continuity_similarity=0.9,
        continuity_threshold=0.3,
        timing_pass=True,
        max_wer=0.2,
    )
