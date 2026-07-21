#!/usr/bin/env python3
"""Produce immutable W64-AQA-004 evidence for a retained, visually rejected image."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image, __version__ as PILLOW_VERSION


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "produce_wave64_runpod_autonomous_audio_shadow_evidence.py"
IMAGE_MEASURER_PATH = SCRIPT_DIR / "measure_wave64_runpod_autonomous_image_quality.py"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_image_shadow_evidence.schema.json"
ZERO_HASH = "0" * 64


class EvidenceError(ValueError):
    """Raised when image lineage or review invariants fail."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise EvidenceError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_module("w64_aqa_audio_shadow_base_for_image", BASE_PATH)
COMPILER = BASE.COMPILER
MEASURER = _load_module("w64_aqa_image_measurer_for_shadow", IMAGE_MEASURER_PATH)


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("generated_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("generated_at must include a timezone")


def _find_pulled_artifact(manifest: dict[str, Any], relative_path: str) -> dict[str, Any]:
    matches = [
        item for item in manifest.get("pulled_artifacts", [])
        if item.get("local_path", "").replace("\\", "/") == relative_path
    ]
    if len(matches) != 1:
        raise EvidenceError("lineage manifest must contain exactly one artifact binding")
    return matches[0]


def build_evidence(
    *,
    artifact_path: Path,
    lineage_manifest_path: Path,
    visual_qa_path: Path,
    global_review_path: Path,
    strict_hold_path: Path,
    generated_at: str,
    artifact_relative_path: str,
    lineage_manifest_relative_path: str,
    visual_qa_relative_path: str,
    global_review_relative_path: str,
) -> dict[str, Any]:
    _validate_timestamp(generated_at)
    for path in (
        artifact_path, lineage_manifest_path, visual_qa_path, global_review_path, strict_hold_path
    ):
        if not path.is_file():
            raise EvidenceError(f"required input is absent: {path}")
    lineage = BASE._json(lineage_manifest_path)
    visual_qa = BASE._json(visual_qa_path)
    global_review = BASE._json(global_review_path)
    strict_hold = BASE._json(strict_hold_path)
    artifact_sha = BASE.sha256_file(artifact_path)
    lineage_binding = _find_pulled_artifact(lineage, artifact_relative_path)
    if lineage_binding.get("sha256") != artifact_sha:
        raise EvidenceError("artifact hash does not match lineage manifest")
    if visual_qa.get("generated_image", {}).get("sha256") != artifact_sha:
        raise EvidenceError("artifact hash does not match visual QA evidence")
    if global_review.get("artifact", {}).get("sha256") != artifact_sha:
        raise EvidenceError("artifact hash does not match global review evidence")
    if global_review.get("overall_decision") != "reject":
        raise EvidenceError("canonical global review must retain its rejection")
    defects = global_review.get("reject_on_any_global_defect", {}).get("global_defects", [])
    defect_codes = [item.get("code") for item in defects if item.get("severity") == "blocking"]
    required_defects = {"contact_placement_not_exact_target", "contact_shadow_not_clear"}
    if not required_defects.issubset(defect_codes):
        raise EvidenceError("canonical blocking visual defects are absent")
    if strict_hold.get("inference_executed") is not False or strict_hold.get("lease_acquired") is not False:
        raise EvidenceError("strict admission evidence must not claim runtime execution")
    if "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT" not in strict_hold.get("blocker_codes", []):
        raise EvidenceError("strict admission evidence lacks the foreign-workload blocker")
    installed = {
        item.get("name"): item.get("digest")
        for item in strict_hold.get("resource_snapshot", {}).get("installed_models", [])
    }
    strict_digest = installed.get("qwen2.5vl:32b")
    if not isinstance(strict_digest, str) or len(strict_digest) != 64:
        raise EvidenceError("strict model digest is absent from admission evidence")

    with Image.open(artifact_path) as image:
        width, height = image.size
        alpha_required = image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info
    hold_sha = BASE.sha256_file(strict_hold_path)
    contract_draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-row004-retained-contact-image-shadow-v1",
        "revision": 1,
        "created_at": generated_at,
        "modality": "image",
        "execution_mode": "shadow_qualification",
        "requested_outputs": [{"output_id": "retained-contact-image", "media_type": "image/png", "durable_relative_path": artifact_relative_path}],
        "quality_profile": {
            "profile_id": "w64-aqa-row004-real-contact-image-v1",
            "hard_gates": [
                {"gate_id": "decode", "metric": "decode_success", "operator": "eq", "threshold": True, "on_failure": "REJECT"},
                {"gate_id": "dynamic-range", "metric": "dynamic_range", "operator": "gte", "threshold": 50.0, "on_failure": "REPAIR"},
                {"gate_id": "entropy", "metric": "entropy_bits", "operator": "gte", "threshold": 4.0, "on_failure": "REPAIR"},
                {"gate_id": "black-clipping", "metric": "black_clip_fraction", "operator": "lt", "threshold": 0.1, "on_failure": "REPAIR"},
                {"gate_id": "white-clipping", "metric": "white_clip_fraction", "operator": "lt", "threshold": 0.1, "on_failure": "REPAIR"},
                {"gate_id": "sharpness", "metric": "sharpness_laplacian_variance", "operator": "gt", "threshold": 10.0, "on_failure": "REPAIR"}
            ],
            "review_roles": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "authority": "deterministic", "can_approve": True, "required": True},
                {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "authority": "strict", "can_approve": True, "required": True}
            ],
            "required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-ROLE-STRICT-VISUAL"]
        },
        "resource_budget": {
            "max_gpu_seconds": 120, "max_gpu_hour_usd": 0.77,
            "max_output_bytes": artifact_path.stat().st_size, "deadline_seconds": 300,
            "secondary_burst": {"enabled": False, "max_cost_usd": 0, "max_seconds": 0, "idle_ttl_seconds": 0, "eligible_gpu_classes": []}
        },
        "attempt_policy": {"max_repairs_per_defect": 0, "max_total_generations": 1, "max_no_progress_cycles": 0},
        "authority_policy": {
            "generation_host": "runpod_only", "ec2_allowed": False, "local_comfyui_allowed": False,
            "triage_can_approve": False, "model_can_promote": False,
            "workflow_model_proposal_only": True, "secrets_visible_to_models": False,
            "external_inference_allowed": False
        },
        "rollback_policy": {"revert_on_regression": True, "promotion_requires_replay": True, "retain_failed_evidence": True, "previous_accepted_artifact_sha256": None},
        "provenance": {
            "workflow_sha256": BASE.sha256_file(lineage_manifest_path),
            "input_artifacts": [
                {"artifact_id": "retained-contact-image", "sha256": artifact_sha, "durable_relative_path": artifact_relative_path},
                {"artifact_id": "canonical-visual-qa", "sha256": BASE.sha256_file(visual_qa_path), "durable_relative_path": visual_qa_relative_path},
                {"artifact_id": "canonical-global-review", "sha256": BASE.sha256_file(global_review_path), "durable_relative_path": global_review_relative_path}
            ],
            "model_bindings": [
                {"role_id": "W64-AQA-ROLE-DETERMINISTIC", "model_id": "deterministic-tool/measure_wave64_runpod_autonomous_image_quality.py", "checkpoint_sha256": BASE.sha256_file(IMAGE_MEASURER_PATH), "runtime_digest": f"pillow-{PILLOW_VERSION}", "qualification_state": "QUALIFIED"},
                {"role_id": "W64-AQA-ROLE-STRICT-VISUAL", "model_id": "ollama/qwen2.5vl:32b", "checkpoint_sha256": strict_digest, "runtime_digest": f"admission-evidence-sha256:{hold_sha}", "qualification_state": "QUALIFIED"}
            ],
            "calibration_ids": ["W64-AQA-CAL-row004-known-contact-defects-v1"]
        },
        "image_spec": {"width": width, "height": height, "color_space": "sRGB", "alpha_required": alpha_required}
    }
    contract = COMPILER.compile_contract(contract_draft)
    measurement = MEASURER.measure_image(artifact_path, contract)
    deterministic_pass = measurement["disposition"] == "PASS_DETERMINISTIC_GATES"
    evidence = {
        "schema_version": "wave64.aqa.image_shadow_evidence.v1",
        "evidence_id": ZERO_HASH,
        "generated_at": generated_at,
        "row_id": "W64-AQA-004",
        "source": {
            "artifact_relative_path": artifact_relative_path,
            "artifact_sha256": artifact_sha,
            "lineage_manifest_relative_path": lineage_manifest_relative_path,
            "lineage_manifest_sha256": BASE.sha256_file(lineage_manifest_path),
            "visual_qa_relative_path": visual_qa_relative_path,
            "visual_qa_sha256": BASE.sha256_file(visual_qa_path),
            "global_review_relative_path": global_review_relative_path,
            "global_review_sha256": BASE.sha256_file(global_review_path),
            "all_hashes_match": True
        },
        "technical_contract": contract,
        "measurement": measurement,
        "codex_visual_review": {
            "authority": "codex_final_visual_qa",
            "whole_image_inspected": True,
            "status": "REJECT_KNOWN_BLOCKING_DEFECTS",
            "blocking_findings": sorted(required_defects),
            "passing_regions": ["background", "body_proportions", "clothing", "faces", "hair", "hands", "lighting"],
            "strict_model_runtime_claimed": False
        },
        "strict_model_gate": {
            "role_id": "W64-AQA-ROLE-STRICT-VISUAL", "model": "qwen2.5vl:32b",
            "checkpoint_digest": strict_digest, "admission_evidence_sha256": hold_sha,
            "runtime_executed": False, "disposition": "HELD_ACTIVE_FOREIGN_GPU_WORKLOAD",
            "blocker_code": "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT"
        },
        "product_promotion_eligible": False,
        "overall_disposition": "PASS_DETERMINISTIC_IMAGE_GATES_REJECT_VISUAL_DEFECTS_STRICT_RUNTIME_HELD" if deterministic_pass else "FAIL_DETERMINISTIC_IMAGE_GATES"
    }
    identity_input = copy.deepcopy(evidence)
    identity_input["evidence_id"] = ZERO_HASH
    evidence["evidence_id"] = hashlib.sha256(BASE.canonical_bytes(identity_input)).hexdigest()
    schema = BASE._json(SCHEMA_PATH)
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("lineage_manifest", type=Path)
    parser.add_argument("visual_qa", type=Path)
    parser.add_argument("global_review", type=Path)
    parser.add_argument("strict_hold", type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--artifact-relative-path", required=True)
    parser.add_argument("--lineage-manifest-relative-path", required=True)
    parser.add_argument("--visual-qa-relative-path", required=True)
    parser.add_argument("--global-review-relative-path", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        evidence = build_evidence(
            artifact_path=args.artifact, lineage_manifest_path=args.lineage_manifest,
            visual_qa_path=args.visual_qa, global_review_path=args.global_review,
            strict_hold_path=args.strict_hold, generated_at=args.generated_at,
            artifact_relative_path=args.artifact_relative_path,
            lineage_manifest_relative_path=args.lineage_manifest_relative_path,
            visual_qa_relative_path=args.visual_qa_relative_path,
            global_review_relative_path=args.global_review_relative_path,
        )
        rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise EvidenceError("output already exists; evidence is immutable")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, EvidenceError, BASE.EvidenceError, COMPILER.ContractError, MEASURER.MeasurementError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
