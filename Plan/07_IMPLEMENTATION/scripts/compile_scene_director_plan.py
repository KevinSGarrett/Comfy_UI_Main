#!/usr/bin/env python3
"""
compile_scene_director_plan.py

Wave07 minimal deterministic Scene Director compiler.

This is intentionally a local/offline stub that converts a request JSON into a
structured plan. A production implementation can replace the heuristic compiler
with an LLM structured-output call, but the output contract should stay the same.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def infer_intent(raw: str, target_output: str) -> Dict[str, Any]:
    text = raw.lower()
    secondary: List[str] = []
    if any(k in text for k in ["full body", "camera", "framing", "angle", "zoom", "crop"]):
        secondary.append("environment_camera_framing")
    if any(k in text for k in ["body", "stomach", "waist", "hips", "thigh", "silhouette", "anatomy"]):
        secondary.append("body_shape_or_anatomy_correction")
    if any(k in text for k in ["contact", "pressure", "indent", "soft", "squeeze", "grab", "ripple", "bounce"]):
        secondary.append("soft_body_contact_deformation")
    if target_output in {"gif", "video"} or any(k in text for k in ["gif", "video", "motion", "frames"]):
        primary = "gif_or_video_scene"
        target = "video" if "video" in text else "gif"
    elif target_output in {"audio", "av_sync"} or any(k in text for k in ["audio", "foley", "voice", "sound"]):
        primary = "audio_or_av_sync"
        target = target_output if target_output != "unknown" else "audio"
    elif any(k in text for k in ["model", "checkpoint", "lora", "civitai"]):
        primary = "model_selection_or_registry_update"
        target = "model_selection"
    else:
        primary = "image_single_hyperreal_character"
        target = "image" if target_output == "unknown" else target_output
    return {
        "primary_intent": primary,
        "secondary_intents": sorted(set(secondary)),
        "target_output": target,
        "confidence": 0.78,
    }


def compile_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    raw = request["raw_user_request"]
    request_id = request["request_id"]
    target_output = request.get("target_output", "unknown")
    intent = infer_intent(raw, target_output)
    full_body = "full body" in raw.lower() or "feet" in raw.lower()

    camera_plan = {
        "camera_id": "cam_auto_001",
        "shot_type": "full_body" if full_body else "medium_full_or_half_body",
        "framing": {
            "body_crop": "head_to_feet_visible" if full_body else "upper_or_full_body_based_on_request",
            "subject_count_visible": 1,
            "safe_margin": "5-8 percent" if full_body else "3-5 percent",
            "full_body_required": bool(full_body),
            "half_body_required": not bool(full_body),
        },
        "lens_look": "natural 35-50mm equivalent",
        "camera_angle": "neutral eye-to-chest height unless request specifies otherwise",
        "camera_height": "waist_to_chest",
        "camera_distance": "match requested crop",
        "zoom_or_focal_length_hint": "avoid extreme distortion",
        "depth_of_field": "moderate",
        "composition_notes": ["preserve requested subject visibility", "keep environment scale plausible"],
        "occlusion_warnings": ["avoid unplanned foreground occlusion"],
        "qa_requirements": ["qa_camera_framing", "qa_scene_intent"],
    }

    mask_plan = [
        {
            "mask_id": "mask_subject_macro",
            "scale": "macro",
            "target_entity_id": "char_001",
            "target_region": "full_subject",
            "purpose": "subject preservation and silhouette QA",
            "feather_px": 16,
            "dilate_px": 4,
            "erode_px": 0,
            "protect_regions": ["background"],
            "qa_overlay_required": True,
        }
    ]
    if any(k in raw.lower() for k in ["skin", "texture", "detail", "cellulite", "fabric"]):
        mask_plan.append({
            "mask_id": "mask_detail_micro",
            "scale": "micro",
            "target_entity_id": "char_001",
            "target_region": "requested_detail_region",
            "purpose": "controlled regional material/detail pass",
            "feather_px": 8,
            "dilate_px": 2,
            "erode_px": 0,
            "protect_regions": ["identity", "background", "hard_edges"],
            "qa_overlay_required": True,
        })
    if "contact" in intent["secondary_intents"] or any(k in raw.lower() for k in ["contact", "pressure", "squeeze", "grab", "indent"]):
        mask_plan.append({
            "mask_id": "mask_contact_zone",
            "scale": "contact",
            "target_entity_id": "char_001",
            "target_region": "requested_contact_target",
            "source_entity_id": "source_001",
            "source_region": "requested_contact_source",
            "contact_zone": "localized_source_target_boundary",
            "purpose": "controlled visual contact/deformation pass",
            "feather_px": 10,
            "dilate_px": 3,
            "erode_px": 0,
            "protect_regions": ["non_contact_background", "identity"],
            "qa_overlay_required": True,
        })

    pass_list = [
        {
            "pass_id": "pass_001_base",
            "pass_type": "base_image_generate",
            "engine_id": "flux2_dev_local",
            "workflow_module_id": "module_base_image_flux2_planned",
            "model_ids": ["flux2_dev_local"],
            "mask_ids": [],
            "inputs": ["scene_graph", "camera_plan", "normalized_request"],
            "outputs": ["base_image", "base_generation_manifest"],
            "qa_goal_ids": ["qa_basic_file", "qa_scene_intent", "qa_camera_framing", "qa_anatomy"],
            "promotion_gate": "required_before_next_pass",
            "runtime_proof_required": True,
            "notes": ["Flux2 is planned/proof-gated; fallback to sdxl_realvisxl if unavailable."],
        }
    ]
    if len(mask_plan) > 1:
        pass_list.append({
            "pass_id": "pass_002_regional_detail",
            "pass_type": "skin_material_microdetail",
            "engine_id": "sdxl_inpaint_detail",
            "workflow_module_id": "module_sdxl_inpaint_detail",
            "model_ids": ["sdxl_realvisxl_lane"],
            "mask_ids": [m["mask_id"] for m in mask_plan if m["scale"] in {"micro", "contact"}],
            "inputs": ["approved_base_image", "mask_plan"],
            "outputs": ["regional_detail_image", "regional_detail_manifest"],
            "qa_goal_ids": ["qa_mask_no_bleed", "qa_anatomy"],
            "promotion_gate": "required_before_release",
            "runtime_proof_required": True,
            "notes": ["Cross-engine bridge is image-file based only."],
        })

    qa_goal_plan = [
        {"qa_goal_id": "qa_basic_file", "scope": "all outputs", "checks": ["file_exists", "decode_ok", "sha256_recorded"], "evidence_required": ["output_manifest.json"], "blocking": True, "promotion_required": True},
        {"qa_goal_id": "qa_scene_intent", "scope": "scene", "checks": ["matches_normalized_request", "no_missing_core_subjects"], "evidence_required": ["qa_scene_report.json"], "blocking": True, "promotion_required": True},
        {"qa_goal_id": "qa_camera_framing", "scope": "camera", "checks": ["crop_matches_plan", "subject_visible"], "evidence_required": ["qa_camera_crop.png"], "blocking": True, "promotion_required": True},
        {"qa_goal_id": "qa_anatomy", "scope": "character", "checks": ["limb_count_ok", "hands_readable", "face_not_melted"], "evidence_required": ["qa_anatomy_report.json"], "blocking": True, "promotion_required": True},
    ]
    if len(mask_plan) > 1:
        qa_goal_plan.append({"qa_goal_id": "qa_mask_no_bleed", "scope": "regional", "checks": ["mask_overlay_saved", "outside_region_unchanged"], "evidence_required": ["mask_overlay.png", "before_after_crop.png"], "blocking": True, "promotion_required": True})

    plan = {
        "plan_id": f"PLAN-{request_id}",
        "request_id": request_id,
        "director_profile_id": request.get("desired_profile_id") or "hyperreal_image_director",
        "raw_user_request": raw,
        "normalized_request": raw.strip(),
        "intent_classification": intent,
        "assumptions": ["Best-effort defaults applied where the request did not specify details."],
        "ambiguity_resolution": {
            "policy": "make_best_effort",
            "assumptions": ["No blocking ambiguity detected by the local stub compiler."],
            "blocking_questions": [],
            "non_blocking_defaults": [{"field": "engine_route.primary_engine_id", "value": "flux2_dev_local proof-gated"}],
            "confidence": 0.76,
        },
        "scene_graph": {
            "scene_id": "scene_auto_001",
            "summary": raw.strip(),
            "characters": [{
                "character_id": "char_001",
                "role": "primary_subject",
                "description": "Primary subject inferred from request.",
                "identity_reference_ids": [],
                "body_targets": [],
                "wardrobe": [],
                "pose": "infer from request or neutral pose",
                "depth_order": 1,
            }],
            "environment": {
                "environment_id": "env_001",
                "description": "Infer realistic environment from request or use neutral studio/interior default.",
                "location_type": "inferred",
                "lighting": "realistic natural/soft lighting",
                "materials": [],
                "scale_constraints": ["maintain plausible scale"],
            },
            "actions": [],
            "props": [],
            "relationships": [],
            "negative_scene_constraints": request.get("negative_constraints", []),
        },
        "camera_plan": camera_plan,
        "mask_plan": mask_plan,
        "model_selection_plan": {
            "selection_id": "modelsel_auto_001",
            "selection_policy": "registry-first; proof-gated; no wrong-engine direct mixing",
            "candidate_models": [
                {"model_id": "flux2_dev_local", "engine_family": "flux2", "asset_type": "checkpoint", "source_registry": "wave06_engine_registry", "civitai_model_id": None, "civitai_version_id": None, "sha256": None, "local_path": None, "s3_uri": None, "allowed_passes": ["base_image_generate"], "selection_status": "needs_runtime_proof", "reason": "planned primary base engine"},
                {"model_id": "sdxl_realvisxl_lane", "engine_family": "sdxl", "asset_type": "checkpoint_lora_stack", "source_registry": "wave42_main_flow_and_civitai_registry", "civitai_model_id": None, "civitai_version_id": None, "sha256": "registry_required", "local_path": "ComfyUI/models", "s3_uri": "s3://canonical-model-bucket/models/sdxl/", "allowed_passes": ["regional_inpaint_detail", "skin_material_microdetail"], "selection_status": "candidate", "reason": "current SDXL ecosystem compatibility"},
            ],
            "blocked_models": [{"reason": "wrong-engine or rejected assets blocked"}],
        },
        "engine_route": {
            "primary_engine_id": "flux2_dev_local",
            "fallback_engine_ids": ["flux1_dev", "sdxl_realvisxl"],
            "routing_reason": "Use planned Flux2 base when proof exists; SDXL for current detail ecosystem.",
            "cross_engine_policy": "image_bridge_only_no_latent_or_lora_mixing",
        },
        "pass_plan": {
            "pass_plan_id": f"PASSPLAN-{request_id}",
            "passes": pass_list,
            "cross_engine_bridges": [{"from_engine": "flux2_dev_local", "to_engine": "sdxl_inpaint_detail", "bridge_type": "approved_image_file", "allowed": True}],
        },
        "qa_goal_plan": qa_goal_plan,
        "promotion_requirements": ["runtime outputs exist", "QA evidence exists", "all blocking QA goals pass"],
        "evidence_requirements": ["scene_director_plan.json", "pass_plan.json", "output_manifest.json", "qa_report.json"],
        "revision_plan": {"state_diff_required": True, "rerun_rules": ["rerun base for camera/subject-count failures", "rerun regional pass for mask failures"]},
    }
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    request = load_json(args.request)
    plan = compile_plan(request)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
