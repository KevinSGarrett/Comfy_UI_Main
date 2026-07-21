#!/usr/bin/env python3
"""Compile immutable W64-AQA job contracts without acquiring runtime authority."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_job_contract.schema.json"
CONTRACT_ID_PLACEHOLDER = "0" * 64
VISUAL_PRODUCTION_REQUIRED_ROLES = {
    "W64-AQA-ROLE-DETERMINISTIC",
    "W64-AQA-ROLE-PRIMARY-VISUAL",
    "W64-AQA-ROLE-INDEPENDENT-JUROR",
}
AUDIO_PRODUCTION_REQUIRED_ROLES = {
    "W64-AQA-ROLE-DETERMINISTIC",
    "W64-AQA-ROLE-AUDIO-SEMANTIC",
    "W64-AQA-ROLE-INDEPENDENT-JUROR",
}
AV_PRODUCTION_REQUIRED_ROLES = VISUAL_PRODUCTION_REQUIRED_ROLES | {
    "W64-AQA-ROLE-AUDIO-SEMANTIC"
}
VISUAL_SHADOW_REQUIRED_ROLES = {
    "W64-AQA-ROLE-DETERMINISTIC",
    "W64-AQA-ROLE-STRICT-VISUAL",
}
DETERMINISTIC_SHADOW_REQUIRED_ROLES = {"W64-AQA-ROLE-DETERMINISTIC"}


def _expected_required_roles(contract: dict[str, Any]) -> set[str]:
    modality = contract["modality"]
    if contract["execution_mode"] == "shadow_qualification":
        if modality in {"audio", "workflow"}:
            return DETERMINISTIC_SHADOW_REQUIRED_ROLES
        return VISUAL_SHADOW_REQUIRED_ROLES
    if modality == "audio":
        return AUDIO_PRODUCTION_REQUIRED_ROLES
    if modality == "av":
        return AV_PRODUCTION_REQUIRED_ROLES
    return VISUAL_PRODUCTION_REQUIRED_ROLES


class ContractError(ValueError):
    """Raised when a draft violates semantic contract rules."""


def canonical_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _semantic_errors(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    profile = contract["quality_profile"]
    roles = profile["review_roles"]
    role_ids = [role["role_id"] for role in roles]
    role_map = {role["role_id"]: role for role in roles}
    required = set(profile["required_approval_roles"])
    expected_required = _expected_required_roles(contract)

    if len(role_ids) != len(set(role_ids)):
        errors.append("review role IDs must be unique")
    if not expected_required.issubset(required):
        errors.append(
            "required approvals do not satisfy the selected execution mode: "
            f"missing {sorted(expected_required - required)}"
        )
    if not required.issubset(role_map):
        errors.append("every required approval role must have a review role declaration")
    for role_id in required & set(role_map):
        if not role_map[role_id]["required"] or not role_map[role_id]["can_approve"]:
            errors.append(f"required approval role is not marked required and approving: {role_id}")
    for role in roles:
        if role["authority"] == "triage" and role["can_approve"]:
            errors.append("triage roles can never approve")

    bindings = contract["provenance"]["model_bindings"]
    binding_ids = [binding["role_id"] for binding in bindings]
    if len(binding_ids) != len(set(binding_ids)):
        errors.append("model binding role IDs must be unique")
    missing_bindings = required - set(binding_ids)
    if missing_bindings:
        errors.append(f"required approval roles lack model bindings: {sorted(missing_bindings)}")
    qualification = {item["role_id"]: item["qualification_state"] for item in bindings}
    expected_preflight = (
        "READY_FOR_LEASE"
        if required and all(qualification.get(role_id) == "QUALIFIED" for role_id in required)
        else "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    )
    if contract["preflight_disposition"] != expected_preflight:
        errors.append("preflight disposition does not match required-role qualification")
    expected_promotion = (
        "PRODUCTION_ELIGIBLE_IF_ALL_GATES_PASS"
        if contract["execution_mode"] == "production_release"
        else "EVIDENCE_ONLY"
    )
    if contract["promotion_disposition"] != expected_promotion:
        errors.append("promotion disposition does not match execution mode")

    gate_ids = [gate["gate_id"] for gate in profile["hard_gates"]]
    if len(gate_ids) != len(set(gate_ids)):
        errors.append("hard gate IDs must be unique")

    output_ids = [output["output_id"] for output in contract["requested_outputs"]]
    if len(output_ids) != len(set(output_ids)):
        errors.append("requested output IDs must be unique")
    return errors


def compile_contract(draft: dict[str, Any]) -> dict[str, Any]:
    """Return a validated immutable contract with a deterministic content ID.

    The content ID is SHA-256 over canonical JSON with contract_id set to 64 zeroes.
    Revision changes therefore always produce a new identifier. Compilation does not
    authorize execution; required unqualified roles produce a fail-closed hold.
    """

    if "contract_id" in draft:
        raise ContractError("draft must not supply contract_id")
    if "preflight_disposition" in draft:
        raise ContractError("draft must not supply preflight_disposition")
    if "promotion_disposition" in draft:
        raise ContractError("draft must not supply promotion_disposition")

    contract = copy.deepcopy(draft)
    bindings = contract.get("provenance", {}).get("model_bindings", [])
    required = set(contract.get("quality_profile", {}).get("required_approval_roles", []))
    qualification = {item.get("role_id"): item.get("qualification_state") for item in bindings}
    contract["preflight_disposition"] = (
        "READY_FOR_LEASE"
        if required and all(qualification.get(role_id) == "QUALIFIED" for role_id in required)
        else "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    )
    contract["promotion_disposition"] = (
        "PRODUCTION_ELIGIBLE_IF_ALL_GATES_PASS"
        if contract.get("execution_mode") == "production_release"
        else "EVIDENCE_ONLY"
    )
    contract["contract_id"] = CONTRACT_ID_PLACEHOLDER

    schema = load_schema()
    try:
        jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(contract)
    except jsonschema.ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "$"
        raise ContractError(f"schema violation at {location}: {exc.message}") from exc

    errors = _semantic_errors(contract)
    if errors:
        raise ContractError("; ".join(errors))

    contract["contract_id"] = hashlib.sha256(canonical_bytes(contract)).hexdigest()
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(contract)
    return contract


def verify_contract(contract: dict[str, Any]) -> None:
    """Verify schema, semantic invariants, and immutable content identity."""

    schema = load_schema()
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(contract)
    errors = _semantic_errors(contract)
    if errors:
        raise ContractError("; ".join(errors))
    observed = contract["contract_id"]
    identity_input = copy.deepcopy(contract)
    identity_input["contract_id"] = CONTRACT_ID_PLACEHOLDER
    expected = hashlib.sha256(canonical_bytes(identity_input)).hexdigest()
    if observed != expected:
        raise ContractError("contract_id does not match canonical contract content")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="JSON draft without derived fields")
    parser.add_argument("--output", type=Path, help="Write compiled contract to this new path")
    parser.add_argument("--verify", action="store_true", help="Verify an already compiled contract")
    args = parser.parse_args()

    try:
        document = json.loads(args.draft.read_text(encoding="utf-8"))
        if args.verify:
            verify_contract(document)
            result = document
        else:
            result = compile_contract(document)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise ContractError("output already exists; contract files are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, ContractError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
