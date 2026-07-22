#!/usr/bin/env python3
"""Compile path-safe, candidate-only campaign Plan/Items/Tracker deltas."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_proposed_delta.schema.json"
PLACEHOLDER = "0" * 64


class DeltaError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _safe(path: str) -> bool:
    pure = PurePosixPath(path.replace("\\", "/"))
    return bool(path) and not pure.is_absolute() and ":" not in pure.parts[0] and ".." not in pure.parts


def compile_delta(draft: dict[str, Any]) -> dict[str, Any]:
    if "delta_id" in draft:
        raise DeltaError("draft must not supply delta_id")
    result = copy.deepcopy(draft)
    result["authority"] = {"candidate_only": True, "may_commit": False, "final_acceptance_authority": "CODEX"}
    result["delta_id"] = PLACEHOLDER
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft7Validator(schema).validate(result)
    except jsonschema.ValidationError as exc:
        raise DeltaError(f"schema violation: {exc.message}") from exc
    paths = [change["relative_path"] for change in result["changes"]]
    if len(paths) != len(set(paths)):
        raise DeltaError("proposed delta paths must be unique")
    if any(not _safe(path) for path in paths):
        raise DeltaError("proposed delta path escapes repository")
    result["delta_id"] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


def verify_delta(result: dict[str, Any]) -> None:
    candidate = copy.deepcopy(result)
    observed = candidate["delta_id"]
    candidate["delta_id"] = PLACEHOLDER
    expected = hashlib.sha256(canonical_bytes(candidate)).hexdigest()
    if observed != expected:
        raise DeltaError("delta_id does not match canonical content")
    compile_input = copy.deepcopy(result)
    del compile_input["delta_id"]
    del compile_input["authority"]
    if compile_delta(compile_input) != result:
        raise DeltaError("proposed delta failed deterministic replay")
