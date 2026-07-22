from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_generated_asset_promotion.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wave64_generated_asset_promotion", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_live_dependencies_are_all_held() -> None:
    admissions = MOD.evaluate_dependency_admissions(ROOT)
    assert set(admissions) == {"TRK-W64-080", "TRK-W64-102", "TRK-W64-103"}
    assert all(item["row_complete"] is False for item in admissions.values())
    assert all(item["dependency_satisfied"] is False for item in admissions.values())
    assert all(item["blocker_codes"] for item in admissions.values())


def test_library_packet_fails_closed_without_false_completion() -> None:
    packet = MOD.build_library_blocker_packet(ROOT)
    assert packet["row_complete"] is False
    assert packet["library_authority"] is False
    assert packet["decision"]["row104_acceptance"] == "held"
    assert "ROW104_DEPENDENCIES_NOT_ACCEPTED" in packet["blocker_codes"]
    assert packet["fixture_calibration"]["fixture_count"] == 5


def test_live_valid_candidate_holds_instead_of_rejecting_while_dependencies_are_held() -> None:
    record = MOD.build_record(
        ROOT,
        packet=MOD.base_packet("live_dependency_hold"),
        is_synthetic=False,
    )
    assert record["decision"]["route"] == "hold"
    assert record["decision"]["status"] == "blocked"
    assert record["decision"]["blocker_codes"] == ["ROW104_DEPENDENCIES_NOT_ACCEPTED"]
    assert record["library"]["selector_visible"] is False


def test_promotable_fixture_is_deterministic_but_never_selector_visible() -> None:
    first = MOD.fixture_record(ROOT, "synthetic_promotable_fixture")
    second = MOD.fixture_record(ROOT, "synthetic_promotable_fixture")
    assert first == second
    assert first["decision"]["route"] == "fixture_promotable"
    assert first["decision"]["row104_acceptance"] == "fixture_only"
    assert first["decision"]["promotion_authority"] is False
    assert first["library"]["selector_visible"] is False
    assert first["origin"]["type"] == "generated"


@pytest.mark.parametrize(
    ("fixture", "blocker"),
    [
        ("missing_rights_rejected", "RIGHTS_NOT_ACCEPTED"),
        ("qa_not_accepted_rejected", "QA_NOT_ACCEPTED"),
        ("exact_duplicate_rejected", "EXACT_DUPLICATE"),
    ],
)
def test_invalid_candidates_are_rejected(fixture: str, blocker: str) -> None:
    record = MOD.fixture_record(ROOT, fixture)
    assert record["decision"]["route"] == "reject"
    assert blocker in record["decision"]["blocker_codes"]
    assert record["library"]["selector_visible"] is False


def test_near_duplicate_requires_and_retains_justified_role() -> None:
    record = MOD.fixture_record(ROOT, "near_duplicate_justified_fixture")
    assert record["decision"]["route"] == "fixture_promotable"
    assert record["dedup"]["near_duplicate"] is True
    assert record["dedup"]["justified_role"]


def test_revocation_removes_visibility_and_retains_evidence() -> None:
    record = MOD.fixture_record(ROOT, "synthetic_promotable_fixture")
    revoked = MOD.revoke_record(ROOT, record, reason="rights withdrawn", receipt_sha256="a" * 64)
    assert revoked["decision"]["route"] == "revoke"
    assert revoked["library"]["selector_visible"] is False
    assert revoked["library"]["evidence_retained"] is True
    assert revoked["revocation"]["status"] == "revoked"


def test_semantic_validator_rejects_selector_visibility_without_authority() -> None:
    record = MOD.fixture_record(ROOT, "synthetic_promotable_fixture")
    mutated = deepcopy(record)
    mutated["library"]["selector_visible"] = True
    mutated.pop("receipt_sha256")
    mutated = MOD.seal_record(mutated)
    with pytest.raises(MOD.GeneratedAssetPromotionError, match="synthetic_fixture"):
        MOD.validate_semantics(mutated)
