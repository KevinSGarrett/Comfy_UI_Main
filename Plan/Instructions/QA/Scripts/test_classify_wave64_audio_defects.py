from __future__ import annotations

import importlib.util
import json
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


def test_rebuild_retained_aggregates_recovers_resume_undercount(tmp_path):
    records_path = tmp_path / "records.jsonl"
    rows = [
        {
            "relative_path": f"a/{idx}.wav",
            "extension": ".wav",
            "feature_status": "pass",
            "defect_status": "pass" if idx % 2 == 0 else "blocked",
            "blocker_code": None if idx % 2 == 0 else "DEFECT_CLASSIFICATION_AMBIGUOUS",
            "production_eligibility": "eligible" if idx % 2 == 0 else "unknown",
            "pcm_sha_verified": True,
            "source_immutable": True,
            "visibility_preserved": True,
            "severe_defect_present": False,
            "analysis_truncated": False,
        }
        for idx in range(5)
    ]
    records_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    counts, blockers, _ext, _elig, paths = MOD._rebuild_retained_defect_aggregates_from_records(
        records_path
    )
    assert counts["records_processed"] == 5
    assert counts["defect_pass"] == 3
    assert counts["defect_blocked"] == 2
    assert blockers["DEFECT_CLASSIFICATION_AMBIGUOUS"] == 2
    assert len(paths) == 5


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


