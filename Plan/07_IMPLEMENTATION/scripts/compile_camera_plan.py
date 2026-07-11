#!/usr/bin/env python3
"""Compile a Wave10 still-image camera plan and optional workflow prompt profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULTS: Dict[str, Dict[str, Any]] = {
    "full_body": {
        "lens_profile": "classic_35mm",
        "camera_angle": "eye_level",
        "depth_profile": "deep_focus",
        "aspect_ratio": "4:5",
        "width": 1024,
        "height": 1280,
    },
    "three_quarter_body": {
        "lens_profile": "normal_50mm",
        "camera_angle": "eye_level",
        "depth_profile": "natural_portrait_dof",
        "aspect_ratio": "4:5",
        "width": 1024,
        "height": 1280,
    },
    "half_body": {
        "lens_profile": "normal_50mm",
        "camera_angle": "eye_level",
        "depth_profile": "natural_portrait_dof",
        "aspect_ratio": "4:5",
        "width": 1024,
        "height": 1280,
    },
    "medium_shot": {
        "lens_profile": "normal_50mm",
        "camera_angle": "eye_level",
        "depth_profile": "natural_portrait_dof",
        "aspect_ratio": "4:5",
        "width": 1024,
        "height": 1280,
    },
    "close_up": {
        "lens_profile": "portrait_85mm",
        "camera_angle": "eye_level",
        "depth_profile": "natural_portrait_dof",
        "aspect_ratio": "1:1",
        "width": 1024,
        "height": 1024,
    },
    "extreme_close_up": {
        "lens_profile": "macro_100mm",
        "camera_angle": "eye_level",
        "depth_profile": "macro_shallow_dof",
        "aspect_ratio": "1:1",
        "width": 1024,
        "height": 1024,
    },
    "detail_insert": {
        "lens_profile": "macro_100mm",
        "camera_angle": "eye_level",
        "depth_profile": "macro_shallow_dof",
        "aspect_ratio": "1:1",
        "width": 1024,
        "height": 1024,
    },
    "two_shot": {
        "lens_profile": "classic_35mm",
        "camera_angle": "three_quarter_front",
        "depth_profile": "layered_depth",
        "aspect_ratio": "16:9",
        "width": 1280,
        "height": 720,
    },
    "group_shot": {
        "lens_profile": "wide_24mm",
        "camera_angle": "eye_level",
        "depth_profile": "deep_focus",
        "aspect_ratio": "16:9",
        "width": 1280,
        "height": 720,
    },
    "wide_shot": {
        "lens_profile": "wide_24mm",
        "camera_angle": "eye_level",
        "depth_profile": "deep_focus",
        "aspect_ratio": "16:9",
        "width": 1280,
        "height": 720,
    },
}

ALLOWED_SHOT_SIZES = frozenset(DEFAULTS)
ALLOWED_LENS_PROFILES = frozenset(
    {
        "ultra_wide_18mm",
        "wide_24mm",
        "classic_35mm",
        "normal_50mm",
        "portrait_85mm",
        "macro_100mm",
        "telephoto_135mm",
        "telephoto_200mm",
    }
)
ALLOWED_CAMERA_ANGLES = frozenset(
    {
        "eye_level",
        "low_angle",
        "high_angle",
        "overhead",
        "worm_eye",
        "three_quarter_front",
        "profile_side",
        "back_view",
        "over_shoulder",
        "dutch_angle",
    }
)
ALLOWED_MODALITIES = frozenset({"image", "video", "gif", "audio_visual"})
ALLOWED_SAMPLERS = frozenset(
    {"dpmpp_2m", "dpmpp_2m_sde", "euler", "euler_ancestral", "heun", "uni_pc"}
)
ALLOWED_SCHEDULERS = frozenset({"normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform", "beta"})
FULL_BODY_REQUIRED_CROP_ANCHORS = frozenset({"head", "hands", "feet"})
FULL_BODY_REQUIRED_SUBJECT_ANCHORS = frozenset({"face", "hands", "feet"})
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

SHOT_PROMPTS = {
    "full_body": "full-length composition, entire subject visible from the top of the head through both feet, both hands fully visible",
    "three_quarter_body": "three-quarter body composition with an intentional lower-leg crop",
    "half_body": "half-body portrait with an intentional crop below the waist",
    "medium_shot": "medium shot with the face, torso, and hands readable",
    "close_up": "close-up portrait with the full face and identity anchors visible",
    "extreme_close_up": "extreme close-up with the requested detail centered and readable",
    "detail_insert": "detail insert with enough surrounding context to identify the location",
    "two_shot": "balanced two-subject composition with separated silhouettes",
    "group_shot": "wide group composition with every requested subject readable",
    "wide_shot": "wide establishing composition with environment scale visible",
}
LENS_PROMPTS = {
    "ultra_wide_18mm": "18mm ultra-wide lens perspective",
    "wide_24mm": "24mm wide lens perspective",
    "classic_35mm": "35mm natural environmental lens perspective",
    "normal_50mm": "50mm neutral lens perspective",
    "portrait_85mm": "85mm portrait lens perspective",
    "macro_100mm": "100mm macro lens perspective",
    "telephoto_135mm": "135mm compressed telephoto perspective",
    "telephoto_200mm": "200mm long-lens perspective",
}
ANGLE_PROMPTS = {
    "eye_level": "eye-level camera",
    "low_angle": "low-angle camera looking upward",
    "high_angle": "high-angle camera looking downward",
    "overhead": "overhead top-down camera",
    "worm_eye": "floor-level worm's-eye camera",
    "three_quarter_front": "front three-quarter camera angle",
    "profile_side": "side-profile camera angle",
    "back_view": "back-view camera angle",
    "over_shoulder": "over-the-shoulder camera angle",
    "dutch_angle": "intentional Dutch camera angle",
}


def _require_dict(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}_must_be_an_object")
    return value


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_must_be_a_nonempty_string")
    return value.strip()


def _parse_dimension(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field}_must_be_an_integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}_must_be_an_integer") from exc
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{field}_must_be_an_integer")
    if isinstance(value, str) and str(parsed) != value.strip():
        raise ValueError(f"{field}_must_be_an_integer")
    if not 512 <= parsed <= 2048:
        raise ValueError(f"{field}_must_be_between_512_and_2048")
    if parsed % 64:
        raise ValueError(f"{field}_must_be_divisible_by_64")
    return parsed


def _parse_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field}_must_be_an_integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}_must_be_an_integer") from exc
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        raise ValueError(f"{field}_must_be_an_integer")
    if isinstance(value, str) and str(parsed) != value.strip():
        raise ValueError(f"{field}_must_be_an_integer")
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field}_must_be_between_{minimum}_and_{maximum}")
    return parsed


def _parse_float(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field}_must_be_numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}_must_be_numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field}_must_be_finite")
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field}_must_be_between_{minimum}_and_{maximum}")
    return parsed


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}_must_be_a_nonempty_string_array")
    normalized = []
    for item in value:
        normalized.append(_require_string(item, field))
    return normalized


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.-")
    if not slug:
        raise ValueError("save_prefix_must_contain_safe_characters")
    return slug[:160]


def _require_sha256(value: Any, field: str) -> str:
    digest = _require_string(value, field).lower()
    if not SHA256_RE.fullmatch(digest):
        raise ValueError(f"{field}_must_be_sha256")
    return digest


def _compile_reference_route(request: Dict[str, Any]) -> Dict[str, Any]:
    raw = request.get("reference_route")
    if raw is None:
        return {"enabled": False, "route_id": "none", "proof_status": "not_requested", "asset": None, "asset_sha256": None}
    route = _require_dict(raw, "reference_route")
    enabled = route.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("reference_route.enabled_must_be_boolean")
    if not enabled:
        if route.get("proof_status") == "proven" or route.get("asset") or route.get("asset_sha256"):
            raise ValueError("reference_route_disabled_but_claimed")
        return {"enabled": False, "route_id": "none", "proof_status": "not_requested", "asset": None, "asset_sha256": None}
    if route.get("proof_status") != "proven":
        raise ValueError("reference_route_requires_explicit_proven_status")
    return {
        "enabled": True,
        "route_id": _require_string(route.get("route_id"), "reference_route.route_id"),
        "proof_status": "proven",
        "asset": _require_string(route.get("asset"), "reference_route.asset"),
        "asset_sha256": _require_sha256(route.get("asset_sha256"), "reference_route.asset_sha256"),
    }


def _compile_control_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    raw = request.get("control_plan")
    if raw is None:
        return {
            "enabled": False,
            "route_id": "none",
            "proof_status": "not_requested",
            "target_lane_id": None,
            "controlnet_asset": None,
            "controlnet_asset_sha256": None,
            "control_image": None,
            "control_image_sha256": None,
            "settings": None,
        }
    control = _require_dict(raw, "control_plan")
    enabled = control.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("control_plan.enabled_must_be_boolean")
    if not enabled:
        claimed = any(
            control.get(field)
            for field in ("controlnet_asset", "controlnet_asset_sha256", "control_image", "control_image_sha256")
        )
        if control.get("proof_status") == "proven" or claimed:
            raise ValueError("control_plan_disabled_but_claimed")
        return {
            "enabled": False,
            "route_id": "none",
            "proof_status": "not_requested",
            "target_lane_id": None,
            "controlnet_asset": None,
            "controlnet_asset_sha256": None,
            "control_image": None,
            "control_image_sha256": None,
            "settings": None,
        }
    if control.get("proof_status") != "proven":
        raise ValueError("control_plan_requires_explicit_proven_status")
    settings = _require_dict(control.get("settings"), "control_plan.settings")
    start_percent = _parse_float(settings.get("start_percent"), "control_plan.settings.start_percent", 0.0, 1.0)
    end_percent = _parse_float(settings.get("end_percent"), "control_plan.settings.end_percent", 0.0, 1.0)
    if start_percent >= end_percent:
        raise ValueError("control_plan_start_percent_must_be_less_than_end_percent")
    return {
        "enabled": True,
        "route_id": _require_string(control.get("route_id"), "control_plan.route_id"),
        "proof_status": "proven",
        "target_lane_id": _require_string(control.get("target_lane_id"), "control_plan.target_lane_id"),
        "controlnet_asset": _require_string(control.get("controlnet_asset"), "control_plan.controlnet_asset"),
        "controlnet_asset_sha256": _require_sha256(
            control.get("controlnet_asset_sha256"), "control_plan.controlnet_asset_sha256"
        ),
        "control_image": _require_string(control.get("control_image"), "control_plan.control_image"),
        "control_image_sha256": _require_sha256(
            control.get("control_image_sha256"), "control_plan.control_image_sha256"
        ),
        "settings": {
            "strength": _parse_float(settings.get("strength"), "control_plan.settings.strength", 0.01, 2.0),
            "start_percent": start_percent,
            "end_percent": end_percent,
        },
    }


def _positive_camera_module(plan: Dict[str, Any]) -> str:
    framing = plan["framing"]
    depth = plan["depth_plan"]
    parts = [
        SHOT_PROMPTS[plan["shot_size"]],
        LENS_PROMPTS[plan["lens_profile"]],
        ANGLE_PROMPTS[plan["camera_angle"]],
        f"{framing['composition_preset'].replace('_', ' ')} composition",
        f"{framing['headroom'].replace('_', ' ')} headroom",
        f"{depth['depth_profile'].replace('_', ' ')}",
    ]
    if plan["shot_size"] == "full_body":
        parts.extend(["controlled footroom", "5 to 10 percent margin around the complete silhouette"])
    return ", ".join(_unique(parts))


def _negative_crop_guard(plan: Dict[str, Any]) -> str:
    if plan["shot_size"] == "full_body":
        return (
            "cropped head, cropped hair, cropped hands, cropped fingers, cropped legs, cropped feet, cropped shoes, "
            "cut off body, out-of-frame limbs, partial body, close-up crop, tight framing, hidden hands, hidden feet"
        )
    return "unintentional crop, cut off face, cut off eyes, out-of-frame required subject, composition that hides required evidence"


def compile_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    """Compile a deterministic camera plan while rejecting unsafe or unknown inputs."""
    request = _require_dict(request, "request")
    shot_size = request.get("shot_size", "half_body")
    if shot_size not in ALLOWED_SHOT_SIZES:
        raise ValueError(f"unknown_shot_size:{shot_size}")
    defaults = DEFAULTS[shot_size]

    modality = request.get("modality", "image")
    if modality not in ALLOWED_MODALITIES:
        raise ValueError(f"unknown_modality:{modality}")
    lens_profile = request.get("lens_profile", defaults["lens_profile"])
    if lens_profile not in ALLOWED_LENS_PROFILES:
        raise ValueError(f"unknown_lens_profile:{lens_profile}")
    camera_angle = request.get("camera_angle", defaults["camera_angle"])
    if camera_angle not in ALLOWED_CAMERA_ANGLES:
        raise ValueError(f"unknown_camera_angle:{camera_angle}")

    width = _parse_dimension(request.get("width", defaults["width"]), "width")
    height = _parse_dimension(request.get("height", defaults["height"]), "height")
    subjects_raw = request.get("subjects")
    if subjects_raw is None:
        subjects_raw = [{"subject_id": "primary_subject", "character_id": request.get("character_id", "char_primary")}]
    if not isinstance(subjects_raw, list) or not subjects_raw:
        raise ValueError("subjects_must_be_a_nonempty_array")

    normalized_subjects = []
    for index, subject_raw in enumerate(subjects_raw, start=1):
        subject = _require_dict(subject_raw, f"subjects[{index - 1}]")
        must_show_default = ["face", "hands", "feet"] if shot_size == "full_body" else ["face", "hands"]
        must_show = _string_list(subject.get("must_show", must_show_default), f"subjects[{index - 1}].must_show")
        crop_policy = subject.get("crop_policy", "full_visible" if shot_size == "full_body" else "intentional_partial")
        if shot_size == "full_body":
            if crop_policy != "full_visible":
                raise ValueError(f"subjects[{index - 1}].full_body_crop_policy_must_be_full_visible")
            missing_subject_anchors = FULL_BODY_REQUIRED_SUBJECT_ANCHORS.difference(must_show)
            if missing_subject_anchors:
                raise ValueError(
                    f"subjects[{index - 1}].full_body_must_show_missing:{','.join(sorted(missing_subject_anchors))}"
                )
        normalized_subjects.append(
            {
                "subject_id": subject.get("subject_id", f"subject_{index}"),
                "character_id": subject.get("character_id", f"char_{index}"),
                "screen_position": subject.get(
                    "screen_position", "center" if len(subjects_raw) == 1 else ("left" if index == 1 else "right")
                ),
                "depth_order": _parse_int(subject.get("depth_order", 1), f"subjects[{index - 1}].depth_order", 1, 64),
                "identity_priority": subject.get("identity_priority", "primary"),
                "crop_policy": crop_policy,
                "occlusion_allowed": subject.get("occlusion_allowed", "none" if len(subjects_raw) == 1 else "minor"),
                "must_show": must_show,
                "must_not_merge_with": list(subject.get("must_not_merge_with", [])),
                "scale_anchor": subject.get("scale_anchor", "floor_contact" if shot_size == "full_body" else "identity_reference"),
            }
        )

    default_must_not_crop = ["head", "hands", "feet"] if shot_size == "full_body" else ["face", "eyes"]
    must_not_crop = _string_list(request.get("must_not_crop", default_must_not_crop), "must_not_crop")
    intentional_crop_allowed = request.get("intentional_crop_allowed", shot_size in {"close_up", "detail_insert", "extreme_close_up"})
    if not isinstance(intentional_crop_allowed, bool):
        raise ValueError("intentional_crop_allowed_must_be_boolean")
    if shot_size == "full_body":
        missing_crop_anchors = FULL_BODY_REQUIRED_CROP_ANCHORS.difference(must_not_crop)
        if missing_crop_anchors:
            raise ValueError(f"full_body_must_not_crop_missing:{','.join(sorted(missing_crop_anchors))}")
        if intentional_crop_allowed:
            raise ValueError("full_body_intentional_crop_is_not_allowed")
        if request.get("crop_policy", "blocked_unintentional_crop") not in {"blocked_unintentional_crop", "full_visible"}:
            raise ValueError("full_body_crop_policy_must_block_unintentional_crop")

    required_patch_targets = [
        "latent_width_height",
        "positive_prompt_camera_module",
        "negative_prompt_crop_guard",
        "save_prefix",
    ]
    workflow_patch_targets = _string_list(
        request.get("workflow_patch_targets", required_patch_targets), "workflow_patch_targets"
    )
    missing_patch_targets = set(required_patch_targets).difference(workflow_patch_targets)
    if missing_patch_targets:
        raise ValueError(f"workflow_patch_targets_missing:{','.join(sorted(missing_patch_targets))}")

    default_qa_goals = ["shot_size_matches_intent", "no_unintentional_crop", "focus_target_sharp"]
    if shot_size == "full_body":
        default_qa_goals.extend(["full_body_visible", "head_hands_feet_visible", "body_scale_consistent"])
    qa_goals = _unique(
        _string_list(request.get("qa_goals", default_qa_goals), "qa_goals") + default_qa_goals
    )

    reference_route = _compile_reference_route(request)
    control_plan = _compile_control_plan(request)
    camera_plan_id = _require_string(
        request.get("camera_plan_id", f"cam_{shot_size}_auto_v1"), "camera_plan_id"
    )
    save_prefix = _slug(request.get("save_prefix", f"wave10_{camera_plan_id}"))

    plan: Dict[str, Any] = {
        "camera_plan_id": camera_plan_id,
        "scene_id": request.get("scene_id", "scene_auto"),
        "modality": modality,
        "shot_size": shot_size,
        "lens_profile": lens_profile,
        "camera_angle": camera_angle,
        "camera_height": request.get("camera_height", "eye"),
        "zoom_level": request.get("zoom_level", "normal"),
        "aspect_ratio": request.get("aspect_ratio", defaults["aspect_ratio"]),
        "resolution": {"width": width, "height": height},
        "framing": {
            "composition_preset": request.get(
                "composition_preset", "full_body_catalog" if shot_size == "full_body" else "rule_of_thirds_portrait"
            ),
            "crop_policy": request.get("crop_policy", "blocked_unintentional_crop"),
            "headroom": request.get("headroom", "controlled"),
            "footroom": request.get("footroom", "controlled" if shot_size == "full_body" else "not_applicable"),
            "side_margin": request.get("side_margin", "controlled"),
            "horizon_line": request.get("horizon_line", "stable"),
            "must_not_crop": must_not_crop,
            "intentional_crop_allowed": intentional_crop_allowed,
        },
        "depth_plan": {
            "depth_profile": request.get("depth_profile", defaults["depth_profile"]),
            "focus_targets": request.get(
                "focus_targets", ["face", "hands", "feet"] if shot_size == "full_body" else ["face", "hands"]
            ),
            "foreground_subjects": request.get("foreground_subjects", []),
            "midground_subjects": request.get("midground_subjects", [s["subject_id"] for s in normalized_subjects]),
            "background_subjects": request.get("background_subjects", ["environment"]),
            "background_blur_strength": _parse_float(
                request.get("background_blur_strength", 0.25), "background_blur_strength", 0.0, 1.0
            ),
            "depth_continuity_notes": request.get(
                "depth_continuity_notes", "Keep required subjects readable and in focus."
            ),
        },
        "subjects": normalized_subjects,
        "workflow_patch_targets": workflow_patch_targets,
        "qa_goals": qa_goals,
    }
    plan["workflow_instructions"] = {
        "positive_prompt_camera_module": _positive_camera_module(plan),
        "negative_prompt_crop_guard": _negative_crop_guard(plan),
        "latent_resolution": {"width": width, "height": height, "batch_size": 1},
        "reference_routing_plan": reference_route,
        "control_plan": control_plan,
        "save_prefix": save_prefix,
        "qa_goals": qa_goals,
    }
    return plan


def compile_prompt_profile(request: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Build a deterministic New-WorkflowRunPackage-compatible prompt profile."""
    if plan.get("modality") != "image":
        raise ValueError("prompt_profile_requires_image_modality")
    positive_prompt = _require_string(request.get("positive_prompt"), "positive_prompt")
    negative_prompt = str(request.get("negative_prompt", "")).strip()
    instructions = _require_dict(plan.get("workflow_instructions"), "workflow_instructions")
    positive_camera = _require_string(
        instructions.get("positive_prompt_camera_module"), "workflow_instructions.positive_prompt_camera_module"
    )
    negative_guard = _require_string(
        instructions.get("negative_prompt_crop_guard"), "workflow_instructions.negative_prompt_crop_guard"
    )
    seed = _parse_int(request.get("seed", 7152026101), "seed", 0, 9223372036854775807)
    sampler_raw = _require_dict(request.get("sampler_settings", {}), "sampler_settings")
    sampler_name = sampler_raw.get("sampler_name", "dpmpp_2m")
    scheduler = sampler_raw.get("scheduler", "karras")
    if sampler_name not in ALLOWED_SAMPLERS:
        raise ValueError(f"unknown_sampler_name:{sampler_name}")
    if scheduler not in ALLOWED_SCHEDULERS:
        raise ValueError(f"unknown_scheduler:{scheduler}")

    sampler_settings = {
        "steps": _parse_int(sampler_raw.get("steps", 24), "sampler_settings.steps", 1, 150),
        "cfg": _parse_float(sampler_raw.get("cfg", 5.5), "sampler_settings.cfg", 0.0, 30.0),
        "sampler_name": sampler_name,
        "scheduler": scheduler,
        "denoise": _parse_float(sampler_raw.get("denoise", 1.0), "sampler_settings.denoise", 0.0, 1.0),
    }
    target_lane_id = _require_string(
        request.get("target_lane_id", "sdxl_realvisxl_base_lane"), "target_lane_id"
    )
    control_plan = instructions["control_plan"]
    if control_plan["enabled"] and control_plan["target_lane_id"] != target_lane_id:
        raise ValueError("control_plan_target_lane_does_not_match_profile_target_lane")

    request_patch_values: Dict[str, Any] = {
        "positive_prompt": f"{positive_prompt.rstrip(', ')}, {positive_camera}",
        "negative_prompt": ", ".join(part for part in (negative_prompt.rstrip(", "), negative_guard) if part),
        "seed": seed,
        "sampler_settings": sampler_settings,
        "latent_resolution": dict(instructions["latent_resolution"]),
        "model_asset": _require_string(
            request.get("model_asset", "realvisxlV50_v50Bakedvae.safetensors"), "model_asset"
        ),
        "save_prefix": instructions["save_prefix"],
    }
    if control_plan["enabled"]:
        request_patch_values.update(
            {
                "controlnet_asset": control_plan["controlnet_asset"],
                "control_image": control_plan["control_image"],
                "controlnet_settings": control_plan["settings"],
            }
        )

    canonical_plan = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    plan_sha256 = hashlib.sha256(canonical_plan).hexdigest()
    save_prefix = instructions["save_prefix"]
    return {
        "schema_version": "1.0",
        "profile_id": _slug(request.get("profile_id", f"{save_prefix}_profile")),
        "target_lane_id": target_lane_id,
        "purpose": request.get(
            "purpose", "Wave10 compiler-driven still-image camera framing and crop-safety proof."
        ),
        "camera_plan_binding": {"camera_plan_id": plan["camera_plan_id"], "sha256": plan_sha256},
        "request_patch_values": request_patch_values,
        "expected_outputs": {
            "artifact_type": "image",
            "minimum_output_count": 1,
            "output_prefix": save_prefix,
        },
        "compiler_outputs": instructions,
        "qa_focus": list(plan["qa_goals"]),
        "runtime_boundaries": {
            "local_profile_only": True,
            "aws_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "gold_masks_consumed": False,
            "body_mask_or_geometry_authority_claimed": False,
            "reference_route_claimed": bool(instructions["reference_routing_plan"]["enabled"]),
            "control_plan_claimed": bool(control_plan["enabled"]),
            "requires_visual_qa": True,
            "requires_target_runtime_reproof_before_lane_certification": True,
        },
    }


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, help="Path to minimal camera request JSON")
    parser.add_argument("--out", required=True, help="Path to output camera plan JSON")
    parser.add_argument(
        "--profile-out",
        required=False,
        help="Optional output path for a New-WorkflowRunPackage-compatible prompt profile",
    )
    args = parser.parse_args()

    try:
        request_path = Path(args.request)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        plan = compile_plan(request)
        _write_json(Path(args.out), plan)
        print(f"Wrote camera plan: {args.out}")
        if args.profile_out:
            profile = compile_prompt_profile(request, plan)
            _write_json(Path(args.profile_out), profile)
            print(f"Wrote prompt profile: {args.profile_out}")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"Camera plan compilation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
