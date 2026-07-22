#!/usr/bin/env python3
"""Validate exact FLUX.2 Klein component identities without activating runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
BUNDLE_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_flux2_klein_4b_dependency_bundle.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_dependency_bundle.schema.json")
PROVENANCE_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_companion_provenance_decision.schema.json")
WORKFLOW_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_workflow_contract.schema.json")


class DependencyBundleError(ValueError):
    """Raised when component identity, source binding, or authority drifts."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DependencyBundleError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_id(value: dict[str, Any]) -> str:
    candidate = json.loads(json.dumps(value))
    candidate["bundle_id"] = "0" * 64
    payload = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_bundle(root: Path, value: dict[str, Any], verify_local_bytes: bool = False) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["bundle_id"] != bundle_id(value):
        raise DependencyBundleError("dependency bundle identity drift")
    if [item["role"] for item in value["components"]] != ["diffusion_model", "text_encoder", "vae"]:
        raise DependencyBundleError("dependency component order drift")
    raw_vae = value["components"][2]
    if raw_vae["local_source"]["sha256"] == raw_vae["sha256"] or raw_vae["local_source"]["bytes"] == raw_vae["bytes"]:
        raise DependencyBundleError("Dev VAE must not be accepted as the Klein companion")
    expected = [
        ("diffusion_model", "flux-2-klein-4b-fp8.safetensors", 4070624520, "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6"),
        ("text_encoder", "qwen_3_4b.safetensors", 8044982048, "6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a"),
        ("vae", "flux2-vae.safetensors", 336211292, "868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3"),
    ]
    observed = [(item["role"], item["filename"], item["bytes"], item["sha256"]) for item in value["components"]]
    if observed != expected:
        raise DependencyBundleError("exact Klein component identity drift")
    diffusion, text_encoder, vae = value["components"]
    if diffusion["current_pod_state"] != "PROMOTED_HASH_VERIFIED":
        raise DependencyBundleError("diffusion model must remain the sole promoted component")
    if any(item["current_pod_state"] != "NOT_IN_ACCEPTED_PROMOTED_LEDGER" for item in (text_encoder, vae)):
        raise DependencyBundleError("companion promotion state drift")
    expected_license_states = [
        "APACHE_2_EXACT_PROVIDER_METADATA_PROJECT_ACCEPTANCE_PENDING",
        "UPSTREAM_FAMILY_APACHE_2_EXACT_ARTIFACT_REDISTRIBUTION_DECLARATION_MISSING",
        "UPSTREAM_FAMILY_APACHE_2_EXACT_ARTIFACT_REDISTRIBUTION_DECLARATION_MISSING",
    ]
    if [item["license_state"] for item in value["components"]] != expected_license_states:
        raise DependencyBundleError("component license state drift")
    provenance_binding = value["provenance_decision"]
    provenance_path = root / Path(provenance_binding["path"])
    if sha256_file(provenance_path) != provenance_binding["sha256"]:
        raise DependencyBundleError("companion provenance decision hash drift")
    provenance = load_json(provenance_path)
    Draft202012Validator(load_json(root / PROVENANCE_SCHEMA_PATH)).validate(provenance)
    if (
        provenance.get("decision_id") != provenance_binding["decision_id"]
        or provenance.get("decision") != provenance_binding["decision"]
        or provenance.get("authority", {}).get("exact_companion_redistribution") is not False
    ):
        raise DependencyBundleError("companion provenance decision authority drift")
    workflow_binding = value["workflow_contract"]
    workflow_path = root / Path(workflow_binding["path"])
    if sha256_file(workflow_path) != workflow_binding["sha256"]:
        raise DependencyBundleError("workflow contract hash drift")
    workflow_contract = load_json(workflow_path)
    Draft202012Validator(load_json(root / WORKFLOW_SCHEMA_PATH)).validate(workflow_contract)
    candidate_path = root / Path(workflow_binding["candidate_path"])
    if (
        workflow_contract.get("contract_id") != workflow_binding["contract_id"]
        or workflow_contract.get("selected_api_candidate", {}).get("sha256") != workflow_binding["candidate_sha256"]
        or sha256_file(candidate_path) != workflow_binding["candidate_sha256"]
        or workflow_contract.get("authority", {}).get("static_workflow_contract") is not True
        or workflow_contract.get("authority", {}).get("runtime_smoke") is not False
    ):
        raise DependencyBundleError("workflow contract identity or authority drift")
    for component in value["components"]:
        source = component.get("local_source")
        if source and source.get("evidence"):
            if sha256_file(root / Path(source["evidence"])) != source["evidence_sha256"]:
                raise DependencyBundleError(f"component evidence hash drift: {component['role']}")
        if verify_local_bytes and source:
            source_path = Path(source["path"])
            if source_path.stat().st_size != source["bytes"] or sha256_file(source_path) != source["sha256"]:
                raise DependencyBundleError(f"local source byte drift: {component['role']}")
    for binding in value["comfyui_runtime"]["source_bindings"]:
        if sha256_file(root / Path(binding["path"])) != binding["sha256"]:
            raise DependencyBundleError(f"ComfyUI source hash drift: {binding['path']}")
    if any(value["authority"][key] for key in ("current_pod_complete", "license_acceptance", "workflow", "object_info", "model_load", "capacity", "quality", "activation", "promotion")):
        raise DependencyBundleError("unsupported dependency bundle authority")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path, default=BUNDLE_PATH)
    parser.add_argument("--verify-local-bytes", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.bundle if args.bundle.is_absolute() else root / args.bundle
    value = load_json(path)
    validate_bundle(root, value, verify_local_bytes=args.verify_local_bytes)
    print(json.dumps({"status": "PASS", "bundle_id": value["bundle_id"], "current_pod_complete": value["authority"]["current_pod_complete"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
