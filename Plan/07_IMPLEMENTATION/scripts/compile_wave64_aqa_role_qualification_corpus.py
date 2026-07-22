#!/usr/bin/env python3
"""Freeze the exact retained W64-AQA role-qualification corpus without runtime claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_role_qualification_corpus_source_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_role_qualification_corpus_manifest.schema.json")
ROLE_REGISTRY_PATH = Path("Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json")
DEFAULT_OUTPUT = Path("Plan/Tracker/Evidence/W64_AQA_ROLE_QUALIFICATION_CORPUS_20260722.json")
REQUIRED_CATEGORIES = {"known_good", "known_bad", "borderline", "adversarial", "refusal", "identity", "temporal", "audio_mask", "workflow"}


class CorpusError(ValueError):
    """Raised when a corpus source or binding is unsafe or incomplete."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CorpusError(f"JSON root must be an object: {path}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_binding(root: Path, relative: str) -> dict[str, Any]:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CorpusError(f"path escapes project root: {relative}") from exc
    if not candidate.is_file():
        raise CorpusError(f"bound file is absent: {relative}")
    return {"path": relative.replace("\\", "/"), "sha256": sha256_file(candidate), "bytes": candidate.stat().st_size}


def compile_manifest(root: Path, source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = deepcopy(source if source is not None else load_json(root / SOURCE_PATH))
    cases = source.get("cases")
    if not isinstance(cases, list) or len(cases) != 9:
        raise CorpusError("exactly nine prospectively declared cases are required")
    categories = {case.get("category") for case in cases}
    if categories != REQUIRED_CATEGORIES:
        raise CorpusError("required category coverage is incomplete")
    case_ids = [case.get("case_id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise CorpusError("case identifiers must be unique")
    role_payload = load_json(root / ROLE_REGISTRY_PATH)
    known_roles = {role["role_id"] for role in role_payload["roles"]}
    compiled = []
    for case in cases:
        roles = case.get("eligible_roles")
        if not isinstance(roles, list) or not roles or not set(roles) <= known_roles:
            raise CorpusError(f"unknown or empty eligible role set: {case.get('case_id')}")
        if case.get("expected_disposition") not in {"PASS", "FAIL", "REFUSE"}:
            raise CorpusError(f"invalid expected disposition: {case.get('case_id')}")
        compiled.append({
            "case_id": case["case_id"], "category": case["category"],
            "partition": case["partition"], "modality": case["modality"],
            "source": safe_binding(root, case["source_path"]),
            "truth_evidence": safe_binding(root, case["truth_evidence_path"]),
            "task_scope": case["task_scope"], "expected_disposition": case["expected_disposition"],
            "eligible_roles": roles,
        })
    calibration = sum(case["partition"] == "calibration" for case in compiled)
    held_out = sum(case["partition"] == "held_out" for case in compiled)
    if calibration < 4 or held_out < 4:
        raise CorpusError("calibration and held-out partitions must each contain at least four cases")
    manifest = {
        "schema_version": "wave64.aqa.role_qualification_corpus_manifest.v1",
        "program_id": "W64-AQA", "tracker_ids": ["W64-AQA-013"],
        "status": "PROSPECTIVE_PRIVATE_CORPUS_FROZEN_RUNTIME_EXECUTION_PENDING",
        "source_registry": safe_binding(root, SOURCE_PATH.as_posix()), "cases": compiled,
        "coverage": {"categories": sorted(categories), "modalities": sorted({case["modality"] for case in compiled}), "calibration_count": calibration, "held_out_count": held_out},
        "corpus_sha256": "0" * 64,
        "authority": {"source_admission": True, "runtime_qualification": False, "quality_qualification": False, "independent_juror": False, "golden_mask": False, "operational_activation": False, "product_promotion": False},
    }
    manifest["corpus_sha256"] = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(manifest)
    return manifest


def validate_manifest(root: Path, manifest: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(manifest)
    expected = compile_manifest(root)
    if manifest != expected:
        raise CorpusError("manifest does not replay from current exact sources")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.validate:
        validate_manifest(root, load_json(args.validate))
        print(json.dumps({"status": "PASS", "manifest": str(args.validate)}))
        return 0
    manifest = compile_manifest(root)
    output = args.output or root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
