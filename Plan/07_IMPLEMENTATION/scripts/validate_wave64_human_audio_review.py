#!/usr/bin/env python3
"""Validate a human listening record and emit strict hash-bound playback proof."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_human_audio_review_request.schema.json"
RECORD_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_human_audio_review_record.schema.json"
PROOF_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_human_playback_review_proof.schema.json"
AUTHORITY_REGISTRY = PROJECT_ROOT / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_valid(path: Path, schema_path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload))
    if errors:
        location = ".".join(str(part) for part in errors[0].path)
        raise ValueError(f"schema validation failed at {location}: {errors[0].message}")
    return payload


def _verify_binding(binding: dict[str, Any]) -> None:
    path = Path(binding["path"]).resolve()
    if not path.is_file():
        raise ValueError(f"bound artifact missing: {path}")
    if path.stat().st_size != binding["bytes"]:
        raise ValueError(f"bound artifact byte mismatch: {path}")
    if _sha256(path) != binding["sha256"]:
        raise ValueError(f"bound artifact hash mismatch: {path}")


def validate_review(request_path: Path, record_path: Path) -> dict[str, Any]:
    request = _load_valid(request_path, REQUEST_SCHEMA)
    record = _load_valid(record_path, RECORD_SCHEMA)
    if record["review_id"] != request["review_id"]:
        raise ValueError("review_id mismatch")
    if record["request_sha256"] != _sha256(request_path):
        raise ValueError("request_sha256 mismatch")
    _verify_binding(request["artifact_binding"])
    for binding in request["automated_evidence_bindings"]:
        _verify_binding(binding)

    registry = json.loads(AUTHORITY_REGISTRY.read_text(encoding="utf-8"))
    identity = record["reviewer_identity"]
    allowed = registry.get("human_playback_review_authorities", [])
    if identity not in allowed:
        raise ValueError("human playback reviewer is not allowlisted")

    section_results = {entry["name"]: entry for entry in record["section_results"]}
    if len(section_results) != len(record["section_results"]):
        raise ValueError("duplicate section result")
    missing_sections = set(request["required_sections"]) - set(section_results)
    if missing_sections:
        raise ValueError(f"missing required sections: {','.join(sorted(missing_sections))}")
    sections_reviewed: list[str] = []
    na_sections: dict[str, str] = {}
    for name in request["required_sections"]:
        result = section_results[name]
        if result["status"] == "reviewed":
            if result["not_applicable_reason"] is not None:
                raise ValueError(f"reviewed section has not-applicable reason: {name}")
            sections_reviewed.append(name)
        else:
            reason = result["not_applicable_reason"]
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"not-applicable section requires reason: {name}")
            na_sections[name] = reason.strip()

    category_results = {entry["name"]: entry for entry in record["category_results"]}
    if len(category_results) != len(record["category_results"]):
        raise ValueError("duplicate category result")
    missing_categories = set(request["required_categories"]) - set(category_results)
    if missing_categories:
        raise ValueError(f"missing required categories: {','.join(sorted(missing_categories))}")
    category_scores: dict[str, float] = {}
    na_categories: dict[str, str] = {}
    threshold_failures: list[str] = []
    for name in request["required_categories"]:
        result = category_results[name]
        if result["status"] == "scored":
            if result["score"] is None or result["not_applicable_reason"] is not None:
                raise ValueError(f"scored category is malformed: {name}")
            score = float(result["score"])
            category_scores[name] = score
            if score < float(request["minimum_score"]):
                threshold_failures.append(name)
        else:
            reason = result["not_applicable_reason"]
            if result["score"] is not None or not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"not-applicable category is malformed: {name}")
            if name not in {"mix_balance", "av_sync"}:
                raise ValueError(f"mandatory category cannot be not-applicable: {name}")
            na_categories[name] = reason.strip()

    blocking_defects = [item for item in record["defects"] if item["severity"] in {"high", "critical"}]
    if record["decision"] == "PASS" and (threshold_failures or blocking_defects):
        raise ValueError("PASS decision conflicts with score threshold or blocking defect")
    if record["decision"] != "PASS":
        raise ValueError("human review is not a passing decision")

    proof = {
        "schema_name": "wave64_human_playback_review_proof",
        "proof_version": 1,
        "proof_kind": "playback_review",
        "authority_type": "human",
        "reviewer_id": identity["reviewer_id"],
        "authority_id": identity["authority_id"],
        "role": identity["role"],
        "synthetic_only": False,
        "audio_sha256": request["artifact_binding"]["sha256"],
        "request_sha256": _sha256(request_path),
        "record_sha256": _sha256(record_path),
        "is_synthetic": False,
        "production_evidence": True,
        "self_authorized": False,
        "independence_attestation": record["independence_attestation"],
        "playback_conditions": record["playback_conditions"],
        "sections_reviewed": sections_reviewed,
        "not_applicable_sections": na_sections,
        "category_scores": category_scores,
        "not_applicable_categories": na_categories,
        "observed_transcript": record["observed_transcript"],
        "defects": record["defects"],
        "decision": record["decision"],
    }
    schema = json.loads(PROOF_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(proof))
    if errors:
        raise ValueError(f"proof schema validation failed: {errors[0].message}")
    return proof


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        output = Path(args.output).resolve()
        if output.exists():
            raise ValueError(f"output already exists: {output}")
        proof = validate_review(Path(args.request).resolve(), Path(args.record).resolve())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "PASS", "proof_sha256": _sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
