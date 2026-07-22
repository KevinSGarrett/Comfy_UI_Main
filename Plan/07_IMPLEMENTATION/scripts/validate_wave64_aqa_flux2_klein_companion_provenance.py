#!/usr/bin/env python3
"""Validate the fail-closed FLUX.2 Klein companion provenance decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
DECISION_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_flux2_klein_companion_provenance_decision.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_companion_provenance_decision.schema.json")


class CompanionProvenanceError(ValueError):
    """Raised when provenance facts drift or unsupported authority appears."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CompanionProvenanceError(f"JSON root must be an object: {path}")
    return value


def content_id(value: dict[str, Any]) -> str:
    candidate = json.loads(json.dumps(value))
    candidate["decision_id"] = "0" * 64
    payload = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_decision(root: Path, value: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["decision_id"] != content_id(value):
        raise CompanionProvenanceError("companion provenance decision identity drift")
    selected = value["selected_companions"]
    if [item["role"] for item in selected] != ["text_encoder", "vae"]:
        raise CompanionProvenanceError("selected companion order drift")
    expected = [
        ("text_encoder", 8044982048, "6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a"),
        ("vae", 336211292, "868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3"),
    ]
    if [(item["role"], item["bytes"], item["sha256"]) for item in selected] != expected:
        raise CompanionProvenanceError("selected companion identity drift")
    upstream = value["upstream_family"]
    if upstream["text_encoder_distribution"]["total_file_bytes"] == selected[0]["bytes"]:
        raise CompanionProvenanceError("text encoder distributions were falsely marked byte-equal")
    if upstream["vae_distribution"]["total_file_bytes"] == selected[1]["bytes"]:
        raise CompanionProvenanceError("VAE distributions were falsely marked byte-equal")
    if value["byte_equivalence"]["text_encoder"] or value["byte_equivalence"]["vae"]:
        raise CompanionProvenanceError("byte equivalence gained without exact proof")
    forbidden = ("exact_companion_redistribution", "project_license_acceptance", "acquisition", "storage_mutation", "runtime", "activation", "promotion")
    if any(value["authority"][key] for key in forbidden):
        raise CompanionProvenanceError("unsupported companion provenance authority")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--decision", type=Path, default=DECISION_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.decision if args.decision.is_absolute() else root / args.decision
    value = load_json(path)
    validate_decision(root, value)
    print(json.dumps({"status": "PASS", "decision_id": value["decision_id"], "decision": value["decision"], "exact_companion_redistribution": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