def _write_row075_retained_strata_fixture(path: Path) -> None:
    rows = [
        {
            "relative_path": "lib/body_pass.wav",
            "asset_id": "index:lib/body_pass.wav",
            "role": "body",
            "event_type": "body_foley",
            "extension": ".wav",
            "defect_status": "pass",
            "technical_defect_pass": True,
            "production_eligibility": "eligible",
            "severe_defect_codes": [],
            "sample_rate_hz": 48000,
            "channels": 1,
            "frame_count": 1000,
            "source_sha256": "a" * 64,
            "canonical_pcm_sha256": "b" * 64,
            "blocker_code": None,
        },
        {
            "relative_path": "lib/body_blocked.wav",
            "asset_id": "index:lib/body_blocked.wav",
            "role": "body",
            "event_type": "body_foley",
            "extension": ".wav",
            "defect_status": "blocked",
            "technical_defect_pass": False,
            "production_eligibility": "unknown",
            "severe_defect_codes": [],
            "sample_rate_hz": 48000,
            "channels": 1,
            "frame_count": 1000,
            "source_sha256": "c" * 64,
            "canonical_pcm_sha256": "d" * 64,
            "blocker_code": "DEFECT_EXTRACTION_FAILED",
        },
        {
            "relative_path": "lib/action_pass.wav",
            "asset_id": "index:lib/action_pass.wav",
            "role": "effects",
            "event_type": "action_sfx",
            "extension": ".wav",
            "defect_status": "pass",
            "technical_defect_pass": True,
            "production_eligibility": "ineligible",
            "severe_defect_codes": ["clicks"],
            "sample_rate_hz": 48000,
            "channels": 1,
            "frame_count": 2000,
            "source_sha256": "e" * 64,
            "canonical_pcm_sha256": "f" * 64,
            "blocker_code": None,
        },
        {
            "relative_path": "lib/impact_pass.wav",
            "asset_id": "index:lib/impact_pass.wav",
            "role": "effects",
            "event_type": "impact",
            "extension": ".wav",
            "defect_status": "pass",
            "technical_defect_pass": True,
            "production_eligibility": "eligible",
            "severe_defect_codes": [],
            "sample_rate_hz": 48000,
            "channels": 2,
            "frame_count": 3000,
            "source_sha256": "1" * 64,
            "canonical_pcm_sha256": "2" * 64,
            "blocker_code": None,
        },
        {
            "relative_path": "lib/clothing_pass.wav",
            "asset_id": "index:lib/clothing_pass.wav",
            "role": "clothing",
            "event_type": "clothing_foley",
            "extension": ".wav",
            "defect_status": "pass",
            "technical_defect_pass": True,
            "production_eligibility": "limited",
            "severe_defect_codes": [],
            "sample_rate_hz": 44100,
            "channels": 1,
            "frame_count": 1500,
            "source_sha256": "3" * 64,
            "canonical_pcm_sha256": "4" * 64,
            "blocker_code": None,
        },
        {
            "relative_path": "lib/furniture_pass.wav",
            "asset_id": "index:lib/furniture_pass.wav",
            "role": "furniture",
            "event_type": "furniture_foley",
            "extension": ".wav",
            "defect_status": "pass",
            "technical_defect_pass": True,
            "production_eligibility": "eligible",
            "severe_defect_codes": [],
            "sample_rate_hz": 48000,
            "channels": 1,
            "frame_count": 1800,
            "source_sha256": "5" * 64,
            "canonical_pcm_sha256": "6" * 64,
            "blocker_code": None,
        },
        {
            "relative_path": "lib/eval_pass.wav",
            "asset_id": "index:lib/eval_pass.wav",
            "role": "evaluation",
            "event_type": "evaluation_reference",
            "extension": ".wav",
            "defect_status": "pass",
            "technical_defect_pass": True,
            "production_eligibility": "ineligible",
            "severe_defect_codes": ["severe_pre_reverb"],
            "sample_rate_hz": 16000,
            "channels": 1,
            "frame_count": 8000,
            "source_sha256": "7" * 64,
            "canonical_pcm_sha256": "8" * 64,
            "blocker_code": None,
        },
        {
            "relative_path": "lib/unclassified_blocked.mp3",
            "asset_id": "index:lib/unclassified_blocked.mp3",
            "role": "effects",
            "event_type": "unclassified",
            "extension": ".mp3",
            "defect_status": "blocked",
            "technical_defect_pass": False,
            "production_eligibility": "unknown",
            "severe_defect_codes": [],
            "sample_rate_hz": 44100,
            "channels": 2,
            "frame_count": 4000,
            "source_sha256": "9" * 64,
            "canonical_pcm_sha256": "0" * 64,
            "blocker_code": "DEFECT_EXTRACTION_FAILED",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_library_strata_labels_synthetic_truth_and_holds_library_pending():
    retained_path = (
        ROOT
        / "runtime_artifacts"
        / "_pytest_row075_library_strata"
        / "select_records.jsonl"
    )
    _write_row075_retained_strata_fixture(retained_path)
    try:
        strata = MOD.select_library_strata_candidates_from_retained(
            ROOT,
            retained_records_path=retained_path,
        )
        assert strata["authority"] == "candidate_shortlist_pending_truth_defects"
        assert strata["selection_policy"] == MOD.SELECTION_POLICY
        assert strata["counts"]["candidates_selected"] == 13
        assert strata["counts"]["strata_filled"] == 13
        assert strata["counts"]["truth_labeled"] == 5
        assert strata["counts"]["truth_pending"] == 6
        assert strata["counts"]["truth_blocked"] == 2
        assert strata["counts"]["truth_unlabeled"] == 8
        assert strata["truth_defect_status"] == "partial"
        assert strata["decision"]["status"] == "blocked"
        assert strata["decision"]["library_authority"] is False
        assert strata["decision"]["row_complete"] is False
        assert strata["decision"]["product_completion"] is False
        assert strata["decision"]["threshold_authority_unfrozen"] is False
        assert strata["decision"]["benchmark_strata_calibrated"] is False
        assert MOD.BLOCKER_THRESHOLD_FROZEN in strata["blocker_codes"]
        assert MOD.BLOCKER_STRATA_ABSENT in strata["blocker_codes"]
        labeled = [item for item in strata["candidates"] if item["truth_label_status"] == "labeled"]
        library = [item for item in strata["candidates"] if item["role"] != "fixture"]
        assert {item["event_type"] for item in labeled} == {
            "clipping",
            "clicks",
            "dropout",
            "truncation",
            "hum",
        }
        assert all(isinstance(item["truth_severe_defect_codes"], list) for item in labeled)
        assert all(item["truth_label_status"] in {"pending", "blocked"} for item in library)
        assert all(item["truth_severe_defect_codes"] is None for item in library)
        refs = strata["row109_synthetic_partition_references"]
        assert refs["partition_ids"] == [
            "train",
            "calibration",
            "held_out_test",
            "adversarial",
        ]
        assert refs["pcm_decode_authorized"] is False
        assert refs["library_authority"] is False
        MOD.validate_strata_manifest(ROOT, strata)
    finally:
        if retained_path.is_file():
            retained_path.unlink()
        parent = retained_path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()


def test_library_strata_hold_packet_keeps_blockers_without_complete():
    retained_path = (
        ROOT
        / "runtime_artifacts"
        / "_pytest_row075_library_strata"
        / "coverage_complete_records.jsonl"
    )
    _write_row075_retained_strata_fixture(retained_path)
    try:
        strata = MOD.select_library_strata_candidates_from_retained(
            ROOT,
            retained_records_path=retained_path,
        )
    finally:
        if retained_path.is_file():
            retained_path.unlink()
        parent = retained_path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    retained = {
        "authority": "accepted_index_retained_defect_reconcile",
        "coverage_complete": True,
        "counts": {
            "records_processed": 39771,
            "records_total": 39771,
            "defect_pass": 8128,
            "defect_blocked": 31643,
        },
        "receipt_path": (
            "runtime_artifacts/audio_defects/row075_index_retained_20260719/"
            "retained_index_defect_receipt.json"
        ),
        "records_path": (
            "runtime_artifacts/audio_defects/row075_index_retained_20260719/records.jsonl"
        ),
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "status": "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN",
    }
    payload = MOD.build_library_blocker_packet(
        ROOT,
        retained_runtime=retained,
        strata_manifest=strata,
    )
    assert payload["status"] == (
        "HOLD_LIBRARY_THRESHOLDS_AND_BENCHMARK_STRATA_ABSENT_RECONCILE_COMPLETE"
    )
    assert payload["row_complete"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["product_completion"] is False
    assert payload["runtime_completion_claimed"] is True
    assert "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY" in payload["blocker_codes"]
    assert "CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT" in payload["blocker_codes"]
    assert payload["library_benchmark_strata"]["candidates_selected"] == 13
    assert payload["library_benchmark_strata"]["truth_defect_status"] == "partial"
    assert payload["library_benchmark_strata"]["benchmark_strata_calibrated"] is False
