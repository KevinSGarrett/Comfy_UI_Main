from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_wav2vec2_expanded_alignment_calibration.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_wav2vec2_expanded_alignment_execution_admission.json"
PLAN = ROOT / "Plan/10_REGISTRIES/wave64_forced_alignment_audio_event_expansion_plan.json"
SPEC = importlib.util.spec_from_file_location("run_expanded_alignment", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def plan() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def lease(now: datetime) -> dict:
    return {"valid": True, "lease_id": "lease_test", "project": "comfyui_main", "profile": "comfyui_model_qualification", "lease_mode": "exclusive", "reserved_peak_gib": 4.0, "safety_reserve_gib": 1.0, "expires_at": (now + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")}


def test_admission_and_partitions_are_exact() -> None:
    MODULE.validate_admission(admission(), PLAN)
    assert [case["case_id"] for case in MODULE.select_cases(admission(), plan(), "calibration")] == ["align_qwen_english", "align_ambience_refusal", "align_foley_refusal"]
    assert len(MODULE.select_cases(admission(), plan(), "held_out")) == 5


def test_sanitized_exact_lease_is_required() -> None:
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    assert MODULE.validate_lease(lease(now), admission(), now=now)["lease_id"] == "lease_test"
    tokenized = lease(now)
    tokenized["token"] = "secret"
    with pytest.raises(MODULE.ExpandedAlignmentError, match="must not contain a token"):
        MODULE.validate_lease(tokenized, admission(), now=now)
    foreign = lease(now)
    foreign["project"] = "maskfactory"
    with pytest.raises(MODULE.ExpandedAlignmentError, match="project mismatch"):
        MODULE.validate_lease(foreign, admission(), now=now)


def test_calibration_receipt_binds_plan_model_and_matched_control() -> None:
    value = {"status": "PASS_CALIBRATION_PARTITION_AND_PROCESS_EXIT_CLEANUP", "partition": "calibration", "plan_sha256": admission()["plan"]["sha256"], "package": {"revision": admission()["model"]["revision"]}, "results": [{"case_id": "align_qwen_english", "passed": True, "greedy_similarity": 0.95}]}
    assert MODULE.validate_calibration_receipt(value, admission()) == 0.95
    changed = copy.deepcopy(value)
    changed["plan_sha256"] = "0" * 64
    with pytest.raises(MODULE.ExpandedAlignmentError, match="plan identity"):
        MODULE.validate_calibration_receipt(changed, admission())


def test_policy_gates_refusal_diagnostic_and_mismatch() -> None:
    no_speech = {"speech_gate": False}
    case = {"policy": "REQUIRE_NO_SPEECH_ALIGNMENT"}
    assert MODULE.policy_result(case, no_speech, None) == (True, False)
    diagnostic = {"inference_complete": True}
    case = {"policy": "MEASURE_LANGUAGE_SCOPED_COVERAGE_NO_AUTHORITY"}
    assert MODULE.policy_result(case, diagnostic, None) == (True, False)
    mismatch = {"greedy_similarity": 0.70}
    case = {"policy": "REQUIRE_MATCH_SCORE_DROP_AT_LEAST_0_15_FROM_MATCHED_SOURCE"}
    assert MODULE.policy_result(case, mismatch, 0.90) == (True, False)


def test_authority_expansion_fails_closed() -> None:
    changed = admission()
    changed["authority"]["audio_event_execution"] = True
    with pytest.raises(MODULE.ExpandedAlignmentError, match="exceeds"):
        MODULE.validate_admission(changed, PLAN)


def test_model_environment_and_partition_substitution_fail_closed() -> None:
    changed = admission()
    changed["model"]["revision"] = "0" * 40
    with pytest.raises(MODULE.ExpandedAlignmentError, match="model identity"):
        MODULE.validate_admission(changed, PLAN)
    changed = admission()
    changed["environment"]["tree_manifest_sha256"] = "0" * 64
    with pytest.raises(MODULE.ExpandedAlignmentError, match="environment identity"):
        MODULE.validate_admission(changed, PLAN)
    changed = admission()
    changed["partitions"]["held_out"] = list(reversed(changed["partitions"]["held_out"]))
    with pytest.raises(MODULE.ExpandedAlignmentError, match="partition identity"):
        MODULE.validate_admission(changed, PLAN)
