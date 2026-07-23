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
SCHEMA_PATHS = {
    "wave64.aqa.campaign.v1": (
        ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_contract.schema.json"
    ),
    "wave64.aqa.campaign.v2": (
        ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_contract_v2.schema.json"
    ),
}
ID_PLACEHOLDER = "0" * 64
IMPLEMENTER = "W64-AQA-ROLE-IMPLEMENTER"
REVIEWER = "W64-AQA-ROLE-REVIEWER"
JUROR = "W64-AQA-ROLE-INDEPENDENT-JUROR"
ARBITER = "W64-AQA-ROLE-ARBITER"
CONTROLLER = "W64-AQA-ROLE-CONTROLLER"
REPAIR_PLANNER = "W64-AQA-ROLE-REPAIR-PLANNER"
DETERMINISTIC = "W64-AQA-ROLE-DETERMINISTIC"
EVIDENCE_COMPILER = "W64-AQA-ROLE-EVIDENCE-COMPILER"
REVIEW_CHAIN_ROLES = (IMPLEMENTER, REVIEWER, JUROR, ARBITER)
BUNDLE_ROLES = (
    CONTROLLER,
    IMPLEMENTER,
    REVIEWER,
    JUROR,
    ARBITER,
    REPAIR_PLANNER,
    DETERMINISTIC,
    EVIDENCE_COMPILER,
)
CLOSED_LOOP_STAGES = {
    "GENERATE_OR_IMPLEMENT", "DETERMINISTIC_QA", "PRIMARY_REVIEW",
    "INDEPENDENT_FAMILY_JUROR", "CONSENSUS_OR_ARBITER", "DEFECT_TAXONOMY",
    "TARGETED_REPAIR", "REGRESSION_QA", "RE_REVIEW", "TERMINALIZE",
}


class CampaignError(ValueError):
    """Raised when a campaign violates a schema or semantic invariant."""


def canonical_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _schema(schema_version: str) -> dict[str, Any]:
    try:
        path = SCHEMA_PATHS[schema_version]
    except KeyError as exc:
        raise CampaignError(f"unsupported campaign schema version: {schema_version}") from exc
    return json.loads(path.read_text(encoding="utf-8"))


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
    missing_roles = set(BUNDLE_ROLES) - set(by_role)
    if missing_roles:
        errors.append(f"required campaign roles are missing: {sorted(missing_roles)}")
    else:
        families = [by_role[role]["family_id"] for role in REVIEW_CHAIN_ROLES]
        if len(set(families)) != 4:
            errors.append("implementer, reviewer, juror, and arbiter must use independent model families")
        checkpoints = [
            by_role[role]["checkpoint_sha256"]
            for role in REVIEW_CHAIN_ROLES
            if "checkpoint_sha256" in by_role[role]
        ]
        if len(set(checkpoints)) != len(checkpoints):
            errors.append("implementer, reviewer, juror, and arbiter must use independent checkpoints")
        qualified = all(by_role[role]["qualification_state"] == "QUALIFIED" for role in BUNDLE_ROLES)
        expected_admission = (
            "READY_CPU_SHADOW"
            if qualified and all(job["phase"] == "CPU" for job in jobs)
            else "READY_FOR_LEASE"
            if qualified
            else "BLOCKED_UNQUALIFIED"
        )
        if contract["admission_disposition"] != expected_admission:
            errors.append("admission disposition does not match role qualification and phase requirements")
    if contract["campaign_profile"] == "MULTIMODAL_MEDIA_CAMPAIGN" and contract["bulk_manifest"] is None:
        errors.append("multimodal media campaigns require a frozen bulk manifest")
    if contract["campaign_profile"] == "DEVELOPMENT_CAMPAIGN" and contract["bulk_manifest"] is not None:
        errors.append("development campaigns must not attach a multimodal bulk manifest")
    if contract["qualification_mode"] != "STATIC_SHADOW":
        missing_stages = CLOSED_LOOP_STAGES - {job["stage"] for job in jobs}
        if missing_stages:
            errors.append(f"non-shadow campaign is missing closed-loop stages: {sorted(missing_stages)}")
    return errors


def compile_contract(draft: dict[str, Any]) -> dict[str, Any]:
    if "campaign_id" in draft:
        raise CampaignError("draft must not supply campaign_id")
    if "admission_disposition" in draft:
        raise CampaignError("draft must not supply admission_disposition")
    contract = copy.deepcopy(draft)
    bindings = {item.get("role_id"): item for item in contract.get("model_bindings", [])}
    qualified = all(
        role in bindings and bindings[role].get("qualification_state") == "QUALIFIED"
        for role in BUNDLE_ROLES
    )
    contract["admission_disposition"] = (
        "READY_CPU_SHADOW"
        if qualified and all(job.get("phase") == "CPU" for job in contract.get("jobs", []))
        else "READY_FOR_LEASE"
        if qualified
        else "BLOCKED_UNQUALIFIED"
    )
    contract["campaign_id"] = ID_PLACEHOLDER
    validator = jsonschema.Draft7Validator(
        _schema(contract.get("schema_version", "")),
        format_checker=jsonschema.FormatChecker(),
    )
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
    jsonschema.Draft7Validator(
        _schema(contract.get("schema_version", "")),
        format_checker=jsonschema.FormatChecker(),
    ).validate(contract)
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


def verify_sealed_job_bytes(contract: dict[str, Any], repository_root: Path) -> None:
    """Bind every referenced child contract to safe path, bytes, SHA-256, and embedded ID."""

    root = repository_root.resolve()
    for job in contract["jobs"]:
        if not _is_safe_relative(job["contract_path"]):
            raise CampaignError(f"contract path escapes repository: {job['node_id']}")
        path = (root / job["contract_path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise CampaignError(f"contract path escapes repository: {job['node_id']}") from exc
        if not path.is_file():
            raise CampaignError(f"sealed child contract is missing: {job['node_id']}")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != job["contract_sha256"]:
            raise CampaignError(f"sealed child contract hash mismatch: {job['node_id']}")
        try:
            child = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise CampaignError(f"sealed child contract is invalid JSON: {job['node_id']}") from exc
        if child.get("contract_id") != job["contract_id"]:
            raise CampaignError(f"sealed child embedded contract_id mismatch: {job['node_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-job-bytes", type=Path, help="Verify child contracts under this repository root")
    args = parser.parse_args()
    try:
        document = json.loads(args.document.read_text(encoding="utf-8"))
        if args.verify:
            verify_contract(document)
            result = document
        else:
            result = compile_contract(document)
        if args.verify_job_bytes:
            verify_sealed_job_bytes(result, args.verify_job_bytes)
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
