from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_campaign_tool_gateway.py"
SPEC = importlib.util.spec_from_file_location("gateway", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_allows_bounded_action() -> None:
    assert MODULE.evaluate({"tool_id": "HASH_FILE", "paths": ["inputs/a.json"]})["decision"] == "ALLOW"


def test_denies_forbidden_tool_authority_and_path_escape() -> None:
    assert MODULE.evaluate({"tool_id": "PUSH_GIT", "paths": []})["decision"] == "DENY"
    assert MODULE.evaluate({"tool_id": "HASH_FILE", "paths": ["../.env"]})["decision"] == "DENY"
    assert MODULE.evaluate({"tool_id": "READ_CAMPAIGN_INPUT", "paths": ["secrets/credential.json"]})["decision"] == "DENY"


def test_denies_arbitrary_validator_and_destructive_action() -> None:
    assert MODULE.evaluate({"tool_id": "RUN_ALLOWLISTED_VALIDATOR", "paths": ["x"], "validator": "shell"})["decision"] == "DENY"
    assert MODULE.evaluate({"tool_id": "HASH_FILE", "paths": ["x"], "destructive": True})["decision"] == "DENY"
