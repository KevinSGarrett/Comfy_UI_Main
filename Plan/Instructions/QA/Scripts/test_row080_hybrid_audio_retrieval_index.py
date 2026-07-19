from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/query_wave64_hybrid_audio_retrieval_index.py"
SPEC = importlib.util.spec_from_file_location("query_wave64_hybrid_audio_retrieval_index", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_dependency_admissions_fail_closed_on_current_hold_deltas():
    admissions = MOD.evaluate_all_dependency_admissions(ROOT)
    assert set(admissions) == {"TRK-W64-069", "TRK-W64-077", "TRK-W64-079"}
    for tracker_id, admission in admissions.items():
        assert admission["dependency_satisfied"] is False
        assert admission["row_complete"] is False
        assert admission["blocker_codes"]
    assert not all(item["dependency_satisfied"] for item in admissions.values())


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row080_acceptance"] == "held"
    assert "ROW069_ROW077_ROW079_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_LIBRARY_HYBRID_RETRIEVAL_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_channels"]) == set(MOD.REQUIRED_CHANNELS)


def test_deterministic_repeat_same_ordered_candidate_set():
    first = MOD.extract_fixture_record(ROOT, "deterministic_repeat_query")
    second = MOD.extract_fixture_record(ROOT, "deterministic_repeat_query")
    assert first == second
    assert first["ordered_candidate_set_sha256"] == second["ordered_candidate_set_sha256"]
    assert first["query_sha256"] == second["query_sha256"]
    assert first["decision"]["route"] == "return_candidates"
    assert first["library_authority"] is False
    assert first["candidates"]
    assert first["candidates"][0]["rank"] == 1


def test_canonical_dedup_collapses_duplicate_content_hashes():
    record = MOD.extract_fixture_record(ROOT, "canonical_dedup_collapses_duplicates")
    pcm_values = [item["canonical_pcm_sha256"] for item in record["candidates"]]
    assert len(pcm_values) == len(set(pcm_values))
    excluded = {
        item["asset_id"]
        for item in record["exclusions"]
        if "CANONICAL_CONTENT_HASH_DUPLICATE" in item["reason_codes"]
    }
    assert "fixture:heel_hardwood_b_dup" in excluded
    assert all(item["representative"] is True for item in record["candidates"])


def test_stale_generation_mix_is_rejected():
    record = MOD.extract_fixture_record(ROOT, "stale_generation_mix_rejected")
    assert record["decision"]["route"] == "blocked"
    assert record["candidates"] == []
    assert "STALE_OR_MIXED_GENERATION_REJECTED" in record["decision"]["blocker_codes"]
    assert any(
        "STALE_OR_MIXED_GENERATION_REJECTED" in item["reason_codes"]
        for item in record["exclusions"]
    )


def test_structured_lexical_vector_channels_merge():
    record = MOD.extract_fixture_record(ROOT, "structured_lexical_vector_merge")
    assert record["decision"]["route"] == "return_candidates"
    assert record["channel_results"]["structured_metadata_filter"]["status"] == "ok"
    assert record["channel_results"]["lexical_search"]["status"] == "ok"
    assert record["channel_results"]["embedding_similarity"]["status"] == "ok"
    assert record["channel_results"]["canonical_content_hash_deduplication"]["status"] == "ok"
    top = record["candidates"][0]
    assert top["asset_id"] == "fixture:hand_body_contact"
    assert set(top["channel_scores"]) == {
        "structured_metadata_filter",
        "lexical_search",
        "embedding_similarity",
    }


def test_missing_embedding_channel_fail_closed():
    record = MOD.extract_fixture_record(ROOT, "missing_embedding_channel_fail_closed")
    assert record["decision"]["route"] == "blocked"
    assert record["candidates"] == []
    assert "EMBEDDING_INDEX_ARTIFACT_MISSING" in record["decision"]["blocker_codes"]
    assert record["channel_results"]["embedding_similarity"]["status"] == "blocked"


def test_schema_rejects_library_authority_true():
    record = MOD.extract_fixture_record(ROOT, "deterministic_repeat_query")
    mutated = deepcopy(record)
    mutated["library_authority"] = True
    mutated["receipt_sha256"] = "a" * 64
    with pytest.raises(MOD.HybridRetrievalError, match="schema_validation_failed"):
        MOD.validate_query_receipt(ROOT, mutated)


def test_duplicate_canonical_pcm_in_result_rejected():
    record = MOD.extract_fixture_record(ROOT, "deterministic_repeat_query")
    mutated = deepcopy(record)
    if len(mutated["candidates"]) < 2:
        pytest.skip("need at least two candidates to mutate duplicate pcm")
    mutated["candidates"][1]["canonical_pcm_sha256"] = mutated["candidates"][0][
        "canonical_pcm_sha256"
    ]
    mutated = MOD.seal_receipt({k: v for k, v in mutated.items() if k != "receipt_sha256"})
    with pytest.raises(MOD.HybridRetrievalError, match="duplicate_canonical_pcm_in_result"):
        MOD.validate_query_receipt(ROOT, mutated)
