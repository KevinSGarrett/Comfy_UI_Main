#!/usr/bin/env python3
"""Record strict QA for the bounded Base two-character robustness pair."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
STAMP = "20260711T035500-0500"
BASELINE = ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_two_character_hand_to_body_w69_seed7152026252_20260707T113434-0500/images/codex_realvisxl_two_character_hand_to_body_seed7152026252_00001_.png"
SOURCE_PROFILE = ROOT / "PromptProfiles/base_generation/realvisxl_multisample_certification/realvisxl_two_character_hand_to_body_seed7152026252_source_hand_visible.json"
RUNS = {
    "7152026253": {
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_BASE_TWO_CHARACTER_CONTACT_ROBUSTNESS_SEED7152026253_20260711T035000-0500.json",
        "image": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_two_character_contact_robustness_seed7152026253_20260711T034617-0500/images/rvxl_twochar_contact_robust_7152026253_00001_.png",
        "profile": ROOT / "PromptProfiles/base_generation/realvisxl_multisample_certification/realvisxl_two_character_hand_to_body_robustness_seed7152026253.json",
        "visual_result": "fail_wrong_interaction_mutual_hand_clasp",
        "findings": [
            "Exactly two distinct clothed adults are present with coherent faces, bodies, and clothing.",
            "The requested woman-to-man upper-arm contact is absent.",
            "Both subjects clasp hands near the center; the man directly participates in the contact.",
            "The woman's open right hand does not rest on the man's upper-arm sleeve.",
            "An additional pointing hand is visible from the man, further violating the hands-down contract.",
        ],
    },
    "7152026254": {
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_BASE_TWO_CHARACTER_CONTACT_ROBUSTNESS_SEED7152026254_20260711T035000-0500.json",
        "image": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_two_character_contact_robustness_seed7152026254_20260711T034707-0500/images/rvxl_twochar_contact_robust_7152026254_00001_.png",
        "profile": ROOT / "PromptProfiles/base_generation/realvisxl_multisample_certification/realvisxl_two_character_hand_to_body_robustness_seed7152026254.json",
        "visual_result": "fail_wrong_interaction_handshake_clasp",
        "findings": [
            "Exactly two distinct clothed adults are present with coherent faces, bodies, and clothing.",
            "The requested woman-to-man upper-arm contact is absent.",
            "The subjects form a mutual handshake or arm-wrestling-style clasp at center frame.",
            "The man directly owns one side of the contact instead of keeping both hands away.",
            "No open woman's hand rests flat on the man's upper-arm sleeve.",
        ],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    required = [BASELINE, SOURCE_PROFILE]
    for run in RUNS.values():
        required.extend([run["runtime"], run["image"], run["profile"]])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required robustness QA input missing: {missing}")

    source_profile = json.loads(SOURCE_PROFILE.read_text(encoding="utf-8"))
    source_patch = source_profile["request_patch_values"]
    samples = []
    technical_checks = []
    for seed, run in RUNS.items():
        runtime = json.loads(run["runtime"].read_text(encoding="utf-8"))
        profile = json.loads(run["profile"].read_text(encoding="utf-8"))
        profile_patch = profile["request_patch_values"]
        with Image.open(run["image"]) as image:
            width, height = image.size
        checks = {
            "runtime_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
            "generation_executed": runtime.get("generation_executed") is True,
            "request_hash_matched": runtime.get("run_package", {}).get("prompt_request", {}).get("hash_match") is True,
            "server_stopped": runtime.get("local_comfy", {}).get("stopped_by_helper") is True,
            "port_closed": runtime.get("local_comfy", {}).get("port_closed_after_stop") is True,
            "output_is_1024_square": width == 1024 and height == 1024,
            "positive_prompt_unchanged": profile_patch.get("positive_prompt") == source_patch.get("positive_prompt"),
            "negative_prompt_unchanged": profile_patch.get("negative_prompt") == source_patch.get("negative_prompt"),
            "sampler_settings_unchanged": profile_patch.get("sampler_settings") == source_patch.get("sampler_settings"),
            "latent_resolution_unchanged": profile_patch.get("latent_resolution") == source_patch.get("latent_resolution"),
            "model_asset_unchanged": profile_patch.get("model_asset") == source_patch.get("model_asset"),
            "expected_seed_applied": profile_patch.get("seed") == int(seed),
        }
        technical_checks.extend(f"seed_{seed}:{name}" for name, passed in checks.items() if not passed)
        samples.append(
            {
                "seed": int(seed),
                "profile": rel(run["profile"]),
                "runtime_evidence": rel(run["runtime"]),
                "image": rel(run["image"]),
                "image_sha256": sha256(run["image"]),
                "width": width,
                "height": height,
                "technical_checks": checks,
                "visual_result": run["visual_result"],
                "interaction_contract_pass": False,
                "findings": run["findings"],
            }
        )

    technical_pass = not technical_checks
    robustness_pass_count = sum(1 for sample in samples if sample["interaction_contract_pass"])
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W66-LOCAL-BASE-TWO-CHARACTER-CONTACT-ROBUSTNESS-QA-{STAMP}",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_id": "sdxl_realvisxl_base_lane",
        "result": "fail_local_two_character_contact_robustness_wrong_interaction",
        "technical_runtime_pass": technical_pass,
        "robustness_contract_pass": False,
        "baseline": {
            "seed": 7152026252,
            "image": rel(BASELINE),
            "sha256": sha256(BASELINE),
            "visual_result": "pass_with_notes_correct_source_owner_shoulder_upper_arm_contact",
        },
        "samples": samples,
        "aggregate": {
            "new_samples": 2,
            "technical_runtime_pass_count": 2 if technical_pass else 2 - len(technical_checks),
            "interaction_contract_pass_count": robustness_pass_count,
            "interaction_contract_fail_count": 2 - robustness_pass_count,
            "repeated_failure_mode": "mutual_hand_clasp_or_handshake_instead_of_source_hand_on_target_upper_arm",
        },
        "strict_decision": {
            "stop_seed_loop": True,
            "base_final_certification_allowed": False,
            "small_robustness_pair_requirement_cleared": False,
            "mask_routed_refine_substituted": False,
            "target_runtime_scope_proven": False,
        },
        "known_issue_review": [
            "The corrected prompt is not robust across nearby seeds; both new outputs changed the interaction class.",
            "The images are visually coherent but do not satisfy source/target ownership or target-region placement.",
            "Later inpaint-detail evidence remains owned by the inpaint lane and is not reassigned to Base.",
            "Manual gold masks remain unavailable and were not consumed by this experiment.",
        ],
        "boundaries": {
            "local_only": True,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_route_used": False,
            "mask_promotion_performed": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
        },
        "next_action": "Do not run more adjacent seeds or certify Base. Revisit only with a materially different composition-control route or scope-matched target-runtime proof after its prerequisites are available.",
    }

    qa_path = ROOT / f"Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_BASE_TWO_CHARACTER_CONTACT_ROBUSTNESS_QA_{STAMP}.json"
    tracker_qa_path = ROOT / f"Plan/Tracker/Evidence/Image_Artifact_QA/W66_LOCAL_BASE_TWO_CHARACTER_CONTACT_ROBUSTNESS_QA_{STAMP}.json"
    write_json(qa_path, evidence)
    tracker_qa_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(qa_path, tracker_qa_path)

    item = {
        "item_id": f"ITEM-W66-BASE-TWO-CHARACTER-CONTACT-ROBUSTNESS-{STAMP}",
        "timestamp": evidence["timestamp"],
        "lane_id": evidence["lane_id"],
        "title": "Base lane corrected two-character contact seed robustness pair",
        "status": "implemented_tested_qa_failed_interaction_contract",
        "implementation_complete": True,
        "runtime_test_complete": True,
        "technical_qa_complete": True,
        "visual_qa_complete": True,
        "tracker_update_complete": True,
        "itemized_list_update_complete": True,
        "known_issue_review_complete": True,
        "done_certification_allowed": False,
        "result_summary": "Both new seed-only variants executed cleanly, but 0/2 preserved the corrected woman-to-man upper-arm contact contract.",
        "qa_evidence": rel(qa_path),
        "remaining_blockers": [
            "two_character_multiseed_robustness_missing",
            "scope_matched_target_runtime_candidate_proof_missing",
            "mask_routed_refine_or_materially_different_composition_control_missing",
        ],
    }
    item_path = ROOT / f"Plan/Items/Reports/W66_BASE_TWO_CHARACTER_CONTACT_ROBUSTNESS_ITEMIZED_LIST_{STAMP}.json"
    write_json(item_path, item)

    blocker = {
        "evidence_id": f"W66-BASE-LANE-FINAL-CERTIFICATION-BLOCKER-AFTER-ROBUSTNESS-{STAMP}",
        "timestamp": evidence["timestamp"],
        "task_tracker_id": "WO-W66-SDXL_REALVISXL_BASE_LANE-FINAL-CERTIFICATION",
        "lane_id": evidence["lane_id"],
        "result": "blocked_base_lane_final_certification_robustness_pair_failed",
        "final_decision": "blocked",
        "closes_work_order": False,
        "implementation_summary": "Executed the required bounded seed-only robustness pair from the corrected preferred Base profile. Both runs passed technically; both failed the interaction contract as mutual hand clasps.",
        "qa_evidence": rel(qa_path),
        "itemized_list_record": rel(item_path),
        "exact_blockers": item["remaining_blockers"],
        "known_issues": evidence["known_issue_review"],
        "generation_executed": True,
        "new_ec2_started": False,
        "final_lane_certification": False,
        "full_project_certification": False,
        "certifier": "Codex Desktop autonomous release manager",
        "next_action": evidence["next_action"],
    }
    blocker_path = ROOT / f"Plan/Instructions/QA/Evidence/Done_Certifications/W66_BASE_LANE_FINAL_CERTIFICATION_BLOCKER_AFTER_ROBUSTNESS_{STAMP}.json"
    tracker_blocker_path = ROOT / f"Plan/Tracker/Evidence/Done_Certifications/W66_BASE_LANE_FINAL_CERTIFICATION_BLOCKER_AFTER_ROBUSTNESS_{STAMP}.json"
    write_json(blocker_path, blocker)
    tracker_blocker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(blocker_path, tracker_blocker_path)

    print(json.dumps({"qa": rel(qa_path), "item": rel(item_path), "blocker": rel(blocker_path), "technical_pass": technical_pass, "robustness_pass_count": robustness_pass_count}, indent=2))
    return 0 if technical_pass and robustness_pass_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
