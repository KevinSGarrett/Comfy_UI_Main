from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_audio_tag_caption_ensemble.py"
SPEC = importlib.util.spec_from_file_location(
    "compile_wave64_audio_tag_caption_ensemble", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row071_075_077_admission_fail_closed_on_current_hold_deltas():
    row071 = MOD.evaluate_row071_admission(ROOT)
    row075 = MOD.evaluate_row075_admission(ROOT)
    row077 = MOD.evaluate_row077_admission(ROOT)
    assert row071["dependency_satisfied"] is False
    assert row075["dependency_satisfied"] is False
    assert row077["dependency_satisfied"] is False
    assert "ROW071_DEPENDENCY_NOT_ACCEPTED" in row071["blocker_codes"]
    assert "ROW075_DEPENDENCY_NOT_ACCEPTED" in row075["blocker_codes"]
    assert "ROW077_DEPENDENCY_NOT_ACCEPTED" in row077["blocker_codes"]
    assert row071["row_complete"] is False
    assert row075["row_complete"] is False
    assert row077["row_complete"] is False


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row078_acceptance"] == "held"
    assert "ROW071_ROW075_ROW077_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_ENSEMBLE_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "TAGGING_AND_CAPTION_MODEL_STACK_UNBOUND" in payload["blocker_codes"]
    assert payload["compiler_revision"] == MOD.COMPILER_REVISION
    assert payload["taxonomy_revision"] == MOD.TAXONOMY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_signal_families"]) == set(MOD.REQUIRED_SIGNAL_FAMILIES)


def test_agreement_fixture_validates_and_is_deterministic():
    first = MOD.extract_fixture_record(ROOT, "agreement_four_families")
    second = MOD.extract_fixture_record(ROOT, "agreement_four_families")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert first["decision"]["source_bytes_unchanged"] is True
    assert first["ensemble_resolution"]["status"] == "resolved"
    assert first["ensemble_resolution"]["conflict_preservation"] is True
    assert len(first["independent_source_observations"]) == 4
    assert first["structured_tags"]["event_family"]["value"] == "footstep"
    assert first["structured_tags"]["material"]["value"] == "hardwood"
    assert first["technical_caption"]["overwrites_source_metadata"] is False
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    MOD.assert_caption_non_overwrite(ROOT, first)


def test_disagreement_material_is_preserved_not_averaged():
    record = MOD.extract_fixture_record(ROOT, "disagreement_material_preserved")
    assert record["ensemble_resolution"]["status"] == "abstain"
    assert record["ensemble_resolution"]["abstention_reason"] == "source_disagreement_preserved"
    assert len(record["source_disagreements"]) == 1
    disagreement = record["source_disagreements"][0]
    assert disagreement["field"] == "material"
    assert disagreement["preserved"] is True
    values = set(disagreement["values_by_signal_family"].values())
    assert values == {"hardwood", "concrete", "tile"}
    assert record["structured_tags"]["material"]["classification"] == "ambiguous"
    assert record["structured_tags"]["material"]["value"] == "abstain"
    assert "SOURCE_DISAGREEMENT_PRESERVED_ABSTAIN" in record["decision"]["blocker_codes"]
    blockers = MOD.assert_promotion_fail_closed(ROOT, record)
    assert "SOURCE_DISAGREEMENT_PRESERVED_ABSTAIN" in blockers


def test_unknown_intensity_fail_closed():
    record = MOD.extract_fixture_record(ROOT, "unknown_intensity_fail_closed")
    assert "intensity_band" in record["unknown_and_out_of_taxonomy"]["unknown_fields"]
    assert record["ensemble_resolution"]["status"] == "abstain"
    assert "UNKNOWN_TAXONOMY_FAIL_CLOSED" in record["decision"]["blocker_codes"]
    assert record["decision"]["promotion_eligible"] is False


def test_out_of_taxonomy_event_fail_closed():
    record = MOD.extract_fixture_record(ROOT, "out_of_taxonomy_event_fail_closed")
    assert "event_family" in record["unknown_and_out_of_taxonomy"]["out_of_taxonomy_fields"]
    assert record["structured_tags"]["event_family"]["classification"] == "out_of_taxonomy"
    assert "OUT_OF_TAXONOMY_FAIL_CLOSED" in record["decision"]["blocker_codes"]
    assert record["decision"]["promotion_eligible"] is False


def test_missing_embedding_family_blocks_resolution():
    record = MOD.extract_fixture_record(ROOT, "missing_embedding_family_blocked")
    assert "semantic_embeddings" in record["unknown_and_out_of_taxonomy"]["missing_signal_families"]
    assert record["ensemble_resolution"]["status"] == "blocked"
    assert "MISSING_REQUIRED_SIGNAL_FAMILIES" in record["decision"]["blocker_codes"]


def test_caption_overwrite_attempt_rejected():
    labels = {
        "event_family": "footstep",
        "material": "hardwood",
        "intensity_band": "medium",
        "attack_characteristic": "transient",
        "room_environment": "dry_close",
    }
    with pytest.raises(
        MOD.AudioTagCaptionEnsembleError,
        match="caption_overwrite_of_source_metadata_forbidden",
    ):
        MOD.build_ensemble_record(
            ROOT,
            asset_id="fixture:overwrite",
            source_sha256="a" * 64,
            source_metadata=MOD._base_metadata(),
            observations=MOD._four_family_observations(labels, prefix="overwrite"),
            allow_caption_overwrite_attempt=True,
        )


def test_schema_rejects_missing_signal_observation_shape():
    record = MOD.extract_fixture_record(ROOT, "agreement_four_families")
    del record["independent_source_observations"][0]["labels"]["material"]
    with pytest.raises(MOD.AudioTagCaptionEnsembleError, match="schema_validation_failed"):
        MOD.validate_ensemble_record(ROOT, record)


def test_source_metadata_snapshot_hash_bound():
    record = MOD.extract_fixture_record(ROOT, "agreement_four_families")
    record["source_metadata_snapshot"]["material"] = "mutated"
    with pytest.raises(
        MOD.AudioTagCaptionEnsembleError,
        match="source_metadata_snapshot_hash_mismatch",
    ):
        MOD.validate_ensemble_record(ROOT, record)
