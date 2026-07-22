#!/usr/bin/env python3
"""Compile immutable frozen bulk-media manifests for campaign admission."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_bulk_manifest.schema.json"
PLACEHOLDER = "0" * 64


class ManifestError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _safe(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return bool(value) and not path.is_absolute() and ":" not in path.parts[0] and ".." not in path.parts


def compile_manifest(draft: dict[str, Any]) -> dict[str, Any]:
    if "manifest_id" in draft:
        raise ManifestError("draft must not supply manifest_id")
    result = copy.deepcopy(draft)
    result["manifest_id"] = PLACEHOLDER
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft7Validator(schema).validate(result)
    except jsonschema.ValidationError as exc:
        raise ManifestError(f"schema violation: {exc.message}") from exc
    refs = result["prompts"] + result["negative_prompts"] + result["source_assets"] + result["workflows"]
    if any(not _safe(item["relative_path"]) for item in refs):
        raise ManifestError("bulk manifest path escapes campaign workspace")
    result["manifest_id"] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


def verify_manifest(result: dict[str, Any]) -> None:
    candidate = copy.deepcopy(result)
    observed = candidate["manifest_id"]
    candidate["manifest_id"] = PLACEHOLDER
    if hashlib.sha256(canonical_bytes(candidate)).hexdigest() != observed:
        raise ManifestError("manifest_id does not match canonical content")
