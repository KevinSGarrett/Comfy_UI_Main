#!/usr/bin/env python3
"""Compile a truthful, fail-closed W64-AQA real-role bundle contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
COMPILER_PATH = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_contract.py"
)
ROLE_REGISTRY_PATH = (
    ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_role_registry.json"
)
PACKAGE_INVENTORY_PATH = (
    ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_role_package_inventory.json"
)
POLICY_PATH = (
    ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_policy.json"
)
BUNDLE_ROLES = (
    "W64-AQA-ROLE-CONTROLLER",
    "W64-AQA-ROLE-IMPLEMENTER",
    "W64-AQA-ROLE-REVIEWER",
    "W64-AQA-ROLE-INDEPENDENT-JUROR",
    "W64-AQA-ROLE-ARBITER",
    "W64-AQA-ROLE-REPAIR-PLANNER",
    "W64-AQA-ROLE-DETERMINISTIC",
    "W64-AQA-ROLE-EVIDENCE-COMPILER",
)
COMPONENT_ROLES = {
    "W64-AQA-ROLE-DETERMINISTIC",
    "W64-AQA-ROLE-EVIDENCE-COMPILER",
}


class RoleBundleError(ValueError):
    """Raised when a real-role binding would be incomplete or misleading."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha256(value: bytes | str) -> str:
    payload = value.encode() if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()


