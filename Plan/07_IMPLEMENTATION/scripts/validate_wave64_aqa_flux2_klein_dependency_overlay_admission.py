#!/usr/bin/env python3
"""Validate the non-mutating FLUX.2 Klein dependency-overlay admission."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
ADMISSION_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_flux2_klein_dependency_overlay_admission.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_dependency_overlay_admission.schema.json")


class OverlayAdmissionError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OverlayAdmissionError(f"JSON root must be an object: {path}")
    return value


def admission_id(value: dict[str, Any]) -> str:
    candidate = json.loads(json.dumps(value))
    candidate["admission_id"] = "0" * 64
    raw = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_admission(root: Path, value: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["admission_id"] != admission_id(value):
        raise OverlayAdmissionError("overlay admission identity drift")
    live = value["live_service"]
    if live["installed"]["transformers"] != "4.46.3" or live["required"]["transformers"] != ">=4.50.3":
        raise OverlayAdmissionError("live Transformers mismatch evidence drift")
    expected = [
        ("transformers", "4.50.3", "6111610a43dec24ef32c3df0632c6b25b07d9711c01d9e1077bdd2ff6b14a38c"),
        ("tokenizers", "0.21.4", "51b7eabb104f46c1c50b486520555715457ae833d5aee9ff6ae853d1130506ff"),
    ]
    observed = [(p["name"], p["version"], p["sha256"]) for p in value["overlay"]["packages"]]
    if observed != expected or value["resolver_probe"]["install_count"] != 2:
        raise OverlayAdmissionError("exact dry-run resolution drift")
    if not value["overlay"]["root"].startswith("/workspace/w64_aqa/environments/flux2-klein/"):
        raise OverlayAdmissionError("overlay escaped transaction-owned root")
    receipt = value["overlay"]["build_receipt"]
    if (
        receipt["file_count"] != 3604
        or receipt["total_bytes"] != 105881854
        or receipt["tree_manifest_sha256"] != "b383ddd0b640b1824f79d6736a0fe90cf65f9cc7d2aecb8ac5cc3f25d89bff38"
        or not all(receipt[key] for key in ("qwen2_tokenizer_import", "flux_encoder_import", "cpu_mode"))
        or receipt["gpu_visible"]
    ):
        raise OverlayAdmissionError("overlay build receipt drift")
    forbidden = ("live_service_mutation", "model_load", "runtime", "quality", "activation", "promotion")
    if any(value["authority"][key] for key in forbidden):
        raise OverlayAdmissionError("unsupported overlay or runtime authority")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--admission", type=Path, default=ADMISSION_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.admission if args.admission.is_absolute() else root / args.admission
    value = load_json(path)
    validate_admission(root, value)
    print(json.dumps({"status": "PASS", "admission_id": value["admission_id"], "overlay_built": True, "dependency_import_compatibility": True, "live_service_mutation": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
