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


def test_row070_and_row071_admission_unlocked_on_accepted_deltas():
    row070 = MOD.evaluate_row070_admission(ROOT)
    row071 = MOD.evaluate_row071_admission(ROOT)
    assert row070["dependency_satisfied"] is True
    assert row071["dependency_satisfied"] is True
    assert row070["blocker_codes"] == []
    assert row071["blocker_codes"] == []
    assert row070["row_complete"] is True
    assert row071["row_complete"] is True


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert payload["decision"]["row075_acceptance"] == "held"
    assert "ROW070_AND_ROW071_DEPENDENCIES_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert (
        "DEDICATED_FULL_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
        or "FULL_LIBRARY_RECONCILE_DEFERRED_OR_IN_PROGRESS" in payload["blocker_codes"]
        or "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT" in payload["blocker_codes"]
    )
    assert payload["detector_revision"] == MOD.DETECTOR_REVISION
    assert payload["fixture_calibration"]["fixture_count"] == 11
    assert set(payload["required_defect_codes"]) == set(MOD.REQUIRED_DEFECT_CODES)
    assert payload["status"].endswith("DEPS_UNLOCKED") or "DEPS_UNLOCKED" in payload["status"]


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


def test_index_retained_probe_limit_emits_runtime_pass_bounded_without_complete():
    runtime_dir = (
        ROOT
        / "runtime_artifacts"
        / "audio_defects"
        / "row075_index_retained_probe_pytest"
    )
    if runtime_dir.exists():
        for child in runtime_dir.iterdir():
            if child.is_file():
                child.unlink()
    retained = MOD.run_retained_index_defect_runtime(
        ROOT,
        runtime_dir=runtime_dir,
        limit=3,
        resume=False,
    )
    assert retained["coverage_complete"] is False
    assert retained["limit"] == 3
    assert retained["counts"]["records_processed"] == 3
    assert retained["row_complete"] is False
    assert retained["library_authority"] is False
    assert retained["product_completion_claimed"] is False
    assert retained["proof_tier"] == "RUNTIME_PASS_BOUNDED"
    packet = MOD.build_library_blocker_packet(ROOT, retained_runtime=retained)
    assert packet["decision"]["product_completion"] is False
    assert packet["decision"]["row075_acceptance"] == "held"
    assert "DEPS_UNLOCKED" in packet["status"]
    assert packet["accepted_index_retained_defect_runtime"]["present"] is True
