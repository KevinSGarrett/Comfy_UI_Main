#!/usr/bin/env python3
"""Compile and verify immutable W64-AQA campaign contracts."""

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
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_contract.schema.json"
ID_PLACEHOLDER = "0" * 64
IMPLEMENTER = "W64-AQA-ROLE-IMPLEMENTER"
REVIEWER = "W64-AQA-ROLE-REVIEWER"
JUROR = "W64-AQA-ROLE-INDEPENDENT-JUROR"


class CampaignError(ValueError):
    """Raised when a campaign violates a schema or semantic invariant."""


def canonical_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _is_safe_relative(path: str) -> bool:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    return not pure.is_absolute() and ":" not in pure.parts[0] and ".." not in pure.parts


def _topological_order(nodes: list[str], dependencies: dict[str, list[str]]) -> list[str]:
    remaining = {node: set(dependencies[node]) for node in nodes}
    order: list[str] = []
    while remaining:
        ready = sorted(node for node, deps in remaining.items() if not deps)
        if not ready:
            raise CampaignError("campaign DAG contains a cycle")
        order.extend(ready)
        for node in ready:
            del remaining[node]
        for deps in remaining.values():
            deps.difference_update(ready)
    return order


def semantic_validate(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    jobs = contract["jobs"]
    job_ids = [job["node_id"] for job in jobs]
    dag_ids = [node["node_id"] for node in contract["dag"]]
    if len(job_ids) != len(set(job_ids)):
        errors.append("job node IDs must be unique")
    if len(dag_ids) != len(set(dag_ids)):
        errors.append("DAG node IDs must be unique")
    if set(job_ids) != set(dag_ids):
        errors.append("DAG nodes must exactly match job nodes")
    known = set(dag_ids)
    dependencies = {node["node_id"]: node["depends_on"] for node in contract["dag"]}
    for node_id, deps in dependencies.items():
        if node_id in deps:
            errors.append(f"node depends on itself: {node_id}")
        missing = set(deps) - known
        if missing:
            errors.append(f"node {node_id} has missing dependencies: {sorted(missing)}")
    if not errors:
        try:
            _topological_order(sorted(known), dependencies)
        except CampaignError as exc:
            errors.append(str(exc))
    for job in jobs:
        if not _is_safe_relative(job["contract_path"]):
            errors.append(f"contract path escapes repository: {job['node_id']}")

    bindings = contract["model_bindings"]
    role_ids = [binding["role_id"] for binding in bindings]
    if len(role_ids) != len(set(role_ids)):
        errors.append("model binding role IDs must be unique")
    by_role = {binding["role_id"]: binding for binding in bindings}
    unknown_job_roles = {job["role_id"] for job in jobs} - set(by_role)
    if unknown_job_roles:
        errors.append(f"jobs reference undeclared roles: {sorted(unknown_job_roles)}")
    missing_roles = {IMPLEMENTER, REVIEWER, JUROR} - set(by_role)
    if missing_roles:
        errors.append(f"required campaign roles are missing: {sorted(missing_roles)}")
    elif any(by_role[role]["qualification_state"] != "QUALIFIED" for role in (IMPLEMENTER, REVIEWER, JUROR)):
        errors.append("campaign roles must be independently qualified")
    else:
        families = [by_role[role]["family_id"] for role in (IMPLEMENTER, REVIEWER, JUROR)]
        if len(set(families)) != 3:
            errors.append("implementer, reviewer, and juror must use independent model families")
        checkpoints = [by_role[role]["checkpoint_sha256"] for role in (IMPLEMENTER, REVIEWER, JUROR)]
        if len(set(checkpoints)) != 3:
            errors.append("implementer, reviewer, and juror must use independent checkpoints")
    return errors


def compile_contract(draft: dict[str, Any]) -> dict[str, Any]:
    if "campaign_id" in draft:
        raise CampaignError("draft must not supply campaign_id")
    contract = copy.deepcopy(draft)
    contract["campaign_id"] = ID_PLACEHOLDER
    validator = jsonschema.Draft7Validator(_schema(), format_checker=jsonschema.FormatChecker())
    try:
        validator.validate(contract)
    except jsonschema.ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "$"
        raise CampaignError(f"schema violation at {location}: {exc.message}") from exc
    errors = semantic_validate(contract)
    if errors:
        raise CampaignError("; ".join(errors))
    contract["campaign_id"] = hashlib.sha256(canonical_bytes(contract)).hexdigest()
    validator.validate(contract)
    return contract


def verify_contract(contract: dict[str, Any]) -> None:
    jsonschema.Draft7Validator(_schema(), format_checker=jsonschema.FormatChecker()).validate(contract)
    errors = semantic_validate(contract)
    if errors:
        raise CampaignError("; ".join(errors))
    identity_input = copy.deepcopy(contract)
    observed = identity_input["campaign_id"]
    identity_input["campaign_id"] = ID_PLACEHOLDER
    expected = hashlib.sha256(canonical_bytes(identity_input)).hexdigest()
    if observed != expected:
        raise CampaignError("campaign_id does not match canonical campaign content")


def topological_order(contract: dict[str, Any]) -> list[str]:
    verify_contract(contract)
    nodes = sorted(node["node_id"] for node in contract["dag"])
    deps = {node["node_id"]: node["depends_on"] for node in contract["dag"]}
    return _topological_order(nodes, deps)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.document.read_text(encoding="utf-8"))
        if args.verify:
            verify_contract(document)
            result = document
        else:
            result = compile_contract(document)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise CampaignError("output already exists; campaign contracts are immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, CampaignError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
