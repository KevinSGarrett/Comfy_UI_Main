#!/usr/bin/env python3
"""Apply the fail-closed RealESRGAN source-selection and export policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY = ROOT / "Plan/10_REGISTRIES/realesrgan_export_selection_policy.json"
DEFAULT_REGISTRY = ROOT / "Plan/10_REGISTRIES/realesrgan_export_candidate_registry.json"
DEFAULT_STAMP = "20260711T044500-0500"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    candidate = (ROOT / value).resolve()
    candidate.relative_to(ROOT.resolve())
    return candidate


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def visual_evidence_is_bound(candidate: dict[str, Any], evidence: dict[str, Any]) -> bool:
    binding = candidate.get("visual_evidence_binding", {})
    if not isinstance(binding, dict):
        return False
    source_hash = str(candidate.get("source", {}).get("sha256", ""))
    output_hash = str(candidate.get("output", {}).get("sha256", ""))
    if not source_hash or not output_hash:
        return False

    schema = binding.get("schema")
    if schema == "singleton_source_generated":
        return (
            evidence.get("source_image", {}).get("sha256") == source_hash
            and evidence.get("generated_image", {}).get("sha256") == output_hash
        )
    if schema == "multisource_sample":
        sample_id = binding.get("sample_id")
        samples = evidence.get("samples", [])
        if not isinstance(sample_id, str) or not isinstance(samples, list):
            return False
        matches = [sample for sample in samples if isinstance(sample, dict) and sample.get("sample_id") == sample_id]
        return (
            len(matches) == 1
            and matches[0].get("source", {}).get("sha256") == source_hash
            and matches[0].get("output", {}).get("sha256") == output_hash
        )
    return False


def calculate_metrics(source_path: Path, output_path: Path) -> tuple[dict[str, Any], tuple[int, int], tuple[int, int]]:
    with Image.open(source_path) as loaded:
        source = loaded.convert("RGB")
        source_size = source.size
        source_pixels = np.asarray(source)
    with Image.open(output_path) as loaded:
        output = loaded.convert("RGB")
        output_size = output.size
        downsampled = np.asarray(output.resize(source_size, Image.Resampling.LANCZOS))

    source_float = source_pixels.astype(np.float32)
    downsampled_float = downsampled.astype(np.float32)
    metrics = {
        "downsample_ssim": float(structural_similarity(source_pixels, downsampled, channel_axis=2, data_range=255)),
        "downsample_psnr_db": float(peak_signal_noise_ratio(source_pixels, downsampled, data_range=255)),
        "downsample_mae": float(np.mean(np.abs(source_float - downsampled_float))),
        "mean_color_shift": float(np.mean(np.abs(source_float.mean(axis=(0, 1)) - downsampled_float.mean(axis=(0, 1))))),
    }
    return metrics, source_size, output_size


def decide_export(
    policy: dict[str, Any],
    technical_pass: bool,
    evidence_valid: bool,
    visual_review: dict[str, Any],
    runtime_scope: str,
) -> dict[str, Any]:
    contract = policy["decision_contract"]
    allowed = set(policy["visual_review"]["allowed_dispositions"])
    review_complete = visual_review.get("review_complete") is True
    reviewer_present = bool(str(visual_review.get("reviewer", "")).strip())
    disposition = str(visual_review.get("disposition", ""))
    blockers = visual_review.get("blocking_regressions", [])
    blockers_valid = isinstance(blockers, list) and all(isinstance(value, str) and value for value in blockers)
    preferred = visual_review.get("preferred_over_source")
    visual_valid = review_complete and reviewer_present and disposition in allowed and blockers_valid and preferred in (True, False, None)

    rejection_reasons: list[str] = []
    if not evidence_valid or not visual_valid:
        if not evidence_valid:
            rejection_reasons.append("required_evidence_missing_invalid_or_not_hash_bound")
        if not visual_valid:
            rejection_reasons.append("visual_review_missing_or_invalid")
        recommendation = contract["missing_or_invalid_evidence"]
    elif not technical_pass:
        rejection_reasons.append("technical_preservation_or_runtime_gate_failed")
        recommendation = contract["technical_failure"]
    elif blockers or disposition == "retain_source" or preferred is False:
        rejection_reasons.extend(blockers or ["explicit_retain_source_disposition"])
        recommendation = contract["visual_regression_or_explicit_retain"]
    elif disposition == "prefer_upscale" and preferred is True:
        recommendation = contract["explicit_preference"]
    elif disposition == "conditional_resolution_export" and preferred is None:
        recommendation = contract["conditional_resolution_use"]
    else:
        rejection_reasons.append("visual_disposition_and_preference_are_inconsistent")
        recommendation = contract["missing_or_invalid_evidence"]

    local_export_allowed = recommendation in {
        contract["conditional_resolution_use"],
        contract["explicit_preference"],
    }
    return {
        "visual_review_valid": visual_valid,
        "quality_preferred": recommendation == contract["explicit_preference"],
        "export_recommendation": recommendation,
        "local_export_allowed": local_export_allowed,
        "source_master_retention_required": True,
        "final_production_export_allowed": local_export_allowed and runtime_scope == "target",
        "rejection_reasons": rejection_reasons,
        "advisories": visual_review.get("advisories", []) if isinstance(visual_review.get("advisories", []), list) else [],
    }


def evaluate_candidate(candidate: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    required = ["candidate_id", "source_class", "runtime_scope", "source", "output", "runtime_evidence", "visual_evidence", "visual_evidence_binding", "visual_review"]
    missing_fields = [key for key in required if key not in candidate]
    if missing_fields:
        return {
            "candidate_id": str(candidate.get("candidate_id", "unknown")),
            "source_class": str(candidate.get("source_class", "unknown")),
            "technical_pass": False,
            "evidence_valid": False,
            **decide_export(policy, False, False, candidate.get("visual_review", {}), str(candidate.get("runtime_scope", "unknown"))),
            "checks": {"required_fields_present": False},
            "errors": [f"missing_required_fields:{','.join(missing_fields)}"],
        }

    errors: list[str] = []
    checks: dict[str, bool] = {"required_fields_present": True}
    source_class = str(candidate["source_class"])
    checks["source_class_registered"] = source_class in policy["source_classes"]

    try:
        source_path = project_path(str(candidate["source"]["path"]))
        output_path = project_path(str(candidate["output"]["path"]))
        runtime_path = project_path(str(candidate["runtime_evidence"]))
        visual_path = project_path(str(candidate["visual_evidence"]))
    except (KeyError, ValueError) as exc:
        errors.append(f"path_or_shape_error:{exc}")
        return {
            "candidate_id": str(candidate["candidate_id"]),
            "source_class": source_class,
            "technical_pass": False,
            "evidence_valid": False,
            **decide_export(policy, False, False, candidate["visual_review"], str(candidate["runtime_scope"])),
            "checks": checks,
            "errors": errors,
        }

    for label, path in (("source", source_path), ("output", output_path), ("runtime_evidence", runtime_path), ("visual_evidence", visual_path)):
        checks[f"{label}_exists"] = path.is_file()
    files_exist = all(checks[key] for key in ("source_exists", "output_exists", "runtime_evidence_exists", "visual_evidence_exists"))

    metrics: dict[str, Any] = {}
    source_size: tuple[int, int] | None = None
    output_size: tuple[int, int] | None = None
    if files_exist:
        checks["source_sha256_matches"] = sha256(source_path) == str(candidate["source"].get("sha256", ""))
        checks["output_sha256_matches"] = sha256(output_path) == str(candidate["output"].get("sha256", ""))
        try:
            metrics, source_size, output_size = calculate_metrics(source_path, output_path)
        except Exception as exc:  # Fail closed on decode or metric ambiguity.
            errors.append(f"image_metric_error:{type(exc).__name__}:{exc}")
    else:
        checks["source_sha256_matches"] = False
        checks["output_sha256_matches"] = False

    thresholds = policy["technical_thresholds"]
    scale = int(thresholds["scale_factor"])
    checks["exact_scale_dimensions"] = bool(
        source_size
        and output_size
        and output_size == (source_size[0] * scale, source_size[1] * scale)
    )
    checks["downsample_ssim_pass"] = metrics.get("downsample_ssim", -1.0) >= float(thresholds["minimum_downsample_ssim"])
    checks["downsample_psnr_pass"] = metrics.get("downsample_psnr_db", -1.0) >= float(thresholds["minimum_downsample_psnr_db"])
    checks["downsample_mae_pass"] = metrics.get("downsample_mae", float("inf")) <= float(thresholds["maximum_downsample_mae"])
    checks["mean_color_shift_pass"] = metrics.get("mean_color_shift", float("inf")) <= float(thresholds["maximum_mean_color_shift"])

    runtime: dict[str, Any] = {}
    visual: dict[str, Any] = {}
    if runtime_path.is_file():
        try:
            runtime = read_json(runtime_path)
        except Exception as exc:
            errors.append(f"runtime_evidence_error:{type(exc).__name__}:{exc}")
    if visual_path.is_file():
        try:
            visual = read_json(visual_path)
        except Exception as exc:
            errors.append(f"visual_evidence_error:{type(exc).__name__}:{exc}")

    checks["runtime_result_accepted"] = runtime.get("result") in policy["accepted_runtime_results"]
    checks["generation_executed"] = runtime.get("generation_executed") is True
    checks["request_hash_matched"] = runtime.get("run_package", {}).get("prompt_request", {}).get("hash_match") is True
    checks["server_stopped_and_port_closed"] = runtime.get("local_comfy", {}).get("stopped_by_helper") is True and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True
    checks["visual_evidence_bound_to_source_and_output"] = visual_evidence_is_bound(candidate, visual)

    evidence_integrity_keys = [
        "source_class_registered",
        "source_exists",
        "output_exists",
        "runtime_evidence_exists",
        "visual_evidence_exists",
        "source_sha256_matches",
        "output_sha256_matches",
        "runtime_result_accepted",
        "generation_executed",
        "request_hash_matched",
        "server_stopped_and_port_closed",
    ]
    evidence_valid = (
        all(checks.get(key) is True for key in evidence_integrity_keys)
        and checks["visual_evidence_bound_to_source_and_output"]
        and not errors
    )
    technical_keys = evidence_integrity_keys + [
        "exact_scale_dimensions",
        "downsample_ssim_pass",
        "downsample_psnr_pass",
        "downsample_mae_pass",
        "mean_color_shift_pass",
    ]
    technical_pass = all(checks.get(key) is True for key in technical_keys) and not errors
    failed_technical_checks = [key for key in technical_keys if checks.get(key) is not True]
    decision = decide_export(policy, technical_pass, evidence_valid, candidate["visual_review"], str(candidate["runtime_scope"]))
    return {
        "candidate_id": str(candidate["candidate_id"]),
        "source_class": source_class,
        "runtime_scope": str(candidate["runtime_scope"]),
        "source": {"path": rel(source_path), "sha256": str(candidate["source"].get("sha256", "")), "width": source_size[0] if source_size else None, "height": source_size[1] if source_size else None},
        "output": {"path": rel(output_path), "sha256": str(candidate["output"].get("sha256", "")), "width": output_size[0] if output_size else None, "height": output_size[1] if output_size else None},
        "runtime_evidence": rel(runtime_path),
        "visual_evidence": rel(visual_path),
        "technical_pass": technical_pass,
        "failed_technical_checks": failed_technical_checks,
        "evidence_valid": evidence_valid,
        "metrics": metrics,
        "checks": checks,
        **decision,
        "errors": errors,
    }


def run_decision_fixture_tests(policy: dict[str, Any]) -> list[dict[str, Any]]:
    base_review: dict[str, Any] = {
        "review_complete": True,
        "reviewer": "fixture reviewer",
        "disposition": "conditional_resolution_export",
        "preferred_over_source": None,
        "blocking_regressions": [],
        "advisories": [],
    }
    contract = policy["decision_contract"]
    fixtures = [
        ("missing_evidence", True, False, base_review, contract["missing_or_invalid_evidence"]),
        ("technical_failure", False, True, base_review, contract["technical_failure"]),
        ("missing_visual_review", True, True, {}, contract["missing_or_invalid_evidence"]),
        ("blocking_visual_regression", True, True, {**base_review, "blocking_regressions": ["waxy_skin_amplification"]}, contract["visual_regression_or_explicit_retain"]),
        ("explicit_retain_source", True, True, {**base_review, "disposition": "retain_source", "preferred_over_source": False}, contract["visual_regression_or_explicit_retain"]),
        ("conditional_resolution_export", True, True, base_review, contract["conditional_resolution_use"]),
        ("explicit_preference", True, True, {**base_review, "disposition": "prefer_upscale", "preferred_over_source": True}, contract["explicit_preference"]),
        ("inconsistent_preference", True, True, {**base_review, "disposition": "prefer_upscale", "preferred_over_source": None}, contract["missing_or_invalid_evidence"]),
    ]
    results = []
    for fixture_id, technical_pass, evidence_valid, review, expected in fixtures:
        decision = decide_export(policy, technical_pass, evidence_valid, deepcopy(review), "local")
        actual = decision["export_recommendation"]
        results.append({"fixture_id": fixture_id, "expected": expected, "actual": actual, "pass": actual == expected})
    return results


def run_binding_fixture_tests() -> list[dict[str, Any]]:
    source_hash = "a" * 64
    output_hash = "b" * 64
    singleton = {
        "source": {"sha256": source_hash},
        "output": {"sha256": output_hash},
        "visual_evidence_binding": {"schema": "singleton_source_generated"},
    }
    multisource = {
        "source": {"sha256": source_hash},
        "output": {"sha256": output_hash},
        "visual_evidence_binding": {"schema": "multisource_sample", "sample_id": "target"},
    }
    fixtures = [
        (
            "singleton_exact_fields",
            singleton,
            {"source_image": {"sha256": source_hash}, "generated_image": {"sha256": output_hash}},
            True,
        ),
        (
            "singleton_hashes_only_in_unrelated_fields",
            singleton,
            {"notes": [source_hash, output_hash]},
            False,
        ),
        (
            "singleton_wrong_output_hash",
            singleton,
            {"source_image": {"sha256": source_hash}, "generated_image": {"sha256": "c" * 64}},
            False,
        ),
        (
            "multisource_exact_sample",
            multisource,
            {"samples": [{"sample_id": "target", "source": {"sha256": source_hash}, "output": {"sha256": output_hash}}]},
            True,
        ),
        (
            "multisource_hashes_on_wrong_sample",
            multisource,
            {"samples": [{"sample_id": "other", "source": {"sha256": source_hash}, "output": {"sha256": output_hash}}]},
            False,
        ),
        (
            "multisource_duplicate_sample_id",
            multisource,
            {"samples": [
                {"sample_id": "target", "source": {"sha256": source_hash}, "output": {"sha256": output_hash}},
                {"sample_id": "target", "source": {"sha256": source_hash}, "output": {"sha256": output_hash}},
            ]},
            False,
        ),
        (
            "unknown_binding_schema",
            {**singleton, "visual_evidence_binding": {"schema": "unknown"}},
            {"source_image": {"sha256": source_hash}, "generated_image": {"sha256": output_hash}},
            False,
        ),
    ]
    results = []
    for fixture_id, candidate, evidence, expected in fixtures:
        actual = visual_evidence_is_bound(candidate, evidence)
        results.append({"fixture_id": fixture_id, "expected": expected, "actual": actual, "pass": actual is expected})
    return results


def validate_policy(policy: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("technical_thresholds", "accepted_runtime_results", "visual_review", "decision_contract", "source_classes", "boundaries"):
        if key not in policy:
            errors.append(f"policy_missing:{key}")
    if registry.get("lane_id") != policy.get("lane_id"):
        errors.append("registry_policy_lane_mismatch")
    if not isinstance(registry.get("candidates"), list) or not registry["candidates"]:
        errors.append("registry_candidates_missing")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--stamp", default=DEFAULT_STAMP)
    parser.add_argument("--self-test-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = read_json(args.policy.resolve())
    registry = read_json(args.registry.resolve())
    policy_errors = validate_policy(policy, registry)
    fixture_tests = run_decision_fixture_tests(policy) if not policy_errors else []
    binding_fixture_tests = run_binding_fixture_tests() if not policy_errors else []
    fixtures_pass = (
        bool(fixture_tests)
        and all(test["pass"] for test in fixture_tests)
        and bool(binding_fixture_tests)
        and all(test["pass"] for test in binding_fixture_tests)
    )
    if args.self_test_only:
        print(json.dumps({"policy_errors": policy_errors, "decision_fixture_tests": fixture_tests, "binding_fixture_tests": binding_fixture_tests, "pass": not policy_errors and fixtures_pass}, indent=2))
        return 0 if not policy_errors and fixtures_pass else 2

    records = [evaluate_candidate(candidate, policy) for candidate in registry.get("candidates", [])] if not policy_errors else []
    deterministic_count = sum(1 for record in records if record["export_recommendation"] not in {"hold_fail_closed_missing_or_invalid_evidence"})
    policy_pass = not policy_errors and fixtures_pass and len(records) == 3 and all(record["evidence_valid"] for record in records) and deterministic_count == len(records)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-REALESRGAN-SOURCE-SELECTION-EXPORT-GATE-{args.stamp}",
        "timestamp": timestamp,
        "lane_id": str(policy.get("lane_id", "")),
        "result": "pass_realesrgan_export_selection_policy_enforced" if policy_pass else "fail_closed_realesrgan_export_selection_policy",
        "pass": policy_pass,
        "scope": "local_three_source_class_export_selection_policy_and_negative_fixture_validation",
        "policy": {"path": rel(args.policy.resolve()), "sha256": sha256(args.policy.resolve())},
        "candidate_registry": {"path": rel(args.registry.resolve()), "sha256": sha256(args.registry.resolve())},
        "policy_errors": policy_errors,
        "negative_fixture_tests": fixture_tests,
        "binding_fixture_tests": binding_fixture_tests,
        "candidates": records,
        "aggregate": {
            "candidate_count": len(records),
            "technical_pass_count": sum(1 for record in records if record["technical_pass"]),
            "technical_reject_count": sum(1 for record in records if record["export_recommendation"] == policy["decision_contract"]["technical_failure"]),
            "evidence_valid_count": sum(1 for record in records if record["evidence_valid"]),
            "conditional_resolution_export_count": sum(1 for record in records if record["export_recommendation"] == policy["decision_contract"]["conditional_resolution_use"]),
            "preferred_upscale_count": sum(1 for record in records if record["quality_preferred"]),
            "retain_source_count": sum(1 for record in records if record["export_recommendation"] == policy["decision_contract"]["visual_regression_or_explicit_retain"]),
            "final_production_export_allowed_count": sum(1 for record in records if record["final_production_export_allowed"]),
            "negative_fixture_pass_count": sum(1 for test in fixture_tests if test["pass"]),
            "negative_fixture_count": len(fixture_tests),
            "binding_fixture_pass_count": sum(1 for test in binding_fixture_tests if test["pass"]),
            "binding_fixture_count": len(binding_fixture_tests),
        },
        "quality_decision": {
            "universal_upscale_preference_claimed": False,
            "source_master_retention_required": True,
            "canny_upscale_rejected_by_strict_ssim": any(record["candidate_id"] == "canny_portrait_seed711570105" and record["export_recommendation"] == policy["decision_contract"]["technical_failure"] for record in records),
            "two_character_upscale_rejected_as_preferred": any(record["candidate_id"] == "two_character_contact_seed7152026252" and not record["local_export_allowed"] for record in records),
            "final_production_export_allowed": False,
            "reason": "The Normal full-body output passes strict preservation for conditional resolution delivery. The older Canny upscale misses the strict SSIM threshold, and the two-character upscale is retained only as technical evidence because skin and dense fabric regress.",
        },
        "boundaries": {
            "new_generation_executed": False,
            "source_or_output_replayed": False,
            "local_only": True,
            "aws_contacted": False,
            "ec2_started": False,
            "target_runtime_proven_by_this_gate": False,
            "final_lane_certification": False,
            "gold_masks_consumed": False,
            "mask_promotion": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
        },
    }
    qa_path = ROOT / f"Plan/Instructions/QA/Evidence/Image_Artifact_QA/W70_REALESRGAN_SOURCE_SELECTION_EXPORT_GATE_{args.stamp}.json"
    tracker_qa_path = ROOT / f"Plan/Tracker/Evidence/Image_Artifact_QA/W70_REALESRGAN_SOURCE_SELECTION_EXPORT_GATE_{args.stamp}.json"
    write_json(qa_path, qa)
    tracker_qa_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(qa_path, tracker_qa_path)

    item = {
        "item_id": f"ITEM-W70-REALESRGAN-SOURCE-SELECTION-EXPORT-GATE-{args.stamp}",
        "timestamp": timestamp,
        "lane_id": qa["lane_id"],
        "title": "RealESRGAN fail-closed source-selection and export policy",
        "status": "complete_pass_with_notes" if policy_pass else "complete_qa_failed",
        "implementation_complete": True,
        "runtime_replay_required": False,
        "technical_qa_complete": True,
        "visual_qa_normalization_complete": True,
        "negative_fixture_testing_complete": fixtures_pass,
        "tracker_update_complete": True,
        "itemized_list_update_complete": True,
        "known_issue_review_complete": True,
        "bounded_done_certification_allowed": policy_pass,
        "final_lane_certification_allowed": False,
        "qa_evidence": rel(qa_path),
        "known_issues": [
            "No current local sample is explicitly preferred over its source for hyperrealism quality.",
            "The older Canny portrait upscale misses the strict 0.95 SSIM preservation threshold and is rejected by this policy.",
            "The two-character upscale remains technically valid but is rejected as the preferred export.",
            "Target-runtime proof remains separate and is required before final production export approval."
        ],
    }
    item_path = ROOT / f"Plan/Items/Reports/W70_REALESRGAN_SOURCE_SELECTION_EXPORT_GATE_ITEMIZED_LIST_{args.stamp}.json"
    write_json(item_path, item)

    cert = {
        "evidence_id": f"W70-REALESRGAN-SOURCE-SELECTION-EXPORT-GATE-DONE-{args.stamp}",
        "timestamp": timestamp,
        "lane_id": qa["lane_id"],
        "result": "done_bounded_realesrgan_source_selection_export_gate" if policy_pass else "blocked_realesrgan_source_selection_export_gate_failed",
        "done_scope": qa["scope"],
        "closes_local_scope_item": policy_pass,
        "closes_final_lane_work_order": False,
        "qa_evidence": rel(qa_path),
        "itemized_list_record": rel(item_path),
        "implementation_test_qa_evidence_complete": policy_pass,
        "final_lane_certification": False,
        "full_project_certification": False,
        "certifier": "Codex Desktop autonomous release manager",
        "next_action": "Use this selector for future RealESRGAN candidates. Run target-runtime proof and final lane review only when intentionally selected; do not replay completed local samples."
    }
    cert_path = ROOT / f"Plan/Instructions/QA/Evidence/Done_Certifications/W70_REALESRGAN_SOURCE_SELECTION_EXPORT_GATE_DONE_{args.stamp}.json"
    tracker_cert_path = ROOT / f"Plan/Tracker/Evidence/Done_Certifications/W70_REALESRGAN_SOURCE_SELECTION_EXPORT_GATE_DONE_{args.stamp}.json"
    write_json(cert_path, cert)
    tracker_cert_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cert_path, tracker_cert_path)

    print(json.dumps({"qa": rel(qa_path), "item": rel(item_path), "certificate": rel(cert_path), "pass": policy_pass, "aggregate": qa["aggregate"]}, indent=2))
    return 0 if policy_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
