from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_proposed_delta.py"
SPEC = importlib.util.spec_from_file_location("delta", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
H = "a" * 64


def draft() -> dict:
    return {"schema_version": "wave64.aqa.campaign_proposed_delta.v1", "campaign_id": H, "base_commit_sha256": H, "changes": [{"relative_path": "Plan/Tracker/example.csv", "operation": "MODIFY", "candidate_sha256": H, "evidence_sha256": H}]}


def test_compile_verify_and_authority() -> None:
    result = MODULE.compile_delta(draft())
    MODULE.verify_delta(result)
    assert result["authority"] == {"candidate_only": True, "may_commit": False, "final_acceptance_authority": "CODEX"}


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:\\escape"])
def test_rejects_path_escape(path: str) -> None:
    value = draft()
    value["changes"][0]["relative_path"] = path
    with pytest.raises(MODULE.DeltaError):
        MODULE.compile_delta(value)


def test_rejects_duplicate_and_tamper() -> None:
    value = draft()
    value["changes"].append(copy.deepcopy(value["changes"][0]))
    with pytest.raises(MODULE.DeltaError, match="unique"):
        MODULE.compile_delta(value)
    result = MODULE.compile_delta(draft())
    result["changes"][0]["candidate_sha256"] = "b" * 64
    with pytest.raises(MODULE.DeltaError, match="delta_id"):
        MODULE.verify_delta(result)
