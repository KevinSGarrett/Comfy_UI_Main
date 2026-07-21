#!/usr/bin/env python3
"""Validate the additive W64-AQA project-control package."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PROGRAM = "W64-AQA"
EXPECTED_IDS = {f"W64-AQA-{number:03d}" for number in range(1, 17)}

PATHS = {
    "master": ROOT
    / "Plan/00_PROJECT_CONTROL/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_AND_CORRECTION_MASTER_PLAN.md",
    "architecture": ROOT
    / "Plan/02_TARGET_ARCHITECTURE/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_CONTROL_PLANE_ARCHITECTURE.md",
    "items": ROOT
    / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv",
    "tracker": ROOT
    / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv",
    "requirements": ROOT
    / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_REQUIREMENTS.json",
    "evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_EXTERNAL_STATE_RECONCILIATION_20260721.json",
    "operations": ROOT
    / "Plan/Instructions/Operations/RUNPOD_AUTONOMOUS_MULTIMODAL_QA_OPERATING_PROTOCOL.md",
    "qa": ROOT
    / "Plan/Instructions/QA/RUNPOD_AUTONOMOUS_MULTIMODAL_QA_AND_BOUNDED_CORRECTION_PROTOCOL.md",
    "registry": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json",
    "schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_qa_decision.schema.json",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "runpod_bearer": re.compile(r"(?i)bearer\s+[A-Za-z0-9_-]{24,}"),
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def collect_errors() -> list[str]:
    errors: list[str] = []
    missing = [str(path.relative_to(ROOT)) for path in PATHS.values() if not path.is_file()]
    if missing:
        return [f"missing required file: {path}" for path in missing]

    try:
        items = load_csv(PATHS["items"])
        tracker = load_csv(PATHS["tracker"])
        requirements = load_json(PATHS["requirements"])
        evidence = load_json(PATHS["evidence"])
        registry = load_json(PATHS["registry"])
        schema = load_json(PATHS["schema"])
    except (csv.Error, json.JSONDecodeError, OSError) as exc:
        return [f"parse failure: {exc}"]

    item_ids = {row.get("Item_ID", "") for row in items}
    tracker_ids = {row.get("Tracker_ID", "") for row in tracker}
    requirement_ids = {entry.get("id", "") for entry in requirements.get("requirements", [])}
    for label, observed in (
        ("items", item_ids),
        ("tracker", tracker_ids),
        ("requirements", requirement_ids),
    ):
        if observed != EXPECTED_IDS:
            errors.append(
                f"{label} ID parity failure: missing={sorted(EXPECTED_IDS - observed)} "
                f"extra={sorted(observed - EXPECTED_IDS)}"
            )

    if {row.get("Item_ID") for row in tracker} != EXPECTED_IDS:
        errors.append("tracker Item_ID references do not match the W64-AQA item set")

    json_docs = (requirements, evidence, registry)
    for document in json_docs:
        if document.get("program_id") != PROGRAM:
            errors.append("JSON document has the wrong program_id")

    runtime = registry.get("runtime_policy", {})
    expected_limits = {
        "max_repair_attempts_per_defect": 2,
        "max_total_generation_attempts": 4,
        "max_no_progress_cycles": 2,
    }
    for key, expected in expected_limits.items():
        if runtime.get(key) != expected:
            errors.append(f"registry {key} must equal {expected}")
    if runtime.get("generation_host") != "runpod_only":
        errors.append("registry must bind generation_host to runpod_only")
    if runtime.get("ec2_forbidden") is not True:
        errors.append("registry must explicitly forbid EC2")
    if runtime.get("phase_safe_exclusive_gpu") is not True:
        errors.append("registry must require phase-safe exclusive GPU use")

    roles = {entry.get("role_id"): entry for entry in registry.get("roles", [])}
    required_roles = {
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-STRICT-VISUAL",
        "W64-AQA-ROLE-FAST-TRIAGE",
        "W64-AQA-ROLE-TEXT-PLANNER",
        "W64-AQA-ROLE-INDEPENDENT-JUROR",
        "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "W64-AQA-ROLE-WORKFLOW-ENGINEER",
        "W64-AQA-ROLE-GOLDEN-MASK",
        "W64-AQA-ROLE-MULTIGPU-ARBITER",
    }
    if not required_roles.issubset(roles):
        errors.append(f"missing roles: {sorted(required_roles - roles.keys())}")

    strict = roles.get("W64-AQA-ROLE-STRICT-VISUAL", {})
    if strict.get("model") != "qwen2.5vl:32b":
        errors.append("current strict visual role must bind qwen2.5vl:32b")
    if strict.get("product_approval_sufficient") is not False:
        errors.append("strict reviewer alone must not be sufficient for approval")

    triage = roles.get("W64-AQA-ROLE-FAST-TRIAGE", {})
    if triage.get("product_approval_sufficient") is not False:
        errors.append("triage role must not have product approval authority")
    if "PASS_PRODUCT" not in triage.get("forbidden_decisions", []):
        errors.append("triage role must explicitly forbid PASS_PRODUCT")

    arbiter = roles.get("W64-AQA-ROLE-MULTIGPU-ARBITER", {})
    if arbiter.get("current_48gb_pod_eligible") is not False:
        errors.append("multi-GPU arbiter must be ineligible on the current 48 GB pod")

    workflow = roles.get("W64-AQA-ROLE-WORKFLOW-ENGINEER", {})
    if workflow.get("proposal_only") is not True:
        errors.append("workflow engineer must be proposal-only")

    modalities = set(schema.get("properties", {}).get("modality", {}).get("enum", []))
    required_modalities = {"image", "video", "audio", "av", "mask", "workflow"}
    if modalities != required_modalities:
        errors.append("decision schema modality coverage is incomplete")

    all_text = "\n".join(path.read_text(encoding="utf-8") for path in PATHS.values())
    required_phrases = (
        "Qwen3-Coder-Next",
        "Qwen3-Omni",
        "Qwen3.5-397B",
        "InternVL",
        "golden-mask",
        "MaskFactory",
        "workflow",
        "two repair attempts",
        "four total generation attempts",
        "two no-progress",
        "EC2",
        "RunPod",
    )
    lowered = all_text.lower()
    for phrase in required_phrases:
        if phrase.lower() not in lowered:
            errors.append(f"required cross-surface concept missing: {phrase}")

    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(all_text):
            errors.append(f"possible secret literal detected: {name}")

    try:
        import jsonschema

        jsonschema.Draft7Validator.check_schema(schema)
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover - library supplies exact detail
        errors.append(f"decision schema invalid: {exc}")

    return errors


def main() -> int:
    errors = collect_errors()
    result = {
        "status": "PASS" if not errors else "FAIL",
        "classification": (
            "W64_AQA_CONTROL_PACKAGE_VALID" if not errors else "W64_AQA_CONTROL_PACKAGE_INVALID"
        ),
        "program_id": PROGRAM,
        "validated_files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in PATHS.values()],
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
