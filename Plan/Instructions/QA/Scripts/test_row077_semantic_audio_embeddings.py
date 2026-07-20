from __future__ import annotations

import importlib.util
import json
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


def test_row069_070_admission_accepts_current_library_authority_deltas():
    row069 = MOD.evaluate_row069_admission(ROOT)
    row070 = MOD.evaluate_row070_admission(ROOT)
    assert row069["dependency_satisfied"] is True
    assert row070["dependency_satisfied"] is True
    assert row069["blocker_codes"] == []
    assert row070["blocker_codes"] == []
    assert row069["row_complete"] is True
    assert row070["row_complete"] is True


def test_library_mode_emits_model_selected_heldout_bound_hold_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["dependencies_unlocked"] is True
    weights_runtime = bool(payload["heldout_binding"].get("weights_runtime"))
    if weights_runtime:
        assert payload["status"] == (
            "HOLD_LIBRARY_EMBEDDING_INDEX_ABSENT_HELDOUT_WEIGHTS_RUNTIME_BOUND"
        )
        assert payload["proof_tier"] == "RUNTIME_PASS_BOUNDED"
        assert payload["highest_proof_tier_achieved"] == "RUNTIME_PASS_BOUNDED"
        assert payload["heldout_binding"]["model_weights_loaded"] is True
        assert payload["heldout_binding"]["emitter"] == MOD.HELDOUT_EMITTER_WEIGHTS_RUNTIME
        assert payload["decision"]["heldout_weights_runtime"] is True
    else:
        assert payload["status"] == (
            "HOLD_LIBRARY_EMBEDDING_INDEX_ABSENT_MODEL_SELECTED_HELDOUT_BOUND"
        )
        assert payload["proof_tier"] == "CONTRACT_PASS_BOUNDED"
        assert payload["highest_proof_tier_achieved"] == "CONTRACT_PASS_BOUNDED"
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row077_acceptance"] == "held"
    assert payload["decision"]["dependencies_unlocked"] is True
    assert payload["decision"]["model_selected"] is True
    assert payload["decision"]["license_bound"] is True
    assert payload["decision"]["hashes_frozen"] is True
    assert payload["decision"]["heldout_bound"] is True
    assert "ROW069_ROW070_DEPENDENCIES_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "EMBEDDING_MODEL_NOT_SELECTED_OR_INSTALLED" not in payload["blocker_codes"]
    assert "PREPROCESSING_RUNTIME_UNBOUND" not in payload["blocker_codes"]
    assert "HELDOUT_RETRIEVAL_LIBRARY_METRICS_ABSENT" not in payload["blocker_codes"]
    assert "EMBEDDING_MODEL_WEIGHTS_NOT_INSTALLED" not in payload["blocker_codes"]
    assert "EMBEDDING_INDEX_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT" in payload["blocker_codes"]
    assert payload["model_selection"]["selected_asset_id"] == "laion_clap_general"
    assert payload["model_selection"]["weights_installed"] is True
    assert payload["heldout_binding"]["scope"] == "held_out_only"
    assert payload["heldout_binding"]["full_library_scan"] is False
    assert payload["compiler_revision"] == MOD.COMPILER_REVISION
    assert payload["registry_revision"] == MOD.REGISTRY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_embedding_spaces"]) == set(MOD.REQUIRED_EMBEDDING_SPACES)


def test_registry_freezes_hashes_and_license_binds_selected_model():
    registry = MOD.load_registry(ROOT)
    frozen = MOD.assert_frozen_hashes(registry)
    selection = MOD.assert_model_selection_binding(registry)
    assert registry["model_binding"]["selected_for_library"] is True
    assert registry["model_binding"]["weights_installed"] is True
    assert selection["selected_asset_id"] == "laion_clap_general"
    assert selection["weights_installed"] is True
    assert MOD.weights_installed(ROOT, registry) is True
    assert selection["expected_key_file_sha256"] == (
        "314eb00cce6ad68d25237b8446b659ccdb136ed4672c1bca470f142f72455026"
    )
    assert frozen["preprocessing_configuration_sha256"] == (
        "457d0fa46b5a3de30386de273e08b61ce681b6ffd41c91ee17b368d27d4a6969"
    )
    assert frozen["taxonomy_revision_sha256"] == (
        "a1ec36bcb43d851ef592c618540ea2d8cb5352233ba10b13892ff7117b966327"
    )
    assert registry["model_binding"]["license_binding"]["acceptance_asserted"] is True
    assert registry["model_binding"]["license_binding"]["binding_sha256"] == (
        selection["license_binding_sha256"]
    )


