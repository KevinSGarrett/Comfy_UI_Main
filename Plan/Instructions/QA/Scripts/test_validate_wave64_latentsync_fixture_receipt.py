from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_FIXTURE_STORAGE_20260722T093100Z"


def load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_mirrored_receipt_hash_and_runtime_boundaries() -> None:
    path = EVIDENCE / "remote_fixture.receipt.json"
    receipt = load(path.name)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "7995ce1df54280088c41c2c04144f4ee2afa2c8da316e214342e00df61e8712a"
    )
    assert receipt["status"] == "FIXTURE_BYTES_VERIFIED_NOT_LOADED_OR_INFERRED"
    assert all(value is False for value in receipt["runtime_claims"].values())


def test_fixture_files_and_acceptance_bind_exactly() -> None:
    receipt = load("remote_fixture.receipt.json")
    acceptance = load("integration_acceptance.json")
    by_role = {item["role"]: item for item in receipt["files"]}
    assert by_role["video"]["sha256"] == acceptance["video"]["sha256"]
    assert by_role["video"]["bytes"] == acceptance["video"]["bytes"]
    assert by_role["audio"]["sha256"] == acceptance["audio"]["sha256"]
    assert by_role["audio"]["bytes"] == acceptance["audio"]["bytes"]


def test_known_defects_and_foreign_hold_remain_explicit() -> None:
    acceptance = load("integration_acceptance.json")
    assert acceptance["video"]["known_defects_retained"]
    assert acceptance["coordinator_hold"]["mode"] == "RECOVERY_REQUIRED"
    assert not acceptance["coordinator_hold"]["admission_enabled"]
    assert not acceptance["coordinator_hold"]["foreign_lease_cleared_or_overridden"]


def test_fixture_acceptance_grants_no_runtime_or_product_authority() -> None:
    authority = load("integration_acceptance.json")["authority"]
    assert authority["fixture_storage_and_rights_scope_accepted"]
    assert all(value is False for name, value in authority.items() if name != "fixture_storage_and_rights_scope_accepted")
