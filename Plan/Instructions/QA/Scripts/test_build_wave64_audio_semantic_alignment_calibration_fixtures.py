from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_audio_semantic_alignment_calibration_fixtures.py"
PLAN = ROOT / "Plan/10_REGISTRIES/wave64_audio_semantic_alignment_calibration_plan.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_audio_semantic_alignment_calibration_plan.schema.json"
SPEC = importlib.util.spec_from_file_location("audio_calibration_builder", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_plan_schema_and_prospective_matrix() -> None:
    import jsonschema

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(plan)
    assert [item["fixture_id"] for item in plan["fixtures"]] == ["clean_speech", "tone_only", "silence", "speech_plus_tone"]
    assert plan["authority"]["operational"] is False


def test_build_is_hash_reproducible_and_authority_closed(tmp_path: Path) -> None:
    first = MODULE.build(PLAN, ROOT, tmp_path / "first")
    second = MODULE.build(PLAN, ROOT, tmp_path / "second")
    assert [item["sha256"] for item in first["fixtures"]] == [item["sha256"] for item in second["fixtures"]]
    assert first["fixtures"][0]["sha256"] == "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
    assert first["authority"] == {"semantic_calibration": False, "forced_alignment": False, "operational": False, "product_promotion": False}
    assert (tmp_path / "first" / "fixture_manifest.json").is_file()


def test_nonempty_output_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "foreign.txt").write_text("owned elsewhere", encoding="utf-8")
    with pytest.raises(MODULE.CalibrationError, match="not empty"):
        MODULE.build(PLAN, ROOT, output)


def test_source_hash_drift_fails_closed(tmp_path: Path) -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan["source"]["sha256"] = "0" * 64
    drift = tmp_path / "drift.json"
    drift.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(MODULE.CalibrationError, match="source identity"):
        MODULE.build(drift, ROOT, tmp_path / "out")
