#!/usr/bin/env python3
"""Fail-closed validator for Base/OpenPose remediation ownership decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

BASE_LANE_ID = "sdxl_realvisxl_base_lane"
OPENPOSE_LANE_ID = "sdxl_realvisxl_controlnet_openpose_lane"

W66_BLOCKER_PATH = ROOT / (
    "Plan/Instructions/QA/Evidence/Done_Certifications/"
    "W66_BASE_LANE_FINAL_CERTIFICATION_BLOCKER_AFTER_ROBUSTNESS_20260711T035500-0500.json"
)
W70_DONE_PATH = ROOT / (
    "Plan/Instructions/QA/Evidence/Done_Certifications/"
    "W70_BASE_REMEDIATION_OPENPOSE_CONTACT_PAIR_DONE_20260711T074300-0500.json"
)
W70_QA_PATH = ROOT / (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/"
    "W70_LOCAL_BASE_REMEDIATION_OPENPOSE_CONTACT_PAIR_QA_20260711T073700-0500.json"
)
QUEUE_PATH = ROOT / "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
ACTIVE_PATH = ROOT / "Workflows/base_generation/ACTIVE_LANES.json"

INPUT_PATHS = (W66_BLOCKER_PATH, W70_DONE_PATH, W70_QA_PATH, QUEUE_PATH, ACTIVE_PATH)

EXPECTED_BASE_STATUS = (
    "runtime_smoke_proven_canonical_two_character_seed_robustness_failed_"
    "local_openpose_composition_remediation_pair_passed_final_certification_blocked"
)
EXPECTED_BASE_NEXT_GATE = (
    "scope_matched_target_runtime_proof_and_explicit_review_before_any_base_owned_"
    "composition_route_adoption"
)
REQUIRED_QA_RECORD_CHECKS = {
    "runtime_passed",
    "generation_executed",
    "request_hash_matched_by_runtime",
    "request_hash_matches_package",
    "request_hash_matches_runtime",
    "server_stopped_and_port_closed",
    "package_lane_is_canonical_openpose",
    "profile_lane_is_canonical_openpose",
    "package_profile_matches",
    "image_pullback_hash_bound",
    "diagnostic_pullback_hash_bound",
    "diagnostic_control_pixels_match_prepared_input",
    "controlnet_asset_bound",
    "control_image_bound",
    "seed_bound",
    "positive_prompt_bound",
    "negative_prompt_bound",
}
BASE_STATUS_POLICY_TOKENS = {
    "canonical",
    "two",
    "character",
    "robustness",
    "failed",
    "openpose",
    "remediation",
    "passed",
    "final",
    "certification",
    "blocked",
}
BASE_NEXT_GATE_POLICY_TOKENS = {
    "scope",
    "matched",
    "target",
    "runtime",
    "proof",
    "explicit",
    "review",
    "base",
    "owned",
    "composition",
    "route",
    "adoption",
}
BASE_PROMOTION_POLICY_TOKENS = {
    "cross",
    "lane",
    "openpose",
    "remediation",
    "evidence",
    "base",
    "ownership",
    "scope",
    "matched",
    "target",
    "runtime",
    "proof",
    "final",
    "review",
    "separate",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


def find_lane(queue_like: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lanes = queue_like.get("lanes")
    if not isinstance(lanes, list):
        return {}
    for lane in lanes:
        if isinstance(lane, dict) and lane.get("lane_id") == lane_id:
            return lane
    return {}


def make_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def normalized_policy_tokens(value: Any) -> set[str]:
    normalized = "".join(
        character.lower() if character.isalnum() else " " for character in str(value)
    )
    return set(normalized.split())


def policy_contains_tokens(value: Any, required: set[str]) -> bool:
    return required.issubset(normalized_policy_tokens(value))


def evaluate_payloads(
    *,
    w66_blocker: dict[str, Any],
    w70_done: dict[str, Any],
    w70_qa: dict[str, Any],
    queue_manifest: dict[str, Any],
    active_manifest: dict[str, Any],
) -> dict[str, Any]:
    queue_base = find_lane(queue_manifest, BASE_LANE_ID)
    queue_openpose = find_lane(queue_manifest, OPENPOSE_LANE_ID)
    active_base = find_lane(active_manifest, BASE_LANE_ID)
    active_openpose = find_lane(active_manifest, OPENPOSE_LANE_ID)

    base_blocked = (
        w66_blocker.get("lane_id") == BASE_LANE_ID
        and w66_blocker.get("result")
        == "blocked_base_lane_final_certification_robustness_pair_failed"
        and w66_blocker.get("final_decision") == "blocked"
        and w66_blocker.get("closes_work_order") is False
        and w66_blocker.get("final_lane_certification") is False
    )

    qa_strict = w70_qa.get("strict_decision", {})
    qa_boundaries = w70_qa.get("boundaries", {})
    qa_records = w70_qa.get("records", [])
    qa_records_pass = (
        isinstance(qa_records, list)
        and len(qa_records) == 2
        and all(
            isinstance(record, dict)
            and isinstance(record.get("checks"), dict)
            and REQUIRED_QA_RECORD_CHECKS.issubset(record["checks"])
            and all(record["checks"].get(name) is True for name in REQUIRED_QA_RECORD_CHECKS)
            for record in qa_records
        )
    )
    remediation_owned_by_openpose = (
        w70_done.get("lane_id") == OPENPOSE_LANE_ID
        and w70_done.get("remediates_lane_id") == BASE_LANE_ID
        and w70_done.get("result")
        == "done_bounded_local_openpose_composition_remediation_pair_pass_with_notes"
        and w70_done.get("closes_local_scope_item") is True
        and w70_done.get("implementation_test_qa_evidence_complete") is True
        and w70_done.get("closes_base_final_lane_work_order") is False
        and w70_done.get("closes_openpose_final_lane_work_order") is False
        and w70_done.get("final_base_lane_certification") is False
        and w70_done.get("final_openpose_lane_certification") is False
        and w70_done.get("full_project_certification") is False
        and w70_qa.get("lane_id") == OPENPOSE_LANE_ID
        and w70_qa.get("remediates_lane_id") == BASE_LANE_ID
        and w70_qa.get("technical_pass") is True
        and w70_qa.get("strict_visual_disposition", {}).get("contract_valid") is True
        and w70_qa.get("strict_visual_disposition", {}).get("all_samples_pass") is True
        and qa_records_pass
        and qa_strict.get("bounded_sample_count") == 2
        and qa_strict.get("materially_different_composition_control_available") is True
        and qa_strict.get("base_final_certification_allowed") is False
        and qa_strict.get("openpose_final_certification_allowed") is False
        and qa_strict.get("target_runtime_proof_added") is False
    )

    cross_lane_separation_rule = (
        policy_contains_tokens(queue_base.get("status"), BASE_STATUS_POLICY_TOKENS)
        and policy_contains_tokens(
            queue_base.get("required_next_runtime_gate"),
            BASE_NEXT_GATE_POLICY_TOKENS,
        )
        and policy_contains_tokens(
            queue_base.get("promotion_rule"),
            BASE_PROMOTION_POLICY_TOKENS,
        )
    )

    queue_active_sync = (
        queue_base.get("lane_id") == BASE_LANE_ID
        and queue_openpose.get("lane_id") == OPENPOSE_LANE_ID
        and active_base.get("lane_id") == BASE_LANE_ID
        and active_openpose.get("lane_id") == OPENPOSE_LANE_ID
        and active_base.get("status") == queue_base.get("status")
        and active_base.get("next_gate") == queue_base.get("required_next_runtime_gate")
        and active_openpose.get("status") == queue_openpose.get("status")
        and active_openpose.get("next_gate")
        == queue_openpose.get("required_next_runtime_gate")
    )

    openpose_only_route_resolution = (
        qa_strict.get("materially_different_composition_control_available") is True
        and qa_strict.get("base_canonical_robustness_failure_cleared") is False
        and "pending_target_runtime_and_final_certification"
        in str(queue_openpose.get("status", ""))
    )

    base_blockers = {
        "base_owned_scope_matched_target_runtime_proof_missing": (
            qa_strict.get("target_runtime_proof_added") is False
            and policy_contains_tokens(
                queue_base.get("required_next_runtime_gate"),
                {"scope", "matched", "target", "runtime", "proof"},
            )
        ),
        "base_route_adoption_decision_pending": (
            policy_contains_tokens(
                queue_base.get("required_next_runtime_gate"),
                {"explicit", "review", "base", "owned", "composition", "route", "adoption"},
            )
        ),
        "base_final_review_remains_blocked": w66_blocker.get("final_decision") == "blocked",
    }

    zero_activity_boundary = {
        "validator_generation_executed": False,
        "validator_contacted_aws": False,
        "validator_ec2_started": False,
        "validator_masks_promoted": False,
        "validator_wave70_hard_gate_rerun": False,
        "validator_wave71_or_higher_activated": False,
        "validator_jira_mutation_performed": False,
        "source_target_runtime_proof_added": qa_strict.get("target_runtime_proof_added"),
        "source_aws_contacted": qa_boundaries.get("aws_contacted"),
        "source_ec2_started": qa_boundaries.get("ec2_started"),
        "source_mask_promotion_performed": qa_boundaries.get("mask_promotion_performed"),
        "source_wave70_hard_gate_rerun": qa_boundaries.get("wave70_hard_gate_rerun"),
        "source_wave71_activated": qa_boundaries.get("wave71_activated"),
        "source_gold_masks_consumed": qa_boundaries.get("gold_masks_consumed"),
        "queue_generation_allowed": queue_manifest.get("runtime_boundary", {}).get(
            "generation_allowed_by_queue_file"
        ),
    }
    boundary_requirements = {
        "source_local_only": qa_boundaries.get("local_only") is True,
        "source_gold_masks_not_consumed": qa_boundaries.get("gold_masks_consumed")
        is False,
    }
    zero_activity_pass = all(
        value is False for value in zero_activity_boundary.values()
    ) and all(boundary_requirements.values())

    checks = [
        make_check(
            "base_lane_blocked_and_not_certified",
            base_blocked,
            "W66 blocker remains canonical for Base lane and final decision is blocked.",
        ),
        make_check(
            "openpose_owns_remediation_with_two_seed_pass_and_noncertification",
            remediation_owned_by_openpose,
            "W70 remediation remains OpenPose-owned, remediates Base, passes 2-seed technical/visual QA, and keeps both lane certifications false.",
        ),
        make_check(
            "base_queue_status_and_promotion_rule_keep_cross_lane_ownership_separate",
            cross_lane_separation_rule,
            "Base queue status/gate/rule keep OpenPose remediation evidence separate from Base certification.",
        ),
        make_check(
            "active_lane_status_and_next_gate_match_queue",
            queue_active_sync,
            "ACTIVE_LANES status/next_gate align with runtime queue for Base and OpenPose.",
        ),
        make_check(
            "materially_different_route_resolved_only_in_openpose",
            openpose_only_route_resolution,
            "Materially different composition-control route is available in OpenPose and does not clear Base canonical failure.",
        ),
        make_check(
            "base_owned_blockers_still_present",
            all(base_blockers.values()),
            "Base-owned target-runtime proof, route-adoption decision, and final review remain blockers.",
        ),
        make_check(
            "zero_generation_aws_masks_wave_gates_jira_confirmed",
            zero_activity_pass,
            "Output explicitly records zero validator generation/AWS/mask/Wave/Jira actions and no source gate promotion.",
        ),
    ]
    pass_all = all(check["pass"] for check in checks)
    result = (
        "pass_base_openpose_ownership_boundaries_confirmed_fail_closed"
        if pass_all
        else "fail_base_openpose_ownership_boundary_violation"
    )

    return {
        "result": result,
        "pass": pass_all,
        "checks": checks,
        "ownership_classification": {
            "materially_different_route_resolved_only_in_openpose": openpose_only_route_resolution,
            "base_scope_matched_target_runtime_proof_blocker": base_blockers[
                "base_owned_scope_matched_target_runtime_proof_missing"
            ],
            "base_route_adoption_decision_blocker": base_blockers[
                "base_route_adoption_decision_pending"
            ],
            "base_final_review_blocker": base_blockers["base_final_review_remains_blocked"],
            "base_final_certification_allowed": False,
            "openpose_final_certification_allowed": False,
            "target_runtime_proof_added": False,
        },
        "zero_activity": zero_activity_boundary,
        "boundary_requirements": boundary_requirements,
    }


def required_files_present(paths: tuple[Path, ...]) -> list[str]:
    return [str(path) for path in paths if not path.is_file()]


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tracker-out", type=Path)
    args = parser.parse_args()

    missing = required_files_present(INPUT_PATHS)
    if missing:
        raise FileNotFoundError(f"Required input missing: {missing}")

    input_records: list[dict[str, Any]] = []
    for path in INPUT_PATHS:
        input_records.append(
            {
                "path": rel(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    w66_blocker = read_json_object(W66_BLOCKER_PATH)
    w70_done = read_json_object(W70_DONE_PATH)
    w70_qa = read_json_object(W70_QA_PATH)
    queue_manifest = read_json_object(QUEUE_PATH)
    active_manifest = read_json_object(ACTIVE_PATH)

    evaluation = evaluate_payloads(
        w66_blocker=w66_blocker,
        w70_done=w70_done,
        w70_qa=w70_qa,
        queue_manifest=queue_manifest,
        active_manifest=active_manifest,
    )

    output = {
        "schema_version": "1.0",
        "evidence_id": "W70-LOCAL-BASE-OPENPOSE-OWNERSHIP-VALIDATOR",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_scope": {"base_lane_id": BASE_LANE_ID, "openpose_lane_id": OPENPOSE_LANE_ID},
        "input_records": input_records,
        "evaluation": evaluation,
        "strict_boundaries": {
            "local_only_validation": True,
            "does_not_certify_base_lane": True,
            "does_not_certify_openpose_lane": True,
            "does_not_enable_target_runtime_proof": True,
            "zero_generation_aws_masks_wave_gates_jira": True,
        },
    }

    out = args.out.resolve()
    write_json(out, output)
    if args.tracker_out:
        tracker_out = args.tracker_out.resolve()
        tracker_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, tracker_out)

    print(json.dumps(output, indent=2))
    return 0 if evaluation["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
