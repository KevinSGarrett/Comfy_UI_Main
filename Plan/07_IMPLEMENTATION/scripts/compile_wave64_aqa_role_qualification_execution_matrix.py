#!/usr/bin/env python3
"""Expand the frozen corpus into a nine-category plan for every W64-AQA role."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
CORPUS_PATH = Path("Plan/Tracker/Evidence/W64_AQA_ROLE_QUALIFICATION_CORPUS_20260722.json")
ROLE_REGISTRY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_role_qualification_execution_matrix.schema.json")
DEFAULT_OUTPUT = Path("Plan/Tracker/Evidence/W64_AQA_ROLE_QUALIFICATION_EXECUTION_MATRIX_20260722.json")
REQUIRED_CATEGORIES = {"known_good", "known_bad", "borderline", "adversarial", "refusal", "identity", "temporal", "audio_mask", "workflow"}


class MatrixError(ValueError):
    """Raised when role/corpus expansion cannot remain exact and fail closed."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MatrixError(f"JSON root must be an object: {path}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_targets(role: dict[str, Any]) -> list[str]:
    values = []
    for key in ("model", "target_model"):
        if isinstance(role.get(key), str):
            values.append(role[key])
    for key in ("models", "target_models"):
        if isinstance(role.get(key), list):
            values.extend(str(value) for value in role[key])
    return values


def compile_matrix(root: Path, corpus: dict[str, Any] | None = None, roles: dict[str, Any] | None = None) -> dict[str, Any]:
    corpus = deepcopy(corpus if corpus is not None else load_json(root / CORPUS_PATH))
    roles = deepcopy(roles if roles is not None else load_json(root / ROLE_REGISTRY_PATH))
    if corpus.get("status") != "PROSPECTIVE_PRIVATE_CORPUS_FROZEN_RUNTIME_EXECUTION_PENDING":
        raise MatrixError("corpus is not frozen for prospective execution")
    role_records = roles.get("roles")
    if not isinstance(role_records, list) or len(role_records) != 12:
        raise MatrixError("exactly twelve registered roles are required")
    plans = []
    for role in role_records:
        role_id = role["role_id"]
        case_plans = []
        for case in corpus["cases"]:
            in_scope = role_id in case["eligible_roles"]
            case_plans.append({
                "case_id": case["case_id"], "category": case["category"], "partition": case["partition"],
                "source_sha256": case["source"]["sha256"], "truth_evidence_sha256": case["truth_evidence"]["sha256"],
                "task_scope": case["task_scope"] if in_scope else f"refuse out-of-scope request: {case['task_scope']}",
                "in_scope": in_scope,
                "expected_disposition": case["expected_disposition"] if in_scope else "REFUSE",
            })
        if {case["category"] for case in case_plans} != REQUIRED_CATEGORIES:
            raise MatrixError(f"role category coverage incomplete: {role_id}")
        plans.append({
            "role_id": role_id, "kind": role["kind"], "registry_state": role["state"],
            "declared_model_targets": model_targets(role), "cases": case_plans,
            "coverage_complete": True, "operational": False,
        })
    matrix = {
        "schema_version": "wave64.aqa.role_qualification_execution_matrix.v1",
        "program_id": "W64-AQA", "tracker_ids": ["W64-AQA-013", "W64-AQA-014"],
        "status": "EXECUTION_MATRIX_FROZEN_MODEL_IDENTITIES_AND_RUNTIME_RECEIPTS_PENDING",
        "corpus": {"path": CORPUS_PATH.as_posix(), "sha256": sha256_file(root / CORPUS_PATH)},
        "role_registry": {"path": ROLE_REGISTRY_PATH.as_posix(), "sha256": sha256_file(root / ROLE_REGISTRY_PATH)},
        "role_plans": plans,
        "coverage": {"role_count": 12, "categories_per_role": 9, "cases_per_role": 9, "total_role_case_bindings": 108},
        "execution_order": ["admit_exact_model_runtime_and_prompt_identity", "acquire_exact_coordinator_lease", "run_calibration_partition", "freeze_observed_thresholds", "run_held_out_partition_once", "compile_capacity_quality_repeatability_refusal_certificate", "verify_process_exit_cleanup", "release_lease", "retain_evidence_and_keep_activation_false_until_acceptance"],
        "matrix_sha256": "0" * 64,
        "authority": {"execution_planning": True, "model_identity": False, "runtime": False, "quality": False, "independent_juror": False, "golden_mask": False, "activation": False, "promotion": False},
    }
    matrix["matrix_sha256"] = hashlib.sha256(canonical_bytes(matrix)).hexdigest()
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(matrix)
    return matrix


def validate_matrix(root: Path, matrix: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(matrix)
    if matrix != compile_matrix(root):
        raise MatrixError("execution matrix does not replay from current corpus and role registry")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.validate:
        validate_matrix(root, load_json(args.validate))
        print(json.dumps({"status": "PASS", "matrix": str(args.validate)}))
        return 0
    matrix = compile_matrix(root)
    output = args.output or root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
