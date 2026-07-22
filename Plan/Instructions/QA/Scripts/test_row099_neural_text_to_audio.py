from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_neural_text_to_audio.py"
SPEC = importlib.util.spec_from_file_location("compile_wave64_neural_text_to_audio", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {
        "TRK-W64-068",
        "TRK-W64-079",
        "TRK-W64-083",
        "TRK-W64-091",
    }
    assert admissions["TRK-W64-068"]["dependency_satisfied"] is True
    assert admissions["TRK-W64-068"]["row_complete"] is True
    for tracker_id in ("TRK-W64-079", "TRK-W64-083", "TRK-W64-091"):
        admission = admissions[tracker_id]
        assert admission["dependency_satisfied"] is False, tracker_id
        assert admission["row_complete"] is False, tracker_id
        assert admission["blocker_codes"], tracker_id
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is True
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row099_acceptance"] == "held"
    assert "ROW099_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_LIBRARY_NEURAL_TEXT_TO_AUDIO_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 7
    assert set(payload["required_gates"]) == set(MOD.REQUIRED_GATES)


def test_eligible_seeded_batch_is_deterministic_and_reconstructable():
    first = MOD.extract_fixture_record(ROOT, "eligible_engine_seeded_batch_routed")
    second = MOD.extract_fixture_record(ROOT, "eligible_engine_seeded_batch_routed")
    assert first == second
    assert first["decision"]["route"] == "candidate_batch"
    assert first["library_authority"] is False
    assert first["decision"]["product_completion"] is False
    assert first["seeded_batch"]["reconstructable"] is True
    assert first["seeded_batch"]["batch_sha256"]
    assert first["gate_results"]["seeded_batch"]["status"] == "pass"
    assert first["gate_results"]["candidate_only"]["status"] == "pass"
    assert len(first["seeded_batch"]["admitted_candidate_ids"]) == 3
    assert all(item["promotion_allowed"] is False for item in first["candidates"])


def test_missing_structured_prompt_is_blocked():
    record = MOD.extract_fixture_record(ROOT, "missing_structured_prompt_blocked")
    assert record["decision"]["route"] == "blocked"
    assert "MISSING_STRUCTURED_PROMPT" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["structured_prompt"]["status"] == "fail"
    assert record["seeded_batch"]["batch_sha256"] is None


def test_unregistered_engine_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "unregistered_engine_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "UNREGISTERED_ENGINE" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["engine_authority"]["status"] == "fail"


def test_rights_fail_closed_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "rights_fail_closed_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "PROMPT_RIGHTS_DENIED" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["rights"]["status"] == "fail"


def test_duration_gate_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "duration_gate_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "DURATION_OUT_OF_ENGINE_BAND" in record["decision"]["blocker_codes"]
    assert record["gate_results"]["seeded_batch"]["status"] == "fail"


def test_semantic_gate_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "semantic_gate_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "SEMANTIC_OUT_OF_BAND" in record["decision"]["blocker_codes"]


def test_uniqueness_duplicate_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "uniqueness_duplicate_rejected")
    assert record["decision"]["route"] == "blocked"
    assert "PCM_DUPLICATE" in record["decision"]["blocker_codes"]


def test_semantic_validator_rejects_tampered_batch_hash():
    record = MOD.extract_fixture_record(ROOT, "eligible_engine_seeded_batch_routed")
    mutated = deepcopy(record)
    mutated["seeded_batch"]["batch_sha256"] = "a" * 64
    mutated = MOD.seal_receipt(
        {k: v for k, v in mutated.items() if k != "receipt_sha256"}
    )
    with pytest.raises(MOD.NeuralTextToAudioError, match="seeded_batch_recompute_mismatch"):
        MOD.validate_route_semantics(mutated)


def test_semantic_validator_rejects_candidate_batch_with_failed_gate():
    record = MOD.extract_fixture_record(ROOT, "eligible_engine_seeded_batch_routed")
    mutated = deepcopy(record)
    mutated["gate_results"]["rights"] = {
        "status": "fail",
        "reason_codes": ["PROMPT_RIGHTS_DENIED"],
    }
    mutated = MOD.seal_receipt(
        {k: v for k, v in mutated.items() if k != "receipt_sha256"}
    )
    with pytest.raises(MOD.NeuralTextToAudioError, match="candidate_batch_with_failed_gate"):
        MOD.validate_route_semantics(mutated)


def test_schema_rejects_library_authority_true():
    record = MOD.extract_fixture_record(ROOT, "eligible_engine_seeded_batch_routed")
    mutated = deepcopy(record)
    mutated["library_authority"] = True
    mutated["receipt_sha256"] = "b" * 64
    with pytest.raises(Exception):
        MOD.validate_route_receipt(ROOT, mutated)
