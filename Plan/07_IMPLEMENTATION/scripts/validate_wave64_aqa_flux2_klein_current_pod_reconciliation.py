#!/usr/bin/env python3
"""Validate the read-only current-pod FLUX.2 Klein reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
RECONCILIATION_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_flux2_klein_current_pod_reconciliation.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_current_pod_reconciliation.schema.json")


class CurrentPodReconciliationError(ValueError):
    """Raised when current-pod facts drift or unsupported authority appears."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CurrentPodReconciliationError(f"JSON root must be an object: {path}")
    return value


def reconciliation_id(value: dict[str, Any]) -> str:
    candidate = json.loads(json.dumps(value))
    candidate["reconciliation_id"] = "0" * 64
    payload = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_reconciliation(root: Path, value: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["reconciliation_id"] != reconciliation_id(value):
        raise CurrentPodReconciliationError("current-pod reconciliation identity drift")
    expected_components = [
        ("diffusion_model", 4070624520, "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6"),
        ("text_encoder", 8044982048, "6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a"),
        ("vae", 336211292, "868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3"),
    ]
    observed_expected = [
        (item["role"], item["expected"]["bytes"], item["expected"]["sha256"])
        for item in value["components"]
    ]
    if observed_expected != expected_components:
        raise CurrentPodReconciliationError("planned component identity drift")
    diffusion, text_encoder, vae = value["components"]
    for component in (diffusion, text_encoder):
        if not component["match"] or component["expected"] != component["observed"]:
            raise CurrentPodReconciliationError(f"exact current-pod identity lost: {component['role']}")
    if vae["match"] or vae["expected"] == vae["observed"]:
        raise CurrentPodReconciliationError("wrong VAE variant was accepted as exact Klein identity")
    if vae["observed"] != {
        "bytes": 336213556,
        "sha256": "d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5",
    }:
        raise CurrentPodReconciliationError("observed Dev VAE identity drift")
    expected_nodes = sorted([
        "UNETLoader", "CLIPLoader", "VAELoader", "CLIPTextEncode",
        "ConditioningZeroOut", "EmptyFlux2LatentImage", "RandomNoise",
        "CFGGuider", "KSamplerSelect", "Flux2Scheduler",
        "SamplerCustomAdvanced", "VAEDecode", "SaveImage",
    ])
    if value["object_info"]["required_nodes"] != expected_nodes:
        raise CurrentPodReconciliationError("required object-info node order drift")
    expected_versions = {
        "torch": "2.4.1+cu124", "transformers": "4.46.3",
        "tokenizers": "0.20.3", "safetensors": "0.8.0",
        "comfyui-workflow-templates": "0.11.12",
        "comfyui-frontend-package": "1.45.21",
    }
    if value["runtime_environment"]["versions"] != expected_versions:
        raise CurrentPodReconciliationError("observed dependency version drift")
    forbidden = (
        "exact_klein_vae_identity", "dependency_compatibility", "license_acceptance",
        "storage_mutation", "model_load", "runtime", "capacity", "quality", "activation", "promotion",
    )
    if any(value["authority"][key] for key in forbidden):
        raise CurrentPodReconciliationError("unsupported FLUX.2 execution authority")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reconciliation", type=Path, default=RECONCILIATION_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.reconciliation if args.reconciliation.is_absolute() else root / args.reconciliation
    value = load_json(path)
    validate_reconciliation(root, value)
    print(json.dumps({
        "status": "PASS",
        "reconciliation_id": value["reconciliation_id"],
        "current_pod_object_info": True,
        "exact_klein_vae_identity": False,
        "runtime": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
