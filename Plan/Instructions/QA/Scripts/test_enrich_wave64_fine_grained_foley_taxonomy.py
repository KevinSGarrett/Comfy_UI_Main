from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/enrich_wave64_fine_grained_foley_taxonomy.py"
SPEC = importlib.util.spec_from_file_location("enrich_wave64_fine_grained_foley_taxonomy", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row074_076_078_admission_fail_closed_on_current_hold_deltas():
    row074 = MOD.evaluate_row074_admission(ROOT)
    row076 = MOD.evaluate_row076_admission(ROOT)
    row078 = MOD.evaluate_row078_admission(ROOT)
    assert row074["dependency_satisfied"] is False
    assert row076["dependency_satisfied"] is False
    assert row078["dependency_satisfied"] is False
    assert "ROW074_DEPENDENCY_NOT_ACCEPTED" in row074["blocker_codes"]
    assert "ROW076_DEPENDENCY_NOT_ACCEPTED" in row076["blocker_codes"]
    assert "ROW078_DEPENDENCY_NOT_ACCEPTED" in row078["blocker_codes"]
    assert row074["row_complete"] is False
    assert row076["row_complete"] is False
    assert row078["row_complete"] is False


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row079_acceptance"] == "held"
    assert "ROW074_ROW076_ROW078_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_ENRICHMENT_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["enricher_revision"] == MOD.ENRICHER_REVISION
    assert payload["taxonomy_revision"] == MOD.TAXONOMY_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 5
    assert set(payload["required_dimensions"]) == set(MOD.REQUIRED_DIMENSIONS)


def test_fixture_records_validate_and_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "heel_on_hardwood")
    second = MOD.extract_fixture_record(ROOT, "heel_on_hardwood")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert first["decision"]["source_bytes_unchanged"] is True
    assert first["compatibility"]["exact_match_compatible"] is True
    assert first["compatibility"]["all_required_dimensions_present"] is True
    assert first["decision"]["exact_match_use_allowed"] is False
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    assert first["taxonomy"]["footwear"] == "heel"
    assert first["taxonomy"]["surface_material"] == "hardwood"
    assert first["taxonomy"]["contact_pair"] == "heel_to_surface"


def test_hand_to_body_fixture_covers_contact_dimensions():
    record = MOD.extract_fixture_record(ROOT, "hand_to_body_contact")
    assert record["taxonomy"]["event_family"] == "body_contact"
    assert record["taxonomy"]["contact_pair"] == "hand_to_body"
    assert record["taxonomy"]["body_region"] == "hand"
    assert record["taxonomy"]["gait_phase"] == "n_a"
    assert record["compatibility"]["exact_match_compatible"] is True


def test_unknown_force_blocks_exact_match_use():
    record = MOD.extract_fixture_record(ROOT, "unknown_force_blocks_exact_match")
    assert "force" in record["compatibility"]["unknown_dimensions"]
    assert record["compatibility"]["exact_match_compatible"] is False
    assert "UNKNOWN_DIMENSION_BLOCKS_EXACT_MATCH" in record["decision"]["blocker_codes"]
    assert "EXACT_MATCH_USE_BLOCKED" in record["decision"]["blocker_codes"]
    assert record["decision"]["promotion_eligible"] is False
    blockers = MOD.assert_promotion_fail_closed(ROOT, record)
    assert "UNKNOWN_DIMENSION_BLOCKS_EXACT_MATCH" in blockers


def test_unknown_room_blocks_exact_match_use():
    record = MOD.extract_fixture_record(ROOT, "unknown_room_blocks_exact_match")
    assert "room" in record["compatibility"]["unknown_dimensions"]
    assert record["compatibility"]["exact_match_compatible"] is False
    assert record["decision"]["exact_match_use_allowed"] is False


def test_footwear_contact_semantic_mismatch_fail_closed():
    record = MOD.extract_fixture_record(ROOT, "footwear_contact_mismatch")
    assert "SEMANTIC_FOOTWEAR_CONTACT_PAIR_MISMATCH" in record["compatibility"]["semantic_blocker_codes"]
    assert "SEMANTIC_FOOTWEAR_BODY_REGION_MISMATCH" in record["compatibility"]["semantic_blocker_codes"]
    assert record["compatibility"]["exact_match_compatible"] is False
    assert record["decision"]["promotion_eligible"] is False


def test_schema_rejects_missing_dimension():
    record = MOD.extract_fixture_record(ROOT, "heel_on_hardwood")
    del record["taxonomy"]["force"]
    with pytest.raises(MOD.FoleyTaxonomyError, match="schema_validation_failed"):
        MOD.validate_enrichment_record(ROOT, record)


def test_invalid_taxonomy_value_blocks_compatibility():
    taxonomy = dict(MOD.FIXTURE_TAXONOMIES["heel_on_hardwood"])
    taxonomy["force"] = "not_a_force_band"
    record = MOD.build_enrichment_record(
        ROOT,
        asset_id="fixture:invalid_force",
        source_sha256="a" * 64,
        segment_id="fixture_segment:invalid_force",
        canonical_pcm_sha256="b" * 64,
        taxonomy=taxonomy,
        evidence_source="synthetic_fixture:invalid_force",
        library_authority=False,
    )
    assert "force" in record["compatibility"]["invalid_dimensions"]
    assert record["compatibility"]["exact_match_compatible"] is False
    assert "INVALID_TAXONOMY_VALUE" in record["decision"]["blocker_codes"]


def test_whitespace_alias_collision_rejected():
    taxonomy = dict(MOD.FIXTURE_TAXONOMIES["heel_on_hardwood"])
    taxonomy["event_family"] = "footstep "
    with pytest.raises(MOD.FoleyTaxonomyError, match="whitespace_or_alias_collision"):
        MOD.build_enrichment_record(
            ROOT,
            asset_id="fixture:alias",
            source_sha256="c" * 64,
            segment_id="fixture_segment:alias",
            canonical_pcm_sha256="d" * 64,
            taxonomy=taxonomy,
            evidence_source="synthetic_fixture:alias",
        )