def test_heldout_binding_is_disjoint_and_forbids_full_library_scan():
    # persist=False so fixture rebuild cannot overwrite weights-runtime artifacts on disk.
    heldout = MOD.build_heldout_binding_artifacts(
        ROOT, emitter=MOD.HELDOUT_EMITTER_FIXTURE, persist=False
    )
    assert heldout["manifest"]["scope"] == "held_out_only"
    assert heldout["manifest"]["emitter"] == MOD.HELDOUT_EMITTER_FIXTURE
    assert heldout["manifest"]["full_library_scan"] is False
    assert heldout["manifest"]["pcm_decoded"] is False
    assert heldout["manifest"]["model_weights_loaded"] is False
    assert heldout["manifest"]["weights_installed"] is True
    assert heldout["manifest"]["row_complete"] is False
    assert heldout["metrics"]["all_slices_pass"] is True
    assert heldout["metrics"]["full_library_metrics"] is False
    assert len(heldout["metrics"]["slices"]) == 4
    assert heldout["index"]["embedding_index_revision"] == MOD.HELDOUT_INDEX_REVISION
    paths = MOD.heldout_artifact_paths(ROOT)
    assert paths["manifest"].is_file()
    assert paths["index"].is_file()
    assert paths["metrics"].is_file()


def test_heldout_weights_runtime_artifacts_forbid_library_scan_when_present():
    heldout = MOD.load_heldout_binding_if_present(ROOT)
    if heldout is None:
        pytest.skip("held-out artifacts absent")
    manifest = heldout["manifest"]
    assert manifest["scope"] == "held_out_only"
    assert manifest["full_library_scan"] is False
    assert manifest["row_complete"] is False
    if manifest.get("emitter") == MOD.HELDOUT_EMITTER_WEIGHTS_RUNTIME:
        assert manifest["model_weights_loaded"] is True
        assert manifest["pcm_decoded"] is True
        assert manifest["vector_dimension"] == MOD.PRODUCTION_VECTOR_DIM
        assert heldout["metrics"]["all_slices_pass"] is True
        assert heldout["metrics"]["full_library_metrics"] is False
        assert heldout["index"]["embedding_index_revision"] == MOD.HELDOUT_INDEX_REVISION


def test_admission_fail_closed_when_delta_marks_held():
    fixture_dir = ROOT / "runtime_artifacts" / "_row077_admission_fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    held = {
        "row_complete": False,
        "status": "HOLD_EXAMPLE",
        "decision": {"row069_acceptance": "held", "row070_acceptance": "held"},
    }
    row069_path = fixture_dir / "row069_held.json"
    row070_path = fixture_dir / "row070_held.json"
    try:
        row069_path.write_text(json.dumps(held), encoding="utf-8")
        row070_path.write_text(json.dumps(held), encoding="utf-8")
        row069 = MOD.evaluate_row069_admission(ROOT, delta_path=row069_path)
        row070 = MOD.evaluate_row070_admission(ROOT, delta_path=row070_path)
        assert row069["dependency_satisfied"] is False
        assert row070["dependency_satisfied"] is False
        assert "ROW069_DEPENDENCY_NOT_ACCEPTED" in row069["blocker_codes"]
        assert "ROW070_DEPENDENCY_NOT_ACCEPTED" in row070["blocker_codes"]
    finally:
        for path in (row069_path, row070_path):
            if path.is_file():
                path.unlink()
        if fixture_dir.is_dir() and not any(fixture_dir.iterdir()):
            fixture_dir.rmdir()


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
