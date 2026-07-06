#!/usr/bin/env python3
"""Compile a Wave10 camera plan from a minimal request.

This script is intentionally local-first and dependency-free. It does not call ComfyUI.
It converts request intent into a structured camera_plan JSON that later workflow
patchers and App Mode surfaces can consume.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


DEFAULTS: Dict[str, Dict[str, str]] = {
    "full_body": {"lens_profile": "classic_35mm", "camera_angle": "eye_level", "depth_profile": "deep_focus", "aspect_ratio": "4:5", "width": "1024", "height": "1280"},
    "half_body": {"lens_profile": "normal_50mm", "camera_angle": "eye_level", "depth_profile": "natural_portrait_dof", "aspect_ratio": "4:5", "width": "1024", "height": "1280"},
    "close_up": {"lens_profile": "portrait_85mm", "camera_angle": "eye_level", "depth_profile": "natural_portrait_dof", "aspect_ratio": "1:1", "width": "1024", "height": "1024"},
    "detail_insert": {"lens_profile": "macro_100mm", "camera_angle": "context_dependent", "depth_profile": "macro_shallow_dof", "aspect_ratio": "1:1", "width": "1024", "height": "1024"},
    "two_shot": {"lens_profile": "classic_35mm", "camera_angle": "three_quarter_front", "depth_profile": "layered_depth", "aspect_ratio": "16:9", "width": "1280", "height": "720"},
    "wide_shot": {"lens_profile": "wide_24mm", "camera_angle": "eye_level", "depth_profile": "deep_focus", "aspect_ratio": "16:9", "width": "1280", "height": "720"},
}


def compile_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    shot_size = request.get("shot_size", "half_body")
    defaults = DEFAULTS.get(shot_size, DEFAULTS["half_body"])
    subjects = request.get("subjects") or [{"subject_id": "primary_subject", "character_id": request.get("character_id", "char_primary")}]
    normalized_subjects = []
    for index, subject in enumerate(subjects, start=1):
        normalized_subjects.append({
            "subject_id": subject.get("subject_id", f"subject_{index}"),
            "character_id": subject.get("character_id", f"char_{index}"),
            "screen_position": subject.get("screen_position", "center" if len(subjects) == 1 else ("left" if index == 1 else "right")),
            "depth_order": int(subject.get("depth_order", 1)),
            "identity_priority": subject.get("identity_priority", "primary"),
            "crop_policy": subject.get("crop_policy", "full_visible" if shot_size == "full_body" else "intentional_partial"),
            "occlusion_allowed": subject.get("occlusion_allowed", "none" if len(subjects) == 1 else "minor"),
            "must_show": subject.get("must_show", ["face", "hands"] if shot_size != "full_body" else ["face", "hands", "feet"]),
            "must_not_merge_with": subject.get("must_not_merge_with", []),
            "scale_anchor": subject.get("scale_anchor", "floor_contact" if shot_size == "full_body" else "identity_reference"),
        })
    plan = {
        "camera_plan_id": request.get("camera_plan_id", f"cam_{shot_size}_auto_v1"),
        "scene_id": request.get("scene_id", "scene_auto"),
        "modality": request.get("modality", "image"),
        "shot_size": shot_size,
        "lens_profile": request.get("lens_profile", defaults["lens_profile"]),
        "camera_angle": request.get("camera_angle", defaults["camera_angle"]),
        "camera_height": request.get("camera_height", "eye"),
        "zoom_level": request.get("zoom_level", "normal"),
        "aspect_ratio": request.get("aspect_ratio", defaults["aspect_ratio"]),
        "resolution": {
            "width": int(request.get("width", defaults["width"])),
            "height": int(request.get("height", defaults["height"])),
        },
        "framing": {
            "composition_preset": request.get("composition_preset", "full_body_catalog" if shot_size == "full_body" else "rule_of_thirds_portrait"),
            "crop_policy": request.get("crop_policy", "blocked_unintentional_crop"),
            "headroom": request.get("headroom", "controlled"),
            "footroom": request.get("footroom", "controlled" if shot_size == "full_body" else "not_applicable"),
            "side_margin": request.get("side_margin", "controlled"),
            "horizon_line": request.get("horizon_line", "stable"),
            "must_not_crop": request.get("must_not_crop", ["head", "hands", "feet"] if shot_size == "full_body" else ["face", "eyes"]),
            "intentional_crop_allowed": bool(request.get("intentional_crop_allowed", shot_size in {"close_up", "detail_insert"})),
        },
        "depth_plan": {
            "depth_profile": request.get("depth_profile", defaults["depth_profile"]),
            "focus_targets": request.get("focus_targets", ["face", "hands"] if shot_size != "detail_insert" else ["detail_target"]),
            "foreground_subjects": request.get("foreground_subjects", []),
            "midground_subjects": request.get("midground_subjects", [s["subject_id"] for s in normalized_subjects]),
            "background_subjects": request.get("background_subjects", ["environment"]),
            "background_blur_strength": float(request.get("background_blur_strength", 0.25)),
            "depth_continuity_notes": request.get("depth_continuity_notes", "Keep required subjects readable and in focus."),
        },
        "subjects": normalized_subjects,
        "workflow_patch_targets": request.get("workflow_patch_targets", ["latent_width_height", "positive_prompt_camera_module", "negative_prompt_crop_guard"]),
        "qa_goals": request.get("qa_goals", ["shot_size_matches_intent", "no_unintentional_crop", "focus_target_sharp"]),
    }
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, help="Path to minimal camera request JSON")
    parser.add_argument("--out", required=True, help="Path to output camera plan JSON")
    args = parser.parse_args()

    request_path = Path(args.request)
    out_path = Path(args.out)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    plan = compile_plan(request)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote camera plan: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
