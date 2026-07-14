#!/usr/bin/env python3
"""Reconcile existing FLUX.1-dev runtime proof without repeating generation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


CANONICAL_WORKFLOW = Path(
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/"
    "flux1_dev_primary_base/workflow.api.json"
)
RUNTIME_WORKFLOW = Path("Workflows/base_generation/flux1_dev_primary_base/workflow.api.json")
RUNTIME_REQUIREMENTS = Path(
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/"
    "flux1_dev_primary_base/runtime_requirements.json"
)
SMOKE_REQUEST = Path(
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/"
    "flux1_dev_primary_base/smoke_test_request.json"
)
EXTERNAL_PREFLIGHT = Path(
    "Plan/Instructions/QA/Evidence/Runtime_Readiness/"
    "W66_FLUX1_DEV_EXISTING_EXTERNAL_MODEL_PREFLIGHT_20260713T010244-0500.json"
)
PASS_A_WORKFLOW = Path(
    "workflows/base_generation/character1_flux_calibration_front/workflow.passA.api.json"
)
PASS_A_OUTPUT = Path("assets/outputs/flux_base/front_passA_00001_.png")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def node_classes(workflow: dict[str, Any]) -> set[str]:
    return {
        node["class_type"]
        for node in workflow.values()
        if isinstance(node, dict) and isinstance(node.get("class_type"), str)
    }


def require_one(rows: list[dict[str, str]], field: str, value: str) -> dict[str, str]:
    matches = [row for row in rows if row.get(field, "").replace("\\", "/") == value]
    if len(matches) != 1:
        raise ValueError(f"expected one {field}={value!r}, found {len(matches)}")
    return matches[0]


def runtime_probe(runtime_url: str, required_classes: set[str]) -> dict[str, Any]:
    base = runtime_url.rstrip("/")
    with urllib.request.urlopen(f"{base}/system_stats", timeout=5) as response:
        stats = json.load(response)
    with urllib.request.urlopen(f"{base}/queue", timeout=5) as response:
        queue = json.load(response)
    with urllib.request.urlopen(f"{base}/object_info", timeout=10) as response:
        object_info = json.load(response)
    missing = sorted(required_classes - set(object_info))
    return {
        "url": base,
        "reachable": True,
        "comfyui_version": stats.get("system", {}).get("comfyui_version"),
        "device_count": len(stats.get("devices", [])),
        "required_node_class_count": len(required_classes),
        "missing_node_classes": missing,
        "queue_running_count": len(queue.get("queue_running", [])),
        "queue_pending_count": len(queue.get("queue_pending", [])),
        "generation_submitted": False,
        "pass": not missing and not queue.get("queue_running") and not queue.get("queue_pending"),
    }


def build_evidence(args: argparse.Namespace) -> dict[str, Any]:
    root = args.project_root.resolve()
    package = args.package_root.resolve()
    canonical_path = root / CANONICAL_WORKFLOW
    runtime_path = root / RUNTIME_WORKFLOW
    requirements_path = root / RUNTIME_REQUIREMENTS
    smoke_path = root / SMOKE_REQUEST
    preflight_path = root / EXTERNAL_PREFLIGHT
    pass_a_path = package / PASS_A_WORKFLOW
    pass_a_output_path = package / PASS_A_OUTPUT

    canonical = load_json(canonical_path)
    runtime_workflow = load_json(runtime_path)
    requirements = load_json(requirements_path)
    smoke = load_json(smoke_path)
    preflight = load_json(preflight_path)
    pass_a = load_json(pass_a_path)
    model_manifest = load_json(package / "manifests/model_requirements.json")
    workflow_inventory = csv_rows(package / "manifests/workflow_inventory.csv")
    generated_inventory = csv_rows(package / "manifests/generated_image_inventory.csv")
    file_manifest = csv_rows(package / "manifests/file_manifest.csv")

    canonical_hash = sha256(canonical_path)
    runtime_hash = sha256(runtime_path)
    pass_a_hash = sha256(pass_a_path)
    canonical_classes = node_classes(canonical)
    pass_a_classes = node_classes(pass_a)
    required_classes = set(requirements["required_nodes"])
    missing_from_canonical = sorted(required_classes - canonical_classes)
    missing_from_pass_a = sorted(required_classes - pass_a_classes)

    workflow_record = require_one(
        workflow_inventory, "relative_path", PASS_A_WORKFLOW.as_posix()
    )
    output_record = require_one(
        generated_inventory, "relative_path", PASS_A_OUTPUT.as_posix()
    )
    output_manifest_record = require_one(
        file_manifest, "relative_path", PASS_A_OUTPUT.as_posix()
    )
    output_hash = sha256(pass_a_output_path)
    output_bytes = pass_a_output_path.stat().st_size
    output_verified = (
        output_record["sha256"].upper() == output_hash
        and output_manifest_record["sha256"].upper() == output_hash
        and int(output_record["bytes"]) == output_bytes
        and int(output_manifest_record["bytes"]) == output_bytes
    )

    expected_model = requirements["required_models"][0]
    package_models = [
        model
        for model in model_manifest["models"]
        if model["name"] == expected_model["filename"]
    ]
    if len(package_models) != 1:
        raise ValueError("FLUX.1-dev package model record is missing or duplicated")
    package_model = package_models[0]
    preflight_models = [
        model
        for model in preflight["local_required_models"]
        if model["filename"] == expected_model["filename"]
    ]
    if len(preflight_models) != 1:
        raise ValueError("FLUX.1-dev preflight model record is missing or duplicated")
    preflight_model = preflight_models[0]
    expected_hash = expected_model["sha256"].upper()
    model_authority_agrees = (
        package_model["installed"] is True
        and package_model["sha256"].upper() == expected_hash
        and package_model["bytes"] == expected_model["bytes"]
        and preflight_model["exists_locally"] is True
        and preflight_model["hash_match"] is True
        and preflight_model["observed_sha256"].upper() == expected_hash
    )

    canonical_hash_in_package = any(
        row.get("sha256", "").upper() == canonical_hash for row in workflow_inventory
    )
    live = runtime_probe(args.runtime_url, required_classes)
    structural_pass = (
        canonical_hash == runtime_hash
        and canonical == runtime_workflow
        and not missing_from_canonical
        and not missing_from_pass_a
        and workflow_record["sha256"].upper() == pass_a_hash
        and workflow_record["json_valid"].lower() == "true"
        and output_verified
        and model_authority_agrees
        and live["pass"]
    )
    license_accepted = False
    canonical_lane_certified = False
    stamp = args.timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"FLUX1-EXISTING-RUNTIME-PROOF-RECONCILIATION-{stamp}",
        "timestamp": args.timestamp,
        "lane_id": "flux1_dev_primary_base",
        "queue_id": "MRQ-W64-100",
        "result": "existing_capability_proven_canonical_lane_and_license_blocked",
        "classifications": [
            "FLUX1_EXISTING_EXTERNAL_MODEL_REUSED",
            "FLUX1_MODEL_LOAD_AND_OUTPUT_CAPABILITY_PROVEN",
            "NO_DUPLICATE_MODEL_DOWNLOAD_REQUIRED",
            "NO_DUPLICATE_CAPABILITY_GENERATION_REQUIRED",
            "BLOCKED_CANONICAL_LANE_RUNTIME_PROOF_MISSING",
            "BLOCKED_FLUX1_DEV_LICENSE_ACCEPTANCE_MISSING",
        ],
        "canonical_contract": {
            "template_path": CANONICAL_WORKFLOW.as_posix(),
            "runtime_mirror_path": RUNTIME_WORKFLOW.as_posix(),
            "template_sha256": canonical_hash,
            "runtime_mirror_sha256": runtime_hash,
            "byte_identical": canonical_hash == runtime_hash,
            "required_node_classes": sorted(required_classes),
            "missing_from_canonical": missing_from_canonical,
            "smoke_request_path": SMOKE_REQUEST.as_posix(),
            "smoke_request_sha256": sha256(smoke_path),
            "exact_canonical_hash_found_in_handoff_workflows": canonical_hash_in_package,
            "exact_canonical_workflow_executed": False,
            "canonical_lane_certified": canonical_lane_certified,
        },
        "existing_runtime_proof": {
            "workflow_path": PASS_A_WORKFLOW.as_posix(),
            "workflow_sha256": pass_a_hash,
            "workflow_inventory_sha256": workflow_record["sha256"].upper(),
            "extra_node_classes": sorted(pass_a_classes - required_classes),
            "missing_required_node_classes": missing_from_pass_a,
            "output": {
                "path": PASS_A_OUTPUT.as_posix(),
                "sha256": output_hash,
                "bytes": output_bytes,
                "generated_inventory_match": output_record["sha256"].upper() == output_hash,
                "file_manifest_match": output_manifest_record["sha256"].upper() == output_hash,
                "verified": output_verified,
            },
            "model_load_and_image_output_capability_proven": structural_pass,
            "proof_scope": "byte_distinct_character_calibration_workflow_not_canonical_lane",
        },
        "model_authority": {
            "filename": expected_model["filename"],
            "expected_sha256": expected_hash,
            "expected_bytes": expected_model["bytes"],
            "existing_path": preflight_model["existing_path"],
            "preflight_observed_sha256": preflight_model["observed_sha256"].upper(),
            "package_recorded_sha256": package_model["sha256"].upper(),
            "authority_records_agree": model_authority_agrees,
            "fresh_multi_gib_model_rehash_performed": False,
            "download_required": False,
        },
        "live_runtime": live,
        "license": {
            "license_id": requirements["licensed_source"]["license_id"],
            "non_commercial_boundary": requirements["licensed_source"]["license_boundary"],
            "acceptance_proven": license_accepted,
            "commercial_use_authorized": False,
        },
        "decision": {
            "structural_reconciliation_pass": structural_pass,
            "duplicate_capability_generation_required": False,
            "exact_canonical_run_required_only_for_canonical_lane_certification": True,
            "canonical_execution_allowed_before_license_acceptance": False,
            "queue_file_mutated": False,
            "recommended_queue_classification": (
                "existing_runtime_capability_reconciled_canonical_lane_and_license_blocked"
            ),
        },
        "worker_assistance": {
            "accepted_as_authority": False,
            "reason": (
                "Two Cursor mapping attempts returned useful substantive conclusions but "
                "failed the wrapper output contract; deterministic reconciliation is authority."
            ),
        },
        "process_exit_contract": {
            "0": "canonical lane and license requirements passed",
            "1": "structural reconciliation failed",
            "2": "existing capability reconciled but canonical lane or license remains blocked",
            "current_exit_code": 2 if structural_pass else 1,
        },
        "boundaries": [
            "No model was downloaded, copied, or reinstalled.",
            "No prompt was submitted and no existing FLUX generation was repeated.",
            "The dirty model runtime queue was not changed or staged.",
            "No AWS, EC2, S3, Jira, mask promotion, Wave70 hard-gate, or Wave71+ action occurred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--package-root", type=Path, default=Path("ztest"))
    parser.add_argument("--runtime-url", default="http://127.0.0.1:8188")
    parser.add_argument(
        "--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds")
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    evidence = build_evidence(args)
    payload = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if not evidence["decision"]["structural_reconciliation_pass"]:
        return 1
    return 0 if evidence["canonical_contract"]["canonical_lane_certified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
