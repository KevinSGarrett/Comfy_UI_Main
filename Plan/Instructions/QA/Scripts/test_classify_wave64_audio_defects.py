from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/classify_wave64_audio_defects.py"
SPEC = importlib.util.spec_from_file_location("classify_wave64_audio_defects", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def _severity(record: dict, code: str) -> str:
    for label in record["defects"]:
        if label["defect_code"] == code:
            return label["severity"]
    raise AssertionError(f"missing defect code {code}")


def test_row070_and_row071_admission_fail_closed_on_current_hold_deltas():
    row070 = MOD.evaluate_row070_admission(ROOT)
    row071 = MOD.evaluate_row071_admission(ROOT)
    assert row070["dependency_satisfied"] is False
    assert row071["dependency_satisfied"] is False
    assert "ROW070_DEPENDENCY_NOT_ACCEPTED" in row070["blocker_codes"]
    assert "ROW071_DEPENDENCY_NOT_ACCEPTED" in row071["blocker_codes"]
    assert row070["row_complete"] is False
    assert row071["row_complete"] is False


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row075_acceptance"] == "held"
    assert "ROW070_AND_ROW071_DEPENDENCIES_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert payload["detector_revision"] == MOD.DETECTOR_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 11
    assert set(payload["required_defect_codes"]) == set(MOD.REQUIRED_DEFECT_CODES)


def test_fixture_records_validate_and_are_deterministic():
    first = MOD.extract_fixture_record(ROOT, "clipping")
    second = MOD.extract_fixture_record(ROOT, "clipping")
    assert first == second
    assert first["decision"]["library_authority"] is False
    assert first["decision"]["status"] == "blocked"
    assert first["decision"]["visibility_preserved"] is True
    assert first["decision"]["source_bytes_unchanged"] is True
    assert first["source_before_sha256"] == first["source_after_sha256"]
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    assert first["taxonomy_coverage"]["all_required_codes_evaluated"] is True
    assert _severity(first, "clipping") == "severe"
    assert first["decision"]["production_eligibility"] == "ineligible"
    assert first["decision"]["severe_defect_present"] is True


def test_clean_fixture_has_no_severe_defects():
    record = MOD.extract_fixture_record(ROOT, "clean_tone")
    assert record["decision"]["severe_defect_present"] is False
    assert all(label["severity"] in {"none", "mild"} for label in record["defects"])
    assert record["decision"]["visibility_preserved"] is True


def test_dropout_and_truncation_fixtures_demote_eligibility():
    dropout = MOD.extract_fixture_record(ROOT, "dropout")
    truncation = MOD.extract_fixture_record(ROOT, "truncation")
    assert _severity(dropout, "dropouts") == "severe"
    assert _severity(truncation, "truncation") == "severe"
    assert dropout["decision"]["production_eligibility"] == "ineligible"
    assert truncation["decision"]["production_eligibility"] == "ineligible"


def test_hum_and_clicks_fixtures_emit_positive_labels():
    hum = MOD.extract_fixture_record(ROOT, "hum")
    clicks = MOD.extract_fixture_record(ROOT, "clicks")
    assert _severity(hum, "hum") in {"moderate", "severe"}
    assert _severity(clicks, "clicks") in {"moderate", "severe"}


def test_codec_and_speech_fixtures_cover_declared_classes():
    codec = MOD.extract_fixture_record(ROOT, "codec_damage")
    speech = MOD.extract_fixture_record(ROOT, "speech_contamination")
    assert _severity(codec, "codec_damage") == "severe"
    assert _severity(speech, "unintelligible_speech_contamination") == "severe"


def test_schema_rejects_missing_defect_evidence():
    record = MOD.extract_fixture_record(ROOT, "hiss_noise")
    del record["defects"][0]["evidence"]
    with pytest.raises(MOD.AudioDefectError, match="schema_validation_failed"):
        MOD.validate_classification_record(ROOT, record)
