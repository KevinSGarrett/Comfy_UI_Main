#!/usr/bin/env python3
"""Compile the fail-closed W64-AQA sole-pod qualification campaign queue."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = Path("Plan/Tracker/Evidence/W64_AQA_ROLE_QUALIFICATION_EXECUTION_MATRIX_20260722.json")
ROLE_REGISTRY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json")
INVENTORY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_autonomous_role_package_inventory.json")
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_sole_pod_qualification_campaign_policy.json")
GENERATION_STACK_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_generation_stack_registry.json")
GENERATION_STACK_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_generation_stack_registry.schema.json")
GENERATION_DEPENDENCY_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_dependency_bundle.schema.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_qualification_campaign_queue.schema.json")
DEFAULT_OUTPUT = Path("Plan/Tracker/Evidence/W64_AQA_SOLE_POD_QUALIFICATION_CAMPAIGN_QUEUE_20260722.json")


class QueueError(ValueError):
    """Raised when campaign selection cannot remain complete and fail closed."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QueueError(f"JSON root must be an object: {path}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_evidence(package: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    identity = package["identity"]
    installation = package["installation"]
    identity_state = identity["identity_state"]
    license_state = identity["license_state"]
    installation_state = installation["state"]
    artifact_digest = installation.get("artifact_digest")
    identity_exact = "REVISION_PINNED" in identity_state or (
        identity_state.startswith("LOCAL_DIGEST_VERIFIED")
        and "UPSTREAM_REVISION_UNVERIFIED" not in identity_state
    )
    license_accepted = "ACCEPTED" in license_state
    installed = artifact_digest is not None and (
        "INSTALLED" in installation_state or "PROMOTED" in installation_state
    )
    dependency_required = "dependency_environment" in package.get("qualification", {}).get(
        "required_gates", []
    )
    dependency_state = package.get("dependency_environment", {}).get("state")
    dependency_environment_ready = not dependency_required or (
        isinstance(dependency_state, str) and "INSTALLED" in dependency_state
    )
    exact = identity_exact and license_accepted and installed
    blockers: list[str] = []
    if not identity_exact or "UPSTREAM_REVISION_UNVERIFIED" in identity_state:
        blockers.append(f"{package['package_id']}:EXACT_UPSTREAM_REVISION_OR_IDENTITY_NOT_VERIFIED")
    if not license_accepted:
        blockers.append(f"{package['package_id']}:PROJECT_LICENSE_ACCEPTANCE_MISSING")
    if not installed:
        blockers.append(f"{package['package_id']}:EXACT_ARTIFACT_NOT_INSTALLED")
    if not dependency_environment_ready:
        blockers.append(f"{package['package_id']}:DEPENDENCY_ENVIRONMENT_NOT_IMPORT_VERIFIED")
    return ({
        "package_id": package["package_id"],
        "identity_state": identity_state,
        "license_state": license_state,
        "installation_state": installation_state,
        "artifact_digest": artifact_digest,
        "exact_identity_installed_and_license_accepted": exact,
        "dependency_environment_required": dependency_required,
        "dependency_environment_state": dependency_state,
        "dependency_environment_ready": dependency_environment_ready,
    }, blockers)


def generation_stack_evidence(root: Path, registry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    Draft202012Validator(load_json(root / GENERATION_STACK_SCHEMA_PATH)).validate(registry)
    selected = [stack for stack in registry["stacks"] if stack["selection_state"] == "SELECTED_INACTIVE"]
    if len(selected) != 1 or selected[0]["stack_id"] != registry["selected_stack_id"]:
        raise QueueError("generation registry must have exactly one selected inactive stack")
    for candidate in registry["stacks"]:
        candidate_binding = candidate["package_binding"]
        candidate_path = root / Path(candidate_binding["path"])
        if sha256_file(candidate_path) != candidate_binding["sha256"]:
            raise QueueError(f"generation package hash drift: {candidate['stack_id']}")
        candidate_package = load_json(candidate_path)
        candidate_asset = candidate["asset"]
        candidate_file = candidate_package.get("files", [{}])[0]
        if (
            candidate_package.get("package_id") != candidate_asset["package_id"]
            or candidate_package.get("repository") != candidate_asset["repository"]
            or candidate_package.get("revision") != candidate_asset["revision"]
            or candidate_package.get("license_metadata") != candidate_asset["license_metadata"]
            or candidate_package.get("root") != candidate_asset["root"]
            or candidate_file.get("path") != candidate_asset["path"]
            or candidate_file.get("bytes") != candidate_asset["bytes"]
            or candidate_file.get("sha256") != candidate_asset["sha256"]
            or candidate_package.get("license_acceptance_authority") is not False
            or candidate["execution"]["executable"] is not False
        ):
            raise QueueError(f"generation stack identity or authority drift: {candidate['stack_id']}")
    stack = selected[0]
    package_binding = stack["package_binding"]
    asset = stack["asset"]
    dependency_binding = stack.get("dependency_bundle")
    if not dependency_binding:
        raise QueueError("selected generation stack has no dependency bundle")
    dependency_path = root / Path(dependency_binding["path"])
    if sha256_file(dependency_path) != dependency_binding["sha256"]:
        raise QueueError("selected generation dependency bundle hash drift")
    dependency = load_json(dependency_path)
    Draft202012Validator(load_json(root / GENERATION_DEPENDENCY_SCHEMA_PATH)).validate(dependency)
    dependency_for_id = json.loads(json.dumps(dependency))
    dependency_for_id["bundle_id"] = "0" * 64
    expected_dependency_id = hashlib.sha256(canonical_bytes(dependency_for_id)).hexdigest()
    component_states = [item.get("current_pod_state") for item in dependency.get("components", [])]
    if (
        dependency.get("bundle_id") != expected_dependency_id
        or dependency.get("stack_id") != stack["stack_id"]
        or dependency.get("authority", {}).get("current_pod_complete") is not False
        or component_states != ["PROMOTED_HASH_VERIFIED", "NOT_IN_ACCEPTED_PROMOTED_LEDGER", "NOT_IN_ACCEPTED_PROMOTED_LEDGER"]
    ):
        raise QueueError("selected generation dependency identity or authority drift")
    return ({
        "path": GENERATION_STACK_PATH.as_posix(),
        "sha256": sha256_file(root / GENERATION_STACK_PATH),
        "stack_id": stack["stack_id"],
        "package_id": asset["package_id"],
        "package_path": package_binding["path"],
        "package_sha256": package_binding["sha256"],
        "asset_sha256": asset["sha256"],
        "dependency_bundle_path": dependency_binding["path"],
        "dependency_bundle_sha256": dependency_binding["sha256"],
        "dependency_bundle_id": dependency["bundle_id"],
        "current_pod_complete": dependency["authority"]["current_pod_complete"],
        "state": stack["selection_state"],
        "exact_storage_identity_bound": stack["execution"]["exact_storage_identity_bound"],
        "executable": stack["execution"]["executable"],
    }, list(stack["blockers"]))


def compile_queue(root: Path) -> dict[str, Any]:
    matrix = load_json(root / MATRIX_PATH)
    role_registry = load_json(root / ROLE_REGISTRY_PATH)
    inventory = load_json(root / INVENTORY_PATH)
    policy = load_json(root / POLICY_PATH)
    generation_registry = load_json(root / GENERATION_STACK_PATH)
    required_pod_policy = {
        "pod_id": "1q4ji0gg1fkhvt",
        "project": "comfyui_main",
        "profile": "comfyui_model_qualification",
        "lease_mode": "exclusive",
        "one_gpu_campaign_at_a_time": True,
        "external_inference_forbidden": True,
        "authorized_migration_watcher_id": "runpod-us-wa-1-2xa40-guarded-migration-watcher",
        "competing_alternative_pod_watcher_forbidden": True,
        "current_pod_authoritative_until_verified_migration_complete": True,
        "coordinator_admission_required": True,
        "idle_telemetry_is_not_authority": True,
        "foreign_recovery_override_forbidden": True,
    }
    if any(policy["pod_policy"].get(key) != value for key, value in required_pod_policy.items()):
        raise QueueError("sole-pod coordinator safety policy drift")
    matrix_roles = [plan["role_id"] for plan in matrix["role_plans"]]
    registry_roles = [role["role_id"] for role in role_registry["roles"]]
    bindings = policy["role_bindings"]
    binding_roles = [binding["role_id"] for binding in bindings]
    if len(matrix_roles) != 12 or len(set(matrix_roles)) != 12:
        raise QueueError("execution matrix must contain twelve unique roles")
    if set(matrix_roles) != set(registry_roles) or set(matrix_roles) != set(binding_roles):
        raise QueueError("matrix, role registry, and campaign policy role sets differ")
    if len(binding_roles) != len(set(binding_roles)):
        raise QueueError("campaign policy contains duplicate role bindings")
    package_records = inventory["packages"]
    packages = {package["package_id"]: package for package in package_records}
    if len(packages) != len(package_records):
        raise QueueError("role package inventory contains duplicate package ids")
    campaigns: list[dict[str, Any]] = []
    campaign_ids: set[str] = set()
    for source in policy["pre_role_campaigns"]:
        admission_path = Path(source["admission_path"])
        admission = load_json(root / admission_path)
        if admission.get("status") != source["required_status"]:
            raise QueueError(f"admission status drift: {admission_path}")
        unknown_dependencies = set(source.get("depends_on", [])) - campaign_ids
        if unknown_dependencies:
            raise QueueError(f"supporting campaign has unknown or forward dependencies: {sorted(unknown_dependencies)}")
        package_id = admission["model"]["package_id"]
        campaign = {
            "sequence": len(campaigns) + 1,
            "campaign_id": source["campaign_id"],
            "kind": "supporting_component",
            "role_id": None,
            "component": source["component"],
            "execution_lane": "exclusive_gpu",
            "package_ids": [package_id],
            "package_evidence": [],
            "admission": {"path": admission_path.as_posix(), "sha256": sha256_file(root / admission_path), "status": admission["status"], "package_id": package_id},
            "certificate": None,
            "generation_stack": None,
            "depends_on": source.get("depends_on", []),
            "execution_steps": source["execution_steps"],
            "readiness": "ADMITTED_COORDINATOR_GATE_REQUIRED",
            "blockers": ["FRESH_COORDINATOR_ADMISSION_AND_EXACT_EXCLUSIVE_LEASE_REQUIRED"],
            "operational": False,
        }
        campaigns.append(campaign)
        campaign_ids.add(campaign["campaign_id"])
    matrix_by_role = {plan["role_id"]: plan for plan in matrix["role_plans"]}
    for binding in bindings:
        role_id = binding["role_id"]
        evidence: list[dict[str, Any]] = []
        blockers = list(binding.get("additional_blockers", []))
        exact_by_id: dict[str, bool] = {}
        for package_id in binding["package_ids"]:
            if package_id not in packages:
                raise QueueError(f"unknown package binding: {package_id}")
            item, package_blockers = package_evidence(packages[package_id])
            evidence.append(item)
            exact_by_id[package_id] = (
                item["exact_identity_installed_and_license_accepted"]
                and item["dependency_environment_ready"]
            )
            blockers.extend(package_blockers)
        mode = binding["binding_mode"]
        certificate_binding = None
        generation_stack_binding = None
        if mode == "all":
            package_gate = bool(exact_by_id) and all(exact_by_id.values())
        elif mode == "any":
            preferred = binding.get("preferred_package_id")
            if preferred not in exact_by_id:
                raise QueueError(f"preferred package is absent from binding: {role_id}")
            package_gate = exact_by_id[preferred]
            blockers = [value for value in blockers if value.startswith(f"{preferred}:")]
        elif mode == "none":
            certificate_path_value = binding.get("certificate_path")
            if certificate_path_value:
                certificate_path = Path(certificate_path_value)
                bundle_path = Path(binding.get("bundle_path", ""))
                certificate = load_json(root / certificate_path)
                bundle = load_json(root / bundle_path)
                if (
                    certificate.get("role_id") != role_id
                    or certificate.get("qualification_disposition") != "QUALIFIED_FOR_DECLARED_SCOPE"
                    or certificate.get("operational_authority_granted") is not True
                    or certificate.get("execution_matrix_sha256") != sha256_file(root / MATRIX_PATH)
                    or bundle.get("role_id") != role_id
                    or bundle.get("certificate_id") != certificate.get("certificate_id")
                    or bundle.get("inputs", {}).get("matrix", {}).get("sha256") != sha256_file(root / MATRIX_PATH)
                    or bundle.get("inputs", {}).get("executor", {}).get("sha256")
                    != sha256_file(root / Path(bundle.get("inputs", {}).get("executor", {}).get("path", "")))
                    or bundle.get("authority", {}).get("declared_local_deterministic_scope") is not True
                ):
                    raise QueueError(f"local certificate is not valid for current matrix: {role_id}")
                certificate_binding = {
                    "path": certificate_path.as_posix(),
                    "sha256": sha256_file(root / certificate_path),
                    "certificate_id": certificate["certificate_id"],
                    "qualification_disposition": certificate["qualification_disposition"],
                    "bundle_path": bundle_path.as_posix(),
                    "bundle_sha256": sha256_file(root / bundle_path),
                    "bundle_id": bundle["bundle_id"],
                }
                package_gate = True
            elif binding.get("generation_stack_path"):
                if Path(binding["generation_stack_path"]) != GENERATION_STACK_PATH:
                    raise QueueError(f"unexpected generation stack registry: {role_id}")
                if role_id != "W64-AQA-ROLE-GENERATION":
                    raise QueueError(f"generation stack bound to non-generation role: {role_id}")
                generation_stack_binding, generation_blockers = generation_stack_evidence(root, generation_registry)
                blockers.extend(generation_blockers)
                package_gate = False
            else:
                package_gate = False
        else:
            raise QueueError(f"unsupported binding mode: {mode}")
        depends_on = binding.get("depends_on", [])
        unknown_dependencies = set(depends_on) - campaign_ids
        if unknown_dependencies:
            raise QueueError(f"role campaign has unknown dependencies: {sorted(unknown_dependencies)}")
        if certificate_binding:
            readiness = "QUALIFIED_DECLARED_LOCAL_SCOPE"
            blockers = []
        elif package_gate:
            readiness = "PREPARED_DEPENDENCIES_AND_COORDINATOR_GATE_REQUIRED"
            blockers.append("FRESH_COORDINATOR_ADMISSION_AND_EXACT_EXCLUSIVE_LEASE_REQUIRED")
            if depends_on:
                blockers.append("DEPENDENT_CAMPAIGN_RECEIPTS_REQUIRED")
            blockers = sorted(set(blockers))
        else:
            readiness = "HELD_PREREQUISITES_INCOMPLETE"
            blockers = sorted(set(blockers or ["EXACT_ROLE_PACKAGE_BINDING_INCOMPLETE"]))
        role_plan = matrix_by_role[role_id]
        campaign_id = "W64-AQA-CAMPAIGN-ROLE-" + role_id.removeprefix("W64-AQA-ROLE-")
        campaigns.append({
            "sequence": len(campaigns) + 1,
            "campaign_id": campaign_id,
            "kind": "role_qualification",
            "role_id": role_id,
            "component": None,
            "execution_lane": binding["execution_lane"],
            "package_ids": binding["package_ids"],
            "package_evidence": evidence,
            "admission": None,
            "certificate": certificate_binding,
            "generation_stack": generation_stack_binding,
            "depends_on": depends_on,
            "execution_steps": matrix["execution_order"],
            "readiness": readiness,
            "blockers": blockers,
            "operational": bool(certificate_binding) or role_plan["operational"],
        })
        campaign_ids.add(campaign_id)
    if [campaign["sequence"] for campaign in campaigns] != list(range(1, 15)):
        raise QueueError("campaign sequence is not contiguous")
    prepared = sum(campaign["readiness"] != "HELD_PREREQUISITES_INCOMPLETE" for campaign in campaigns)
    queue = {
        "schema_version": "wave64.aqa.qualification_campaign_queue.v1",
        "program_id": "W64-AQA",
        "status": "SOLE_POD_QUEUE_FROZEN_RUNTIME_COORDINATOR_GATE_REQUIRED",
        "inputs": {
            "execution_matrix": {"path": MATRIX_PATH.as_posix(), "sha256": sha256_file(root / MATRIX_PATH)},
            "role_registry": {"path": ROLE_REGISTRY_PATH.as_posix(), "sha256": sha256_file(root / ROLE_REGISTRY_PATH)},
            "package_inventory": {"path": INVENTORY_PATH.as_posix(), "sha256": sha256_file(root / INVENTORY_PATH)},
            "campaign_policy": {"path": POLICY_PATH.as_posix(), "sha256": sha256_file(root / POLICY_PATH)},
            "generation_stack_registry": {"path": GENERATION_STACK_PATH.as_posix(), "sha256": sha256_file(root / GENERATION_STACK_PATH)},
        },
        "pod_gate": {
            "pod_id": policy["pod_policy"]["pod_id"], "project": policy["pod_policy"]["project"],
            "profile": policy["pod_policy"]["profile"], "lease_mode": policy["pod_policy"]["lease_mode"],
            "one_gpu_campaign_at_a_time": True, "coordinator_admission_required": True,
            "runtime_snapshot_bound": False, "idle_telemetry_is_not_authority": True,
            "foreign_recovery_override_forbidden": True,
        },
        "campaigns": campaigns,
        "coverage": {
            "pre_role_campaign_count": 2, "role_campaign_count": 12,
            "matrix_role_count": len(matrix_roles), "all_matrix_roles_bound": True,
            "prepared_campaign_count": prepared, "held_campaign_count": len(campaigns) - prepared,
        },
        "next_action": {
            "campaign_id": campaigns[0]["campaign_id"], "runnable_now": False,
            "required_transition": "FRESH_COORDINATOR_ADMISSION_AND_EXACT_LEASE_IS_GRANTED",
            "execution_steps": campaigns[0]["execution_steps"],
        },
        "queue_sha256": "0" * 64,
        "authority": {"execution_planning": True, "runtime": False, "capacity": False, "quality": False, "independent_juror": False, "golden_mask": False, "activation": False, "promotion": False},
    }
    queue["queue_sha256"] = hashlib.sha256(canonical_bytes(queue)).hexdigest()
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(queue)
    return queue


def validate_queue(root: Path, queue: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(queue)
    if queue != compile_queue(root):
        raise QueueError("qualification queue does not replay from current inputs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.validate:
        validate_queue(root, load_json(args.validate))
        print(json.dumps({"status": "PASS", "queue": str(args.validate)}))
        return 0
    queue = compile_queue(root)
    output = args.output or root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
