#!/usr/bin/env python3
"""Compile a fail-closed read-only MaskFactory artifact consumer contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_maskfactory_consumer_contract.schema.json"
REQUIRED_ROLES = {
    "source_media",
    "candidate_mask",
    "accepted_golden_reference",
    "target_overlay",
}
REQUIRED_GATES = {
    "geometry",
    "golden_hash",
    "target_binding",
    "completeness",
    "leakage",
    "boundary",
    "alpha",
    "topology",
    "overlay",
}


class ConsumerContractError(ValueError):
    """Raised when an external mask package is not safe to consume."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _validate_relative_path(value: str) -> None:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not value
        or value.startswith(("/", "\\"))
        or ":" in value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
    ):
        raise ConsumerContractError(f"artifact path is not a safe relative path: {value}")


def compile_contract(draft: dict[str, Any]) -> dict[str, Any]:
    contract = copy.deepcopy(draft)
    if contract.get("schema_version") != "wave64.aqa.maskfactory_consumer_contract.v1":
        raise ConsumerContractError("unsupported schema_version")
    producer = contract.get("producer")
    if not isinstance(producer, dict) or producer.get("producer_id") != "MaskFactory":
        raise ConsumerContractError("producer must be MaskFactory")
    if producer.get("repository_class") != "external_read_only":
        raise ConsumerContractError("MaskFactory repository must be external_read_only")
    authority = contract.get("authority")
    if not isinstance(authority, dict):
        raise ConsumerContractError("authority is required")
    if authority.get("external_writes_allowed") is not False:
        raise ConsumerContractError("external MaskFactory writes are forbidden")
    if authority.get("candidate_only") is not True:
        raise ConsumerContractError("MaskFactory output must remain candidate-only")
    if authority.get("product_promotion_allowed") is not False:
        raise ConsumerContractError("MaskFactory contract cannot grant promotion")

    artifacts = contract.get("artifacts")
    if not isinstance(artifacts, list):
        raise ConsumerContractError("artifacts must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    by_role: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ConsumerContractError("every artifact must be an object")
        artifact_id = artifact.get("artifact_id")
        role = artifact.get("role")
        if not isinstance(artifact_id, str) or artifact_id in by_id:
            raise ConsumerContractError("artifact IDs must be unique non-empty strings")
        if not isinstance(role, str) or role in by_role:
            raise ConsumerContractError("artifact roles must be unique")
        _validate_relative_path(str(artifact.get("relative_path", "")))
        by_id[artifact_id] = artifact
        by_role[role] = artifact
    if set(by_role) != REQUIRED_ROLES:
        raise ConsumerContractError("exact source candidate golden and overlay roles are required")

    target = contract.get("target_binding")
    if not isinstance(target, dict):
        raise ConsumerContractError("target_binding is required")
    source = by_role["source_media"]
    if target.get("source_artifact_id") != source["artifact_id"]:
        raise ConsumerContractError("target binding must reference the source artifact")
    width, height = source.get("width"), source.get("height")
    if any(
        artifact.get("width") != width or artifact.get("height") != height
        for artifact in by_role.values()
    ):
        raise ConsumerContractError("source candidate golden and overlay geometry must match")

    quality = contract.get("quality_contract")
    if not isinstance(quality, dict):
        raise ConsumerContractError("quality_contract is required")
    golden = by_role["accepted_golden_reference"]
    if quality.get("golden_reference_artifact_id") != golden["artifact_id"]:
        raise ConsumerContractError("quality contract must bind the accepted golden hash")
    if set(quality.get("required_gates") or []) != REQUIRED_GATES:
        raise ConsumerContractError("all deterministic golden-mask gates are required")

    contract["contract_id"] = "0" * 64
    contract["admission_disposition"] = "READY_FOR_DETERMINISTIC_MASK_QA"
    contract["runtime_authority_granted"] = False
    contract["promotion_eligible"] = False
    contract["contract_id"] = hashlib.sha256(canonical_bytes(contract)).hexdigest()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(contract)
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        result = compile_contract(draft)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise ConsumerContractError("output already exists; contracts are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, ConsumerContractError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
