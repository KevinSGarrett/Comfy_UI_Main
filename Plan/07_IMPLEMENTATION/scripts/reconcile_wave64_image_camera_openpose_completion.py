from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image

from compile_camera_plan import compile_plan
from qa_wave10_camera_compiler_runtime import (
    body_points,
    framing_keypoints_in_frame,
    nonblank_metrics,
    validate_visual_disposition,
)


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TRK, ITEM = "TRK-W64-011", "ITEM-W64-011"
STATUS = "Completed_Local_OpenPose_Camera_Composition_Pass_Target_Runtime_Not_Certified"
DECISION = "local_openpose_camera_composition_complete_target_runtime_lane_certification_not_claimed"
LANE = "sdxl_realvisxl_controlnet_openpose_lane"
RUN_ID = "wave10_camera_full_body_openpose_hands_visible_seed7152026103"
EXPECTED_DWPOSE_HASHES = {
    "yolox_l.onnx": "7860ae79de6c89a3c1eb72ae9a2756c0ccfbe04b7791bb5880afabd97855a411",
    "dw-ll_ucoco_384.onnx": "724f4ff2439ed61afb86fb8a1951ec39c6220682803b4a8bd4f598cd913b1843",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def add(current: str, values: list[str]) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def nodes_of_type(graph: dict[str, Any], class_type: str) -> list[dict[str, Any]]:
    return [node for node in graph.values() if isinstance(node, dict) and node.get("class_type") == class_type]


def single_node(graph: dict[str, Any], class_type: str) -> dict[str, Any]:
    nodes = nodes_of_type(graph, class_type)
    if len(nodes) != 1:
        raise ValueError(f"Expected one {class_type}, found {len(nodes)}")
    return nodes[0]


def images_equal(left: Path, right: Path) -> bool:
    with Image.open(left) as left_image, Image.open(right) as right_image:
        left_pixels = np.asarray(left_image.convert("RGB"))
        right_pixels = np.asarray(right_image.convert("RGB"))
    return left_pixels.shape == right_pixels.shape and bool(np.array_equal(left_pixels, right_pixels))


def visible_hand_keypoints(person: dict[str, Any], field: str) -> int:
    values = person.get(field) or []
    return sum(
        1
        for index in range(2, len(values), 3)
        if float(values[index]) > 0.0
    )


def run_test(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    match = re.search(r"Ran (\d+) tests?", output)
    return {
        "path": rel(path),
        "sha256": sha(path),
        "exit_code": completed.returncode,
        "tests_run": int(match.group(1)) if match else 0,
        "passed": completed.returncode == 0 and match is not None,
    }


def rewrite_csv(path: Path, key: str, expected: str, changes: dict[str, object], note: str) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames or [], list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        if "Notes" in fields:
            row["Notes"] = note
        for field, value in changes.items():
            if field in fields:
                row[field] = add(row.get(field, ""), value) if isinstance(value, list) else str(value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matched


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row011 OpenPose Camera Composition Completion"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        existing = current[:next_heading].strip() if next_heading >= 0 else current.strip()
        if existing == block.strip():
            return
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(block.strip() + "\n\n" + current, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    request_path = PLAN / "09_EXAMPLES/wave10_camera_full_body_openpose_hands_visible_runtime_request.example.json"
    plan_path = PLAN / "09_EXAMPLES/wave10_camera_full_body_openpose_hands_visible_compiled.example.json"
    profile_path = ROOT / "PromptProfiles/base_generation/wave10_camera_compiler/wave10_camera_full_body_openpose_hands_visible_seed7152026103.json"
    package_path = ROOT / f"runtime_artifacts/run_packages/{RUN_ID}/RUN_PACKAGE_MANIFEST.json"
    runtime_path = PLAN / "Instructions/QA/Evidence/Workflow_Runtime/W64_LOCAL_WAVE10_CAMERA_OPENPOSE_HANDS_VISIBLE_EXECUTE_20260713T060800-0500.json"
    pullback = PLAN / "Instructions/Operations/Pulled_Back_Artifacts/wave10_camera_openpose_hands_visible_20260713T060800-0500"
    image_path = pullback / "images/wave10_camera_openpose_hands_visible_7152026103_00001_.png"
    diagnostic_path = pullback / "images/codex_sdxl_realvisxl_controlnet_openpose_control_map_diagnostic_00013_.png"
    prep_dir = PLAN / "Instructions/Operations/Prepared_Input_Assets/openpose_full_body_hands_visible_row011_v1"
    prep_path = prep_dir / "PREPARATION_MANIFEST.json"
    control_path = prep_dir / "controlnet_openpose_row011_full_body_hands_visible_v1.png"
    active_input = ROOT / "ComfyUI/input/controlnet_openpose_row011_full_body_hands_visible_v1.png"
    visual_path = PLAN / "Instructions/QA/Evidence/Image_Artifact_QA/W64_WAVE10_CAMERA_OPENPOSE_HANDS_VISIBLE_VISUAL_QA_20260713T061500-0500.json"
    prior_path = QA / "IMAGE_CAMERA_COMPOSITION_RECONCILIATION_20260713T015834-0500.json"
    prior_detail_path = PLAN / "Tracker/Evidence/Wave64/image_camera_composition_retry.json"
    dwpose_dir = Path(r"C:\Comfy_UI_Lora\OpenPose\models\dwpose")
    required = [
        request_path, plan_path, profile_path, package_path, runtime_path, image_path,
        diagnostic_path, prep_path, control_path, active_input, visual_path, prior_path, prior_detail_path,
        *(dwpose_dir / filename for filename in EXPECTED_DWPOSE_HASHES),
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing Row011 completion inputs: " + ", ".join(missing))

    request, plan, profile, package, runtime, prep, visual, prior, prior_detail = map(
        load,
        (request_path, plan_path, profile_path, package_path, runtime_path, prep_path, visual_path, prior_path, prior_detail_path),
    )
    prior_plan_path = ROOT / prior_detail["compiler"]["plan"]
    if not prior_plan_path.is_file():
        raise SystemExit(f"Prior Row011 compiled plan missing: {prior_plan_path}")
    prior_plan = load(prior_plan_path)
    recompiled_plan = compile_plan(request)
    prompt_record = next(
        record for record in package["generated_files"] if str(record.get("path", "")).endswith("/prompt_request.json")
    )
    prompt_path = ROOT / prompt_record["path"]
    prompt_request = load(prompt_path)
    graph = prompt_request.get("prompt")
    if not isinstance(graph, dict):
        raise SystemExit("Packaged prompt graph missing")

    patch = profile["request_patch_values"]
    sampler = single_node(graph, "KSampler")["inputs"]
    latent = single_node(graph, "EmptyLatentImage")["inputs"]
    checkpoint = single_node(graph, "CheckpointLoaderSimple")["inputs"]
    controlnet = single_node(graph, "ControlNetLoader")["inputs"]
    load_image = single_node(graph, "LoadImage")["inputs"]
    apply_control = single_node(graph, "ControlNetApplyAdvanced")["inputs"]
    prompt_texts = {node["inputs"].get("text") for node in nodes_of_type(graph, "CLIPTextEncode")}
    save_nodes = nodes_of_type(graph, "SaveImage")
    output_save = [node for node in save_nodes if node["inputs"].get("filename_prefix") == patch["save_prefix"]]

    target_records = [
        record for record in runtime.get("pulled_artifacts", [])
        if record.get("local_path") == rel(image_path)
    ]
    diagnostic_records = [
        record for record in runtime.get("pulled_artifacts", [])
        if record.get("local_path") == rel(diagnostic_path)
    ]
    with Image.open(image_path) as loaded:
        image = loaded.convert("RGB")
        dimensions = image.size
    image_metrics = nonblank_metrics(image)

    aux_src = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    detector = DwposeDetector(
        Wholebody(
            str(dwpose_dir / "yolox_l.onnx"),
            str(dwpose_dir / "dw-ll_ucoco_384.onnx"),
            torchscript_device="cpu",
        )
    )
    _, generated_keypoints = detector(
        np.asarray(image),
        detect_resolution=768,
        include_body=True,
        include_hand=True,
        include_face=True,
        output_type="pil",
        image_and_json=True,
    )
    keypoints_path = pullback / "qa_openpose_keypoints.json"
    write(keypoints_path, generated_keypoints)
    points = body_points(generated_keypoints)
    generated_people = generated_keypoints.get("people") or []
    generated_person = generated_people[0] if len(generated_people) == 1 else {}
    hand_keypoint_counts = {
        "left": visible_hand_keypoints(generated_person, "hand_left_keypoints_2d"),
        "right": visible_hand_keypoints(generated_person, "hand_right_keypoints_2d"),
    }

    tests = [
        run_test(PLAN / "Instructions/QA/Scripts/test_compile_camera_plan.py"),
        run_test(PLAN / "Instructions/QA/Scripts/test_qa_wave10_camera_compiler_runtime.py"),
    ]
    visual_contract_valid, visual_pass, visual_issues = validate_visual_disposition(visual, sha(image_path))
    control_plan = plan["workflow_instructions"]["control_plan"]
    checks = {
        "ICOC-001_prior_prompt_only_failure_preserved": prior.get("status") == "Blocked_Visual_Runtime_Composition_Mismatch",
        "ICOC-002_materially_different_openpose_objective": (
            prior_detail.get("lane_id") == "sdxl_realvisxl_base_lane"
            and prior_plan.get("workflow_instructions", {}).get("control_plan", {}).get("enabled") is False
            and prior_detail.get("expected_runtime_bindings", {}).get("seed") != patch["seed"]
            and package.get("lane_id") == LANE
            and control_plan.get("enabled") is True
        ),
        "ICOC-003_request_recompiles_exactly": recompiled_plan == plan,
        "ICOC-004_compiled_plan_is_full_body": plan.get("shot_size") == "full_body" and plan.get("resolution") == {"width": 768, "height": 1024},
        "ICOC-005_control_plan_hash_bound": control_plan.get("enabled") is True and control_plan.get("proof_status") == "proven" and control_plan.get("control_image_sha256") == sha(control_path),
        "ICOC-006_preparation_passed": prep.get("pass") is True and prep.get("detections", {}).get("person_count") == 1 and prep.get("detections", {}).get("visible_body_keypoint_counts") == [18],
        "ICOC-007_excluded_folder_not_used": prep.get("checks", {}).get("source_is_outside_excluded_new_folder") is True and "new folder" not in prep.get("source", {}).get("path", "").lower(),
        "ICOC-008_gold_masks_not_consumed": prep.get("checks", {}).get("gold_masks_not_consumed") is True,
        "ICOC-009_dwpose_models_hash_match": all(sha(dwpose_dir / name) == expected for name, expected in EXPECTED_DWPOSE_HASHES.items()),
        "ICOC-010_active_control_input_hash_matches": sha(active_input) == sha(control_path),
        "ICOC-011_package_passes_local_only": package.get("result") == "pass_local_only" and package.get("run_id") == RUN_ID,
        "ICOC-012_package_profile_exact": package.get("prompt_profile", {}).get("applied") is True and package.get("prompt_profile", {}).get("path") == rel(profile_path),
        "ICOC-013_package_prompt_hash_matches": sha(prompt_path) == package.get("prompt_request", {}).get("sha256") == prompt_record.get("sha256"),
        "ICOC-014_prompt_pair_bound": patch.get("positive_prompt") in prompt_texts and patch.get("negative_prompt") in prompt_texts,
        "ICOC-015_sampler_bound": all(sampler.get(name) == value for name, value in patch["sampler_settings"].items()) and sampler.get("seed") == patch.get("seed"),
        "ICOC-016_resolution_bound": all(latent.get(name) == value for name, value in patch["latent_resolution"].items()),
        "ICOC-017_model_and_controlnet_bound": checkpoint.get("ckpt_name") == patch.get("model_asset") and controlnet.get("control_net_name") == patch.get("controlnet_asset"),
        "ICOC-018_control_image_bound": load_image.get("image") == patch.get("control_image"),
        "ICOC-019_control_settings_bound": all(apply_control.get(name) == value for name, value in patch["controlnet_settings"].items()),
        "ICOC-020_output_prefix_bound": len(output_save) == 1,
        "ICOC-021_runtime_passed": runtime.get("result") == "pass_local_run_package_generation_smoke" and runtime.get("generation_executed") is True,
        "ICOC-022_runtime_request_hash_matches": runtime.get("run_package", {}).get("prompt_request", {}).get("actual_sha256") == package.get("prompt_request", {}).get("sha256"),
        "ICOC-023_runtime_local_and_aws_free": runtime.get("local_only") is True and runtime.get("aws_contacted") is False and runtime.get("ec2_started") is False,
        "ICOC-024_runtime_server_stopped": runtime.get("local_comfy", {}).get("stopped_by_helper") is True and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True,
        "ICOC-025_target_output_hash_bound": len(target_records) == 1 and target_records[0].get("sha256") == sha(image_path),
        "ICOC-026_control_diagnostic_present": len(diagnostic_records) == 1 and diagnostic_records[0].get("sha256") == sha(diagnostic_path),
        "ICOC-027_control_diagnostic_pixels_match": images_equal(control_path, diagnostic_path),
        "ICOC-028_output_dimensions_and_pixels_pass": dimensions == (768, 1024) and image_metrics.get("pass") is True,
        "ICOC-029_generated_person_and_landmarks_pass": len(generated_people) == 1 and len(points) == 18 and framing_keypoints_in_frame(points),
        "ICOC-030_visual_contract_passes": visual_contract_valid and visual_pass and not visual_issues,
        "ICOC-031_unit_tests_pass": all(test["passed"] for test in tests) and sum(test["tests_run"] for test in tests) >= 20,
        "ICOC-032_no_lane_or_mask_overclaim": visual.get("limitations", [None, None])[1].startswith("This local image does not certify") and visual.get("safety_boundary", {}).get("gold_masks_consumed") is False,
        "ICOC-033_bilateral_hand_keypoints_visible": hand_keypoint_counts == {"left": 21, "right": 21},
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("Failed Row011 OpenPose completion checks: " + ", ".join(failed))

    canonical = QA / "image_camera_composition.json"
    refresh_basis = {
        rel(path): sha(path)
        for path in (
            request_path, plan_path, profile_path, package_path, runtime_path,
            image_path, diagnostic_path, prep_path, control_path, visual_path,
            prior_path, prior_detail_path, prior_plan_path,
        )
    }
    current = load(canonical) if canonical.is_file() else {}
    if (
        current.get("artifact_type") == "wave64_image_camera_composition_openpose_completion"
        and current.get("refresh_basis", refresh_basis) == refresh_basis
    ):
        iso = current["created_iso"]
        stamp = current["evidence_id"].removeprefix("IMAGE_CAMERA_COMPOSITION_OPENPOSE_COMPLETION_")
    else:
        now = datetime.now(ZoneInfo("America/Chicago"))
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")
    stamped = QA / f"IMAGE_CAMERA_COMPOSITION_OPENPOSE_COMPLETION_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "image_camera_composition_openpose_completion_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-011_image_camera_composition_openpose_completion.json"
    evidence_paths = [rel(path) for path in (canonical, stamped, mirror, test_log, report, runtime_path, visual_path, prep_path)]
    payload = {
        "schema_version": "1.0",
        "artifact_type": "wave64_image_camera_composition_openpose_completion",
        "evidence_id": stamped.stem,
        "created_iso": iso,
        "refresh_basis": refresh_basis,
        "wave": 64,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": True,
        "qa_decision": DECISION,
        "scope": "local Row011 camera framing, crop safety, required-region visibility, and strict visual-runtime proof",
        "prior_failure_preserved": {"path": rel(prior_path), "status": prior["status"], "reason": prior["exact_blocker"]},
        "material_change": {
            "from_lane": "sdxl_realvisxl_base_lane",
            "to_lane": LANE,
            "from_control": "prompt_only",
            "to_control": "hash-bound DWPose/OpenPoseXL2",
            "source_original": prep["source"],
        },
        "compiler": {
            "request": rel(request_path),
            "request_sha256": sha(request_path),
            "plan": rel(plan_path),
            "plan_sha256": sha(plan_path),
            "canonical_plan_sha256": canonical_sha(plan),
            "profile": rel(profile_path),
            "profile_sha256": sha(profile_path),
        },
        "runtime": {
            "package": rel(package_path),
            "package_sha256": sha(package_path),
            "prompt_request": rel(prompt_path),
            "prompt_request_sha256": sha(prompt_path),
            "execution_evidence": rel(runtime_path),
            "execution_evidence_sha256": sha(runtime_path),
            "image": rel(image_path),
            "image_sha256": sha(image_path),
            "control_diagnostic": rel(diagnostic_path),
            "control_diagnostic_sha256": sha(diagnostic_path),
            "dimensions": {"width": dimensions[0], "height": dimensions[1]},
            "nonblank_metrics": image_metrics,
        },
        "dwpose": {
            "source_preparation": rel(prep_path),
            "source_preparation_sha256": sha(prep_path),
            "control_map": rel(control_path),
            "control_map_sha256": sha(control_path),
            "generated_keypoints": rel(keypoints_path),
            "generated_keypoints_sha256": sha(keypoints_path),
            "generated_person_count": len(generated_keypoints.get("people") or []),
            "generated_body_landmark_count": len(points),
            "generated_visible_hand_keypoint_counts": hand_keypoint_counts,
        },
        "validation_gates": {
            "camera_spec_check": "pass_compiler_and_hash_bound_control",
            "crop_boundary_check": "pass_head_hair_hands_feet_visible",
            "composition_score": {"status": "pass", "score": 100},
            "visual_runtime_ready": "pass_local_strict_visual_review",
        },
        "codex_visual_review": {
            "path": rel(visual_path),
            "sha256": sha(visual_path),
            "result": visual["result"],
            "findings": visual["findings"],
            "limitations": visual["limitations"],
        },
        "unit_tests": tests,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "safety_boundary": {
            "local_generation_count": 1,
            "aws_contacted": False,
            "ec2_started": False,
            "s3_mutated": False,
            "gold_or_candidate_masks_consumed": False,
            "masks_promoted": False,
            "wave70_hard_gates_rerun": False,
            "wave71_plus_activated": False,
            "jira_mutated": False,
            "target_runtime_lane_certification_claimed": False,
            "body_or_finger_geometry_authority_claimed": False,
        },
        "project_completion": {"full_project_complete": False, "final_certification_decision": "blocked"},
        "next_action": "Preserve completed Row011 local camera-composition proof. Keep Row012 blocked on manual gold masks and continue the next eligible non-mask implementation/runtime task without treating this image as mask or geometry authority.",
        "evidence_paths": evidence_paths,
    }
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(
        test_log,
        {
            "schema_version": "1.0",
            "created_iso": iso,
            "tracker_id": TRK,
            "result": "pass_local_openpose_camera_composition_completion",
            "unit_tests": tests,
            "checks": payload["checks"],
            "summary": payload["check_summary"],
        },
    )
    write(
        report,
        {
            "schema_version": "1.0",
            "created_iso": iso,
            "tracker_id": TRK,
            "item_id": ITEM,
            "status": STATUS,
            "row_complete": True,
            "material_change": payload["material_change"],
            "validation_gates": payload["validation_gates"],
            "codex_visual_review": payload["codex_visual_review"],
            "claim_boundary": payload["safety_boundary"],
            "evidence": evidence_paths,
            "next_action": payload["next_action"],
        },
    )

    note = (
        f"Wave64 Row011 {stamp}: materially different hash-bound DWPose/OpenPoseXL2 local runtime closes the prior "
        f"hands-in-pockets camera blocker; both hands, head/hair, and feet pass strict visual review; {len(checks)}/{len(checks)} "
        "checks pass; target-runtime OpenPose lane certification and geometry/mask authority remain unclaimed."
    )
    tags = [
        "wave64_row011_local_openpose_camera_complete",
        "crop_visibility_pass",
        "visual_runtime_pass_local",
        "target_runtime_lane_certification_not_claimed",
        "row012_gold_mask_blocker_preserved",
    ]
    tracker_paths = (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    )
    item_paths = (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    )
    tracker_changes = [
        rewrite_csv(
            path,
            "Tracker_ID",
            TRK,
            {"Status": STATUS, "Status_Decision": DECISION, "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags},
            note,
        )
        for path in tracker_paths
    ]
    item_changes = [
        rewrite_csv(
            path,
            "Item_ID",
            ITEM,
            {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags},
            note,
        )
        for path in item_paths
    ]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"Row011 CSV update mismatch: {tracker_changes} {item_changes}")

    block = f"""## Wave64 Row011 OpenPose Camera Composition Completion - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. A materially different local DWPose/OpenPoseXL2 objective uses the user-supplied true full-body reference `Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg`, outside the excluded partial-body folder. The hash-bound control map detects one person with all 18 body landmarks and both hand skeletons. One bounded local ComfyUI sample passes request/package/runtime hashes, 768x1024 framing, full head/hair, both fully visible hands, both feet, balanced margins, coherent whole-image anatomy, and no control-map leakage. The prior prompt-only hands-in-pockets failure remains historical evidence. This closes Row011 local camera composition only; it does not certify the OpenPose lane in target runtime or claim body, finger, mask, Wave70, or Wave71+ authority. AWS and EC2 were not used.

Next safe action: preserve Row012's manual-gold-mask blocker and continue the next eligible non-mask implementation/runtime task.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in (
        "NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md",
        "BLOCKERS.md", "KNOWN_ISSUES.md",
    ):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof.open("r", encoding="utf-8-sig", newline="") as handle:
        recorded = any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(stamped) for row in csv.DictReader(handle))
    if not recorded:
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow(
                [iso, "64", TRK, "Closed the local camera-composition blocker with a materially different OpenPose-controlled runtime sample.",
                 "; ".join(evidence_paths), f"{len(checks)}/{len(checks)} checks; local runtime and strict visual QA pass",
                 DECISION, rel(stamped), payload["next_action"]]
            )
    print(json.dumps({"status": STATUS, "row_complete": True, "checks": payload["check_summary"], "next": payload["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
