#!/usr/bin/env python3
"""Fail-closed allowlist gateway for isolated autonomous campaign actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any


ALLOWED = {
    "HASH_FILE",
    "READ_CAMPAIGN_INPUT",
    "VALIDATE_JSON",
    "RUN_ALLOWLISTED_VALIDATOR",
    "WRITE_CANDIDATE_ARTIFACT",
    "RENDER_ACCEPTANCE_SUMMARY",
}
FORBIDDEN = {
    "PUSH_GIT", "PROMOTE_PRODUCT", "WEAKEN_THRESHOLD", "SPEND_MONEY",
    "READ_CREDENTIAL", "DESTRUCTIVE_ACTION", "OVERRIDE_FOREIGN_LEASE", "SELF_PROMOTE",
}
VALIDATORS = {"pytest", "ruff check", "python-jsonschema"}


def _safe_relative(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return bool(value) and not path.is_absolute() and ":" not in path.parts[0] and ".." not in path.parts


def evaluate(request: dict[str, Any]) -> dict[str, Any]:
    tool = request.get("tool_id")
    paths = request.get("paths", [])
    reasons: list[str] = []
    if tool in FORBIDDEN or tool not in ALLOWED:
        reasons.append("TOOL_NOT_ALLOWLISTED")
    if not isinstance(paths, list) or any(not isinstance(path, str) or not _safe_relative(path) for path in paths):
        reasons.append("PATH_ESCAPE_OR_INVALID")
    if any(path.lower().endswith(".env") or "credential" in path.lower() or "secret" in path.lower() for path in paths):
        reasons.append("CREDENTIAL_PATH_FORBIDDEN")
    if tool == "RUN_ALLOWLISTED_VALIDATOR" and request.get("validator") not in VALIDATORS:
        reasons.append("VALIDATOR_NOT_ALLOWLISTED")
    if request.get("destructive", False):
        reasons.append("DESTRUCTIVE_ACTION_FORBIDDEN")
    return {
        "schema_version": "wave64.aqa.campaign_tool_decision.v1",
        "decision": "DENY" if reasons else "ALLOW",
        "reasons": sorted(set(reasons)),
        "tool_id": tool,
        "final_acceptance_authority": "CODEX",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    decision = evaluate(json.loads(args.request.read_text(encoding="utf-8")))
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["decision"] == "ALLOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
