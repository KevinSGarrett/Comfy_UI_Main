#!/usr/bin/env python3
"""Unit tests for Base/OpenPose remediation ownership validator."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_base_openpose_remediation_ownership import (  # noqa: E402
    BASE_LANE_ID,
    EXPECTED_BASE_NEXT_GATE,
    EXPECTED_BASE_STATUS,
    OPENPOSE_LANE_ID,
    REQUIRED_QA_RECORD_CHECKS,
    evaluate_payloads,
)


def valid_payloads() -> dict[str, dict]:
    queue_base = {
        "lane_id": BASE_LANE_ID,
        "status": EXPECTED_BASE_STATUS,
        "required_next_runtime_gate": EXPECTED_BASE_NEXT_GATE,
        "promotion_rule": (
            "Do not promote Base from the close-up, failed canonical seed pair, or "
            "cross-lane OpenPose remediation evidence. Base ownership, scope-matched "
            "target-runtime proof, and final review remain separate requirements."
        ),
    }
    queue_openpose = {
        "lane_id": OPENPOSE_LANE_ID,
        "status": (
            "local_openpose_tablehands_fullbody_walking_and_two_character_contact_"
            "remediation_robustness_pass_with_notes_pending_target_runtime_and_final_"
            "certification"
        ),
        "required_next_runtime_gate": (
            "target_runtime_proof_and_final_openpose_review_only_when_intentionally_selected"
        ),
    }
    active_base = {
        "lane_id": BASE_LANE_ID,
        "status": EXPECTED_BASE_STATUS,
        "next_gate": EXPECTED_BASE_NEXT_GATE,
    }
    active_openpose = {
        "lane_id": OPENPOSE_LANE_ID,
        "status": queue_openpose["status"],
        "next_gate": queue_openpose["required_next_runtime_gate"],
    }
    return {
        "w66_blocker": {
            "lane_id": BASE_LANE_ID,
            "result": "blocked_base_lane_final_certification_robustness_pair_failed",
            "final_decision": "blocked",
            "closes_work_order": False,
            "final_lane_certification": False,
        },
        "w70_done": {
            "lane_id": OPENPOSE_LANE_ID,
            "remediates_lane_id": BASE_LANE_ID,
            "result": "done_bounded_local_openpose_composition_remediation_pair_pass_with_notes",
            "closes_local_scope_item": True,
            "implementation_test_qa_evidence_complete": True,
            "closes_base_final_lane_work_order": False,
            "closes_openpose_final_lane_work_order": False,
            "final_base_lane_certification": False,
            "final_openpose_lane_certification": False,
            "full_project_certification": False,
        },
        "w70_qa": {
            "lane_id": OPENPOSE_LANE_ID,
            "remediates_lane_id": BASE_LANE_ID,
            "technical_pass": True,
            "strict_visual_disposition": {
                "contract_valid": True,
                "all_samples_pass": True,
            },
            "records": [
                {"checks": {name: True for name in REQUIRED_QA_RECORD_CHECKS}},
                {"checks": {name: True for name in REQUIRED_QA_RECORD_CHECKS}},
            ],
            "strict_decision": {
                "bounded_sample_count": 2,
                "materially_different_composition_control_available": True,
                "base_canonical_robustness_failure_cleared": False,
                "base_final_certification_allowed": False,
                "openpose_final_certification_allowed": False,
                "target_runtime_proof_added": False,
            },
            "boundaries": {
                "local_only": True,
                "aws_contacted": False,
                "ec2_started": False,
                "gold_masks_consumed": False,
                "mask_promotion_performed": False,
                "wave70_hard_gate_rerun": False,
                "wave71_activated": False,
            },
        },
        "queue_manifest": {
            "lanes": [queue_base, queue_openpose],
            "runtime_boundary": {"generation_allowed_by_queue_file": False},
        },
        "active_manifest": {"lanes": [active_base, active_openpose]},
    }


class EvaluateBaseOpenPoseOwnershipTests(unittest.TestCase):
    def test_pass_case(self) -> None:
        payloads = valid_payloads()
        result = evaluate_payloads(**payloads)
        self.assertTrue(result["pass"])

    def test_lane_ownership_mismatch_fails(self) -> None:
        payloads = valid_payloads()
        payloads["w70_done"]["lane_id"] = BASE_LANE_ID
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_accidental_final_certification_fails(self) -> None:
        payloads = valid_payloads()
        payloads["w70_done"]["final_base_lane_certification"] = True
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_missing_target_runtime_boundary_fails(self) -> None:
        payloads = valid_payloads()
        payloads["w70_qa"]["strict_decision"]["target_runtime_proof_added"] = True
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_queue_active_mismatch_fails(self) -> None:
        payloads = valid_payloads()
        payloads["active_manifest"]["lanes"][0]["next_gate"] = "wrong_gate"
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_gold_mask_consumption_fails(self) -> None:
        payloads = valid_payloads()
        payloads["w70_qa"]["boundaries"]["gold_masks_consumed"] = True
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_missing_required_qa_record_check_fails(self) -> None:
        payloads = valid_payloads()
        payloads["w70_qa"]["records"][0]["checks"].pop("control_image_bound")
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_active_lane_identity_mismatch_fails(self) -> None:
        payloads = valid_payloads()
        payloads["active_manifest"]["lanes"][0]["lane_id"] = "wrong_lane"
        result = evaluate_payloads(**payloads)
        self.assertFalse(result["pass"])

    def test_semantically_equivalent_policy_wording_passes(self) -> None:
        payloads = valid_payloads()
        queue_base = payloads["queue_manifest"]["lanes"][0]
        queue_base["status"] = (
            "final certification blocked: canonical two-character robustness failed; "
            "OpenPose remediation passed"
        )
        queue_base["required_next_runtime_gate"] = (
            "Explicit review and scope-matched target-runtime proof before Base-owned "
            "composition route adoption"
        )
        queue_base["promotion_rule"] = (
            "Keep cross-lane OpenPose remediation evidence separate from Base ownership; "
            "scope-matched target-runtime proof and final review remain required."
        )
        active_base = payloads["active_manifest"]["lanes"][0]
        active_base["status"] = queue_base["status"]
        active_base["next_gate"] = queue_base["required_next_runtime_gate"]
        result = evaluate_payloads(**payloads)
        self.assertTrue(result["pass"])


if __name__ == "__main__":
    unittest.main()
