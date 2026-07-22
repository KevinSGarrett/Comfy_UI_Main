from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_forced_alignment_audio_event_expansion.py"
PLAN = ROOT / "Plan/10_REGISTRIES/wave64_forced_alignment_audio_event_expansion_plan.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_forced_alignment_audio_event_expansion.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_alignment_event_expansion", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def value() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def test_real_plan_matches_schema_and_exact_local_sources() -> None:
    import jsonschema

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(value())
    assert MODULE.validate(value(), ROOT) == []


def test_missing_natural_speaker_fails_closed() -> None:
    changed = copy.deepcopy(value())
    for source in changed["sources"]:
        if source["speaker_class"] == "public_domain_natural_speaker":
            source["speaker_class"] = "project_generated_qwen_clone"
    assert "a distinct natural-speaker source is required" in MODULE.validate(
        changed, ROOT, verify_bytes=False
    )


def test_unknown_case_source_and_missing_partition_fail_closed() -> None:
    changed = copy.deepcopy(value())
    changed["alignment_cases"][0]["source_id"] = "not_admitted"
    for case in changed["alignment_cases"] + changed["event_cases"]:
        case["partition"] = "calibration"
    errors = MODULE.validate(changed, ROOT, verify_bytes=False)
    assert any("unknown sources" in error for error in errors)
    assert "calibration and held-out partitions are both required" in errors


def test_frozen_case_identity_and_order_fail_closed() -> None:
    changed = copy.deepcopy(value())
    changed["alignment_cases"][0]["case_id"] = "substituted_case"
    changed["execution_order"] = list(reversed(changed["execution_order"]))
    errors = MODULE.validate(changed, ROOT, verify_bytes=False)
    assert "alignment case IDs do not match the frozen set" in errors
    assert "execution order does not match the frozen sequence" in errors


def test_authority_expansion_fails_closed() -> None:
    changed = copy.deepcopy(value())
    changed["authority"]["audio_event_recognition"] = True
    assert "prospective plan exceeds source-admission authority" in MODULE.validate(
        changed, ROOT, verify_bytes=False
    )


def test_hash_drift_fails_closed() -> None:
    changed = copy.deepcopy(value())
    changed["sources"][0]["sha256"] = "0" * 64
    assert any(
        "source qwen_l02_english failed identity" in error
        for error in MODULE.validate(changed, ROOT)
    )
