#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_rights_provenance_authority.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_wave64_audio_rights_provenance_authority", SCRIPT
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_row067_admission_is_satisfied_on_accepted_evidence():
    admission = MOD.evaluate_row067_admission(ROOT)
    assert admission["dependency_satisfied"] is True
    assert admission["blocker_codes"] == []


def test_vocabulary_registry_revision_is_frozen():
    registry = MOD.load_vocabulary_registry(ROOT)
    assert registry["revision"] == MOD.VOCABULARY_REVISION
    for dimension in MOD.FROZEN_DIMENSIONS:
        assert dimension in registry["frozen_dimensions"]


def test_source_and_generated_rights_contracts_require_decision_hash():
    contracts = MOD.inspect_source_generated_rights_contracts(ROOT)
    assert contracts["contracts_tightened"] is True
    assert "rights_decision_sha256" in contracts["source_required"]
    assert "rights_decision_sha256" in contracts["generated_required"]
    assert contracts["gap_codes"] == []


def test_cc0_and_project_owned_fixtures_pass_deterministically():
    registry = MOD.load_vocabulary_registry(ROOT)
    fixtures = {item["fixture_name"]: item for item in MOD.build_fixture_records(ROOT, registry)}
    first = fixtures["cc0_source_selection_pass"]["record"]
    second = fixtures["project_owned_transform_pass"]["record"]
    assert first["decision"]["status"] == "pass"
    assert first["decision"]["authority_granted"] is True
    assert second["decision"]["status"] == "pass"
    rerun = MOD.build_fixture_records(ROOT, registry)
    again = {item["fixture_name"]: item for item in rerun}["cc0_source_selection_pass"]["record"]
    assert again == first


def test_unknown_license_and_unbound_attribution_fail_closed():
    registry = MOD.load_vocabulary_registry(ROOT)
    fixtures = {item["fixture_name"]: item for item in MOD.build_fixture_records(ROOT, registry)}
    unknown = fixtures["unknown_license_blocks"]["record"]
    unbound = fixtures["cc_by_missing_attribution_blocks"]["record"]
    assert unknown["decision"]["status"] == "blocked"
    assert "LICENSE_UNKNOWN_OR_PROHIBITED" in unknown["decision"]["blocker_codes"]
    assert unbound["decision"]["status"] == "blocked"
    assert "ATTRIBUTION_REQUIRED_BUT_UNBOUND" in unbound["decision"]["blocker_codes"]


def test_incomplete_dimension_rejected_by_schema():
    registry = MOD.load_vocabulary_registry(ROOT)
    probe = MOD.assert_incomplete_rights_fail_closed(ROOT, registry)
    assert probe["incomplete_dimension_rejected"] is True


def test_schema_rejects_authority_granted_without_pass_seal_consistency():
    registry = MOD.load_vocabulary_registry(ROOT)
    record = MOD.build_decision_skeleton(
        decision_id="fixture:bad_seal",
        subject_kind="source_asset",
        subject_id="fixture/source/bad_seal.wav",
        license_class="cc0",
        license_id="CC0-1.0",
        requested_use="library_selection",
        attribution_text="",
    )
    sealed = MOD.finalize_decision(ROOT, record, registry)
    broken = deepcopy(sealed)
    broken["rights_decision_sha256"] = "a" * 63
    with pytest.raises(MOD.RightsAuthorityError, match="schema_validation_failed"):
        MOD.validate_decision_record(ROOT, broken)


def test_lifecycle_schemas_require_rights_decision_sha256():
    lifecycle = MOD.inspect_lifecycle_rights_bindings(ROOT)
    assert lifecycle["lifecycle_binding_complete"] is True
    assert lifecycle["unbound_count"] == 0
    assert lifecycle["bound_count"] == len(MOD.LIFECYCLE_SCHEMAS)
    assert all(detail["rights_decision_sha256_required"] for detail in lifecycle["details"])


def test_authority_packet_accepts_without_claiming_runtime_or_product():
    packet = MOD.build_authority_packet(ROOT)
    assert packet["rights_decision_authority_accepted"] is True
    assert packet["row_complete"] is True
    assert packet["runtime_completion_claimed"] is False
    assert packet["product_completion_claimed"] is False
    assert packet["implementation_completion_claimed"] is False
    assert packet["decision"]["row068_acceptance"] == "accepted"
    assert packet["decision"]["runtime_completion"] is False
    assert packet["decision"]["product_completion"] is False
    assert packet["decision"]["lifecycle_binding_complete"] is True
    assert packet["fixture_calibration"]["fixture_count"] >= 8
    hold_codes = {hold["code"] for hold in packet["remaining_holds"]}
    assert "LIFECYCLE_RIGHTS_BINDING_INCOMPLETE" not in hold_codes
    assert "LIBRARY_RUNTIME_RIGHTS_STAMPING_ABSENT" in hold_codes
    assert packet["lifecycle_bindings"]["lifecycle_binding_complete"] is True