def canonical_text_sha256(path: Path) -> str:
    return sha256(path.read_bytes().replace(b"\r\n", b"\n"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_compiler():
    spec = importlib.util.spec_from_file_location("w64_campaign_compiler_v2", COMPILER_PATH)
    if not spec or not spec.loader:
        raise RoleBundleError("campaign compiler could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exact_optional_sha(value: Any) -> str | None:
    return value if isinstance(value, str) and len(value) == 64 else None


def build_bindings(root: Path = ROOT) -> list[dict[str, Any]]:
    role_registry = load_json(
        root / ROLE_REGISTRY_PATH.relative_to(ROOT)
    )
    inventory = load_json(
        root / PACKAGE_INVENTORY_PATH.relative_to(ROOT)
    )
    roles = {item["role_id"]: item for item in role_registry["roles"]}
    packages = {item["package_id"]: item for item in inventory["packages"]}
    missing_roles = set(BUNDLE_ROLES) - set(roles)
    if missing_roles:
        raise RoleBundleError(f"bundle roles missing from registry: {sorted(missing_roles)}")

    bindings: list[dict[str, Any]] = []
    for role_id in BUNDLE_ROLES:
        role = roles[role_id]
        binding = {
            "role_id": role_id,
            "family_id": role["family_id"],
            "binding_kind": role["binding_kind"],
            "residency_group": role["residency_group"],
            "capacity_state": role["capacity_state"],
            "qualification_state": role["qualification_state"],
        }
        if role_id in COMPONENT_ROLES:
            if role["binding_kind"] != "CERTIFIED_COMPONENT":
                raise RoleBundleError(f"component role has wrong binding kind: {role_id}")
            certificate_path = root / role["certificate_path"]
            certificate = load_json(certificate_path)
            if canonical_text_sha256(certificate_path) != role["certificate_sha256"]:
                raise RoleBundleError(f"component certificate hash mismatch: {role_id}")
            if (
                certificate["role_id"] != role_id
                or certificate["certificate_id"] != role["certificate_id"]
            ):
                raise RoleBundleError(f"component certificate identity mismatch: {role_id}")
            binding.update(
                {
                    "certificate_id": certificate["certificate_id"],
                    "checkpoint_sha256": certificate["checkpoint_sha256"],
                    "environment_sha256": certificate["runtime_digest"],
                }
            )
        else:
            if role["binding_kind"] != "MODEL_PACKAGE":
                raise RoleBundleError(f"model role has wrong binding kind: {role_id}")
            package_id = role["package_id"]
            if package_id not in packages:
                raise RoleBundleError(f"model package is absent: {role_id} -> {package_id}")
            if role["qualification_state"] != "UNQUALIFIED":
                raise RoleBundleError(
                    f"model role lacks accepted campaign qualification: {role_id}"
                )
            package = packages[package_id]
            binding["package_id"] = package_id
            checkpoint = _exact_optional_sha(
                package.get("installation", {}).get("artifact_digest")
            )
            environment = package.get("dependency_environment", {})
            environment_sha = _exact_optional_sha(
                environment.get("tree_sha256")
                or environment.get("installed_tree_sha256")
            )
            if checkpoint:
                binding["checkpoint_sha256"] = checkpoint
            if environment_sha:
                binding["environment_sha256"] = environment_sha
        bindings.append(binding)
    return bindings


def execute(output: Path, root: Path = ROOT) -> dict[str, Any]:
    if output.exists():
        raise RoleBundleError(f"output already exists: {output}")
    output.mkdir(parents=True)
    contracts = output / "contracts"
    contracts.mkdir()

    compiler = load_compiler()
    bindings = build_bindings(root)
    child_id = sha256("W64-AQA-REAL-ROLE-BUNDLE-PREFLIGHT-V2")
    child = {
        "contract_id": child_id,
        "operation": "REAL_ROLE_BUNDLE_STATIC_PREFLIGHT",
        "runtime_contact_allowed": False,
        "gpu_allowed": False,
        "promotion_allowed": False,
    }
    child_payload = canonical_bytes(child)
    child_path = contracts / "real_role_bundle_preflight.json"
    child_path.write_bytes(child_payload)

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "ls-tree", "-r", "HEAD"], cwd=root, check=True, capture_output=True
    ).stdout
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    deterministic = next(
        item
        for item in bindings
        if item["role_id"] == "W64-AQA-ROLE-DETERMINISTIC"
    )
    draft = {
        "schema_version": "wave64.aqa.campaign.v2",
        "campaign_name": "w64-aqa-real-role-bundle-static-preflight-v2",
        "campaign_profile": "DEVELOPMENT_CAMPAIGN",
        "qualification_mode": "STATIC_SHADOW",
        "repository": {
            "remote": remote,
            "commit_sha256": sha256(head),
            "tree_sha256": sha256(tree),
        },
        "policy": {
            "policy_id": "W64-AQA-TOOL-POLICY-002",
            "policy_sha256": sha256(
                (root / POLICY_PATH.relative_to(ROOT)).read_bytes()
            ),
            "max_attempts": 1,
            "repair_attempts": 0,
            "abstain_on_unqualified_role": True,
        },
        "jobs": [
            {
                "node_id": "real_role_bundle_static_preflight",
                "contract_path": "contracts/real_role_bundle_preflight.json",
                "contract_sha256": sha256(child_payload),
                "contract_id": child_id,
                "input_sha256": sha256(canonical_bytes(bindings)),
                "runtime_sha256": deterministic["environment_sha256"],
                "prompt_sha256": sha256("no-natural-language-completion-authority"),
                "environment_sha256": deterministic["environment_sha256"],
                "role_id": "W64-AQA-ROLE-DETERMINISTIC",
                "phase": "CPU",
                "stage": "DETERMINISTIC_QA",
                "modality": "CODE",
                "risk_tier": "CRITICAL",
                "residency_group": "cpu",
                "estimated_vram_gib": 0,
                "continue_unrelated_branches": True,
            }
        ],
        "dag": [
            {
                "node_id": "real_role_bundle_static_preflight",
                "depends_on": [],
            }
        ],
        "model_bindings": bindings,
        "bulk_manifest": None,
        "authority": {
            "runpod_may_execute_isolated_batches": True,
            "runpod_may_propose_deltas": True,
            "runpod_may_push_git": False,
            "runpod_may_promote": False,
            "runpod_may_spend": False,
            "runpod_may_override_foreign_lease": False,
            "final_acceptance_authority": "CODEX",
        },
    }
    contract = compiler.compile_contract(draft)
    compiler.verify_sealed_job_bytes(contract, output)
    if contract["admission_disposition"] != "BLOCKED_UNQUALIFIED":
        raise RoleBundleError("real role bundle did not fail closed")

    contract_path = output / "campaign_contract.json"
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    unqualified = [
        item["role_id"]
        for item in bindings
        if item["qualification_state"] != "QUALIFIED"
    ]
    report = {
        "schema_version": "wave64.aqa.real_role_bundle_preflight.v1",
        "status": "PASS_TRUTHFUL_BINDINGS_BLOCKED_UNQUALIFIED",
        "source_commit": head,
        "campaign_id": contract["campaign_id"],
        "contract_sha256": sha256(contract_path.read_bytes()),
        "binding_count": len(bindings),
        "qualified_component_count": len(bindings) - len(unqualified),
        "unqualified_model_role_count": len(unqualified),
        "unqualified_roles": unqualified,
        "runpod_contacted": False,
        "gpu_used": False,
        "model_inference_performed": False,
        "product_authority": False,
        "golden_mask_authority": False,
        "next_action": (
            "QUALIFY_REAL_MODEL_ROLES_INDEPENDENTLY_BEFORE_RUNTIME_CAMPAIGN_ADMISSION"
        ),
    }
    report_path = output / "binding_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"contract": contract, "report": report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = execute(args.output)
    print(json.dumps(packet["report"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
