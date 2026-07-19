from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_semantic_audio_embeddings.py"
SPEC = importlib.util.spec_from_file_location(
    "compile_wave64_semantic_audio_embeddings", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row069_070_admission_fail_closed_on_current_hold_deltas():
    row069 = MOD.evaluate_row069_admission(ROOT)
    row070 = MOD.evaluate_row070_admission(ROOT)
    assert row069["dependency_satisfied"] is False
    assert row070["dependency_satisfied"] is False
    assert "ROW069_DEPENDENCY_NOT_ACCEPTED" in row069["blocker_codes"]
    assert "ROW070_DEPENDENCY_NOT_ACCEPTED" in row070["blocker_codes"]
    assert row069["row_complete"] is False
    assert row070["row_complete"] is False


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row077_acceptance"] == "held"
    assert "ROW069_ROW070_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "EMBEDDING_MODEL_NOT_SELECTED_OR_INSTALLED" in payload["blocker_codes"]
    assert payload["compiler_revision"] == MOD.COMPILER_REVISION
    assert payload["registry_revision"] == MOD.REGISTRY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_embedding_spaces"]) == set(MOD.REQUIRED_EMBEDDING_SPACES)


def test_audio_text_compatible_space_is_deterministic():
    first = MOD.extract_fixture_record(ROOT, "audio_text_compatible_space")
    second = MOD.extract_fixture_record(ROOT, "audio_text_compatible_space")
    assert first == second
    assert first["vector"]["compatible_audio_text_space"] is True
    assert first["decision"]["status"] == "fixture_ok"
    assert first["library_authority"] is False
    text = MOD.build_embedding_record(
        ROOT,
        asset_id="fixture:audio_text_compatible_space:text",
        source_input_sha256=MOD._stable_hash("text:material:hardwood"),
        modality="text_taxonomy",
        embedding_space="material",
        partition="calibration",
        vector_seed="space:footstep:hardwood",
        taxonomy_label="hardwood",
        retrieval_evidence=first["retrieval_evidence"],
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
        status="fixture_ok",
    )
    similarity = MOD.cosine_similarity(first["vector"]["values"], text["vector"]["values"])
    assert similarity >= 0.999


def test_determinism_repeat_is_exact():
    record = MOD.extract_fixture_record(ROOT, "determinism_repeat")
    assert record["determinism_proof"]["identical_bytes"] is True
    assert record["determinism_proof"]["max_abs_delta"] == 0.0
    assert record["determinism_proof"]["repeat_count"] == 2


def test_heldout_retrieval_ranks_true_neighbor_first():
    record = MOD.extract_fixture_record(ROOT, "heldout_retrieval_pass")
    assert record["partition"] == "held_out"
    assert record["retrieval_evidence"]["metric_pass"] is True
    sims = record["retrieval_evidence"]["cosine_similarities"]
    assert len(sims) >= 2
    assert sims[0] > sims[1]
    assert record["retrieval_evidence"]["neighbor_asset_ids"][0].endswith("footstep")


def test_unknown_ambiguous_fail_closed_abstains():
    record = MOD.extract_fixture_record(ROOT, "unknown_ambiguous_fail_closed")
    assert record["partition"] == "unknown"
    assert record["retrieval_evidence"]["abstained"] is True
    assert record["decision"]["status"] == "abstain"
    assert "UNKNOWN_OR_AMBIGUOUS_FAIL_CLOSED" in record["decision"]["blocker_codes"]
    blockers = MOD.assert_promotion_fail_closed(ROOT, record)
    assert "UNKNOWN_OR_AMBIGUOUS_FAIL_CLOSED" in blockers


def test_similarity_cannot_certify_or_promote():
    record = MOD.extract_fixture_record(ROOT, "similarity_non_certifying")
    assert record["non_certifying_policy"]["similarity_alone_cannot_certify"] is True
    assert record["decision"]["promotion_eligible"] is False
    assert record["decision"]["status"] == "blocked"
    assert "SIMILARITY_ALONE_CANNOT_CERTIFY" in record["decision"]["blocker_codes"]


def test_partitions_remain_disjoint_across_fixtures():
    records = [MOD.extract_fixture_record(ROOT, name) for name in MOD.FIXTURE_NAMES]
    MOD.assert_partitions_disjoint(records)


def test_schema_rejects_mutated_embedding_hash():
    record = MOD.extract_fixture_record(ROOT, "determinism_repeat")
    mutated = deepcopy(record)
    mutated["embedding_sha256"] = "a" * 64
    with pytest.raises(MOD.SemanticAudioEmbeddingError, match="embedding_sha256_mismatch"):
        MOD.validate_embedding_record(ROOT, mutated)


def test_schema_rejects_missing_non_certifying_flag_shape():
    record = MOD.extract_fixture_record(ROOT, "similarity_non_certifying")
    mutated = deepcopy(record)
    del mutated["non_certifying_policy"]["cannot_certify_rights"]
    with pytest.raises(MOD.SemanticAudioEmbeddingError, match="schema_validation_failed"):
        MOD.validate_embedding_record(ROOT, mutated)
