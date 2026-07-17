#!/usr/bin/env python3
"""Build the additive Wave64 Rows261-320 hyperreal video/audio/App package.

This generator materializes planning contracts only.  It must never claim that
models, workflows, the durable controller, the operator application, or any
end-to-end media runtime is implemented or certified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any


UPDATED_AT = "2026-07-16T20:30:00-05:00"
PACKAGE_ID = "wave64_hyperreal_video_audio_app_third_pass_rows261_320"
STATUS = "Planned_Autonomous_Implementation_Required"
COMMON_ID = "https://comfy-ui-main.local/schemas/hyperreal-media-common/1.0.0"


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def text_bytes(value: str) -> bytes:
    return value.strip() .encode("utf-8") + b"\n"


def csv_bytes(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return stream.getvalue().encode("utf-8")


def s(min_length: int = 1) -> dict[str, Any]:
    return {"type": "string", "minLength": min_length}


def sha() -> dict[str, Any]:
    return {"$ref": f"{COMMON_ID}#/$defs/Sha256"}


def ref() -> dict[str, Any]:
    return {"$ref": f"{COMMON_ID}#/$defs/ImmutableRecordRef"}


def refs(min_items: int = 1) -> dict[str, Any]:
    return {"type": "array", "items": ref(), "minItems": min_items}


def enum(*values: str) -> dict[str, Any]:
    return {"enum": list(values)}


def array(items: dict[str, Any], min_items: int = 0, unique: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "array", "items": items}
    if min_items:
        result["minItems"] = min_items
    if unique:
        result["uniqueItems"] = True
    return result


def strict_object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required or list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def record_schema(
    slug: str,
    title: str,
    id_field: str,
    properties: dict[str, Any],
    required: list[str],
    *,
    all_of: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base_properties: dict[str, Any] = {
        "schema_version": {"const": "1.0.0"},
        "record_type": {"const": slug.replace("-", "_")},
        id_field: s(),
        "revision": s(),
        "status": enum("draft", "planned", "validated", "certified", "accepted", "rejected", "blocked", "revoked"),
        "created_at": {"type": "string", "format": "date-time"},
        "provenance": {"$ref": f"{COMMON_ID}#/$defs/Provenance"},
    }
    base_properties.update(properties)
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://comfy-ui-main.local/schemas/{slug}/1.0.0",
        "title": title,
        "type": "object",
        "required": ["schema_version", "record_type", id_field, "revision", "status", "created_at", *required, "provenance"],
        "properties": base_properties,
        "additionalProperties": False,
    }
    if all_of:
        schema["allOf"] = all_of
    return schema


WORKSTREAMS = [
    ("HVAA-01", "video_project_clock_reference_authority", "Freeze project, rational media clock, reference authority, color pipeline, and output contracts."),
    ("HVAA-02", "video_shot_keyframe_continuity", "Publish shot, keyframe, camera, identity, anatomy, lighting, and material continuity authority."),
    ("HVAA-03", "video_motion_physics_interaction", "Model primary, micro, secondary, contact, fabric, hair, fluid, camera, and settling motion."),
    ("HVAA-04", "video_engine_candidate_multipass_routing", "Route exact video bundles per shot/pass and compare bounded candidates without latent-family leakage."),
    ("HVAA-05", "video_frame_qa_and_local_span_repair", "Create frame truth, calibrated temporal QA, defect localization, and immutable-parent span repair."),
    ("HVAA-06", "video_longform_benchmark_and_promotion", "Qualify long-form continuity, benchmark engines, measure uncertainty, and issue scoped video certificates."),
    ("HVAA-07", "audio_event_graph_and_source_strategy", "Compile owned audio events and route recorded, retrieved, procedural, neural, synthesized, or hybrid sources."),
    ("HVAA-08", "voice_nonverbal_prosody_and_lipsync", "Bind character voice, pronunciation, performance, breath, nonverbal vocalization, alignment, and visemes."),
    ("HVAA-09", "foley_force_material_acoustic_spatial", "Render force/material-aware foley and physically coherent room, occlusion, distance, and spatial objects."),
    ("HVAA-10", "mix_master_av_clock_and_local_repair", "Mix nondestructive stems, master to profiles, preserve clocks, and repair only failed AV spans."),
    ("HVAA-11", "audio_av_benchmark_learning_and_promotion", "Run objective and perceptual audio/AV QA, calibrated critics, learning reports, and scoped release."),
    ("HVAA-12", "operator_app_platform_ia_and_timeline", "Deliver project, character, scene, shot, mask, image, video, audio, AV, and timeline information architecture."),
    ("HVAA-13", "operator_commands_queries_compare_and_repair", "Expose typed commands/queries, live DAG state, comparisons, explanations, repair, and approvals."),
    ("HVAA-14", "operator_models_runtime_observability_recovery", "Expose model evidence, workers, leases, queues, incidents, reconciliation, recovery, and audit history."),
    ("HVAA-15", "operator_security_accessibility_testing_release", "Enforce roles, local credential isolation, accessibility, responsive behavior, tests, deployment, and release."),
]


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    row_number = 261
    previous_release: str | None = None
    phases = (
        ("contract", "Publish strict schemas and canonical record boundaries"),
        ("policy", "Freeze registries, policies, thresholds, and authority"),
        ("implementation", "Implement the bounded runtime/application slice with synthetic fixtures first"),
        ("assurance", "Prove positive, negative, fault, perceptual, and release behavior"),
    )
    for workstream_id, slug, objective in WORKSTREAMS:
        local_ids: list[str] = []
        for phase_index, (phase, phase_title) in enumerate(phases):
            item_id = f"ITEM-W64-{row_number:03d}"
            tracker_id = f"TRK-W64-{row_number:03d}"
            dependencies: list[str] = []
            if phase_index:
                dependencies.append(local_ids[-1])
            elif previous_release:
                dependencies.append(previous_release)
            if row_number == 261:
                dependencies = ["ITEM-W64-220"]
            row = {
                "row_number": row_number,
                "item_id": item_id,
                "tracker_id": tracker_id,
                "workstream_id": workstream_id,
                "workstream": slug,
                "phase": phase,
                "title": f"{phase_title}: {slug.replace('_', ' ')}",
                "objective": objective,
                "dependencies": dependencies,
                "required_artifacts": [
                    f"{slug}_{phase}_record",
                    f"{slug}_{phase}_evidence",
                    "append_only_decision_or_status_record",
                ],
                "acceptance_tests": [
                    "schema_and_semantic_validation",
                    "authority_and_reference_resolution",
                    "negative_path_fail_closed",
                    "no_runtime_completion_from_planning",
                ],
                "external_gates": [
                    "exact_model_bundle_certificate_when_execution_is_requested",
                    "durable_controller_and_comfyui_runtime_release_when_execution_is_requested",
                    "maskfactory_certificate_for_mask_authority_when_required",
                    "human_or_policy_release_gate_for_perceptual_promotion",
                ],
                "status": STATUS,
                "runtime_completion_claimed": False,
                "source_citations": [
                    "Plan/01_CURRENT_SYSTEM_REVIEW/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_GAP_AUDIT.md",
                    "Plan/02_TARGET_ARCHITECTURE/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_CONTROL_ARCHITECTURE.md",
                ],
            }
            rows.append(row)
            local_ids.append(item_id)
            row_number += 1
        previous_release = local_ids[-1]
    # The final release row must require every earlier row transitively and the
    # external release authorities without making those authorities planning prerequisites.
    rows[-1]["required_artifacts"].extend(
        [
            "rows261_319_transitive_dependency_proof",
            "video_audio_av_app_release_decision",
            "runtime_truth_statement",
        ]
    )
    rows[-1]["external_gates"].extend(
        [
            "ITEM-W64-260_model_intelligence_production_selection_release",
            "Rows149_220_multimodal_controller_and_media_release",
            "current_maskfactory_release_snapshot",
        ]
    )
    return rows


def build_common_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": COMMON_ID,
        "title": "Wave64 Hyperreal Media and Operator Application Common Definitions",
        "$defs": {
            "Sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "ImmutableRecordRef": strict_object(
                {
                    "schema_id": s(), "record_type": s(), "record_id": s(), "revision": s(),
                    "sha256": {"$ref": "#/$defs/Sha256"}, "bytes": {"type": "integer", "minimum": 1},
                    "path_or_uri": s(),
                }
            ),
            "Provenance": strict_object(
                {
                    "producer": s(), "producer_version": s(), "source_refs": array({"$ref": "#/$defs/ImmutableRecordRef"}),
                    "registry_snapshot_ids": array(s(), 1, True), "canonicalization": {"const": "rfc8785_jcs"},
                }
            ),
            "ExecutionScope": strict_object({"project_id": s(), "scene_id": s(), "shot_id": s(), "take_id": s()}),
            "OwnerRef": strict_object(
                {"owner_type": enum("character_instance", "object_instance", "environment", "camera", "audio_bus", "global"), "owner_id": s()}
            ),
            "RationalTimebase": strict_object(
                {"numerator": {"type": "integer", "minimum": 1}, "denominator": {"type": "integer", "minimum": 1}, "drop_frame": {"type": "boolean"}}
            ),
            "MediaSpan": strict_object(
                {
                    "clock_id": s(), "timebase": {"$ref": "#/$defs/RationalTimebase"},
                    "start_pts": {"type": "integer", "minimum": 0}, "end_pts_exclusive": {"type": "integer", "minimum": 1},
                    "start_frame": {"type": ["integer", "null"], "minimum": 0}, "end_frame_exclusive": {"type": ["integer", "null"], "minimum": 1},
                    "start_sample": {"type": ["integer", "null"], "minimum": 0}, "end_sample_exclusive": {"type": ["integer", "null"], "minimum": 1},
                    "rounding_policy": enum("exact_only", "floor_start_ceil_end", "nearest_ties_to_even"),
                }
            ),
            "MetricResult": strict_object(
                {
                    "metric_id": s(), "metric_revision": s(), "value": {"type": "number"}, "unit": s(),
                    "threshold": {"type": "number"}, "direction": enum("min", "max", "range"),
                    "passed": {"type": "boolean"}, "confidence_low": {"type": "number", "minimum": 0, "maximum": 1},
                    "confidence_high": {"type": "number", "minimum": 0, "maximum": 1}, "evidence_ref": {"$ref": "#/$defs/ImmutableRecordRef"},
                }
            ),
            "ArtifactRef": strict_object(
                {
                    "artifact_id": s(), "media_type": s(), "sha256": {"$ref": "#/$defs/Sha256"},
                    "bytes": {"type": "integer", "minimum": 1}, "safe_relative_locator": {"type": "string", "pattern": "^(?![A-Za-z]:)(?!/)(?!.*\\.\\.).+$"},
                }
            ),
        },
    }


def build_schemas() -> dict[str, dict[str, Any]]:
    clock = {"$ref": f"{COMMON_ID}#/$defs/MediaSpan"}
    scope = {"$ref": f"{COMMON_ID}#/$defs/ExecutionScope"}
    owner = {"$ref": f"{COMMON_ID}#/$defs/OwnerRef"}
    metric = {"$ref": f"{COMMON_ID}#/$defs/MetricResult"}
    artifact = {"$ref": f"{COMMON_ID}#/$defs/ArtifactRef"}
    schemas: dict[str, dict[str, Any]] = {"hyperreal_media_common.schema.json": build_common_schema()}

    schemas["hyperreal_video_project_spec.schema.json"] = record_schema(
        "hyperreal-video-project-spec", "Hyperreal Video Project Specification", "video_project_spec_id",
        {
            "project_id": s(), "canonical_clock": clock, "deliverable_kind": enum("clip", "shot_sequence", "loop", "long_form", "av_master"),
            "width": {"type": "integer", "minimum": 256}, "height": {"type": "integer", "minimum": 256},
            "pixel_aspect_ratio": {"type": "number", "exclusiveMinimum": 0}, "frame_rate": {"type": "number", "exclusiveMinimum": 0},
            "duration_pts": {"type": "integer", "minimum": 1}, "color_pipeline_id": s(), "camera_model_id": s(),
            "character_package_refs": refs(), "scene_package_ref": ref(), "shot_refs": refs(), "qa_profile_id": s(),
            "audio_required": {"type": "boolean"}, "runtime_execution_allowed": {"const": False},
        },
        ["project_id", "canonical_clock", "deliverable_kind", "width", "height", "pixel_aspect_ratio", "frame_rate", "duration_pts", "color_pipeline_id", "camera_model_id", "character_package_refs", "scene_package_ref", "shot_refs", "qa_profile_id", "audio_required", "runtime_execution_allowed"],
    )

    shot_segment = strict_object(
        {
            "segment_id": s(), "span": clock, "camera_state_ref": ref(), "pose_state_refs": refs(), "mask_binding_refs": refs(),
            "keyframe_refs": refs(), "action_beat_ids": array(s(), 1, True), "audio_event_ids": array(s(), 0, True),
            "continuity_parent_segment_id": {"type": ["string", "null"]}, "cut_kind": enum("hard_cut", "match_cut", "dissolve", "continuous"),
        }
    )
    schemas["hyperreal_video_shot_timeline.schema.json"] = record_schema(
        "hyperreal-video-shot-timeline", "Hyperreal Video Shot Timeline", "video_shot_timeline_id",
        {"scope": scope, "canonical_clock": clock, "segments": array(shot_segment, 1), "segment_order_sha256": sha(), "overlap_policy": enum("forbid", "transition_only"), "coverage_complete": {"const": True}},
        ["scope", "canonical_clock", "segments", "segment_order_sha256", "overlap_policy", "coverage_complete"],
    )

    schemas["hyperreal_video_keyframe_authority.schema.json"] = record_schema(
        "hyperreal-video-keyframe-authority", "Hyperreal Video Keyframe Authority", "video_keyframe_authority_id",
        {
            "scope": scope, "frame_index": {"type": "integer", "minimum": 0}, "pts": {"type": "integer", "minimum": 0},
            "image_artifact": artifact, "character_instance_ids": array(s(), 1, True), "identity_refs": refs(), "pose_ref": ref(),
            "depth_ref": ref(), "mask_binding_refs": refs(), "camera_ref": ref(), "lighting_state_ref": ref(), "surface_state_refs": refs(),
            "authority_tier": enum("draft", "approved_keyframe", "locked_boundary"), "certificate_ref": {"oneOf": [ref(), {"type": "null"}]},
        },
        ["scope", "frame_index", "pts", "image_artifact", "character_instance_ids", "identity_refs", "pose_ref", "depth_ref", "mask_binding_refs", "camera_ref", "lighting_state_ref", "surface_state_refs", "authority_tier", "certificate_ref"],
        all_of=[{
            "if": {"properties": {"authority_tier": {"enum": ["approved_keyframe", "locked_boundary"]}}, "required": ["authority_tier"]},
            "then": {"properties": {"certificate_ref": ref()}},
        }],
    )

    motion_channel = strict_object(
        {
            "channel_id": s(), "motion_class": enum("primary", "micro", "secondary", "contact", "camera", "stabilization"),
            "owner": owner, "span": clock, "driver": enum("keyframe", "pose", "depth", "flow", "physics", "reference_video", "procedural", "model_generated"),
            "amplitude_limit": {"type": "number", "minimum": 0}, "frequency_limit_hz": {"type": "number", "minimum": 0},
            "phase_relation_ids": array(s(), 0, True), "conservation_or_constraint_ids": array(s(), 0, True), "parameter_payload_ref": ref(),
        }
    )
    schemas["hyperreal_video_motion_physics_plan.schema.json"] = record_schema(
        "hyperreal-video-motion-physics-plan", "Hyperreal Video Motion and Physics Plan", "video_motion_physics_plan_id",
        {"scope": scope, "channels": array(motion_channel, 1), "contact_graph_ref": ref(), "material_profile_refs": refs(), "gravity_vector": array({"type": "number"}, 3), "unit_system": {"const": "si"}, "solver_or_generator_policy_id": s()},
        ["scope", "channels", "contact_graph_ref", "material_profile_refs", "gravity_vector", "unit_system", "solver_or_generator_policy_id"],
    )

    candidate_eval = strict_object(
        {
            "bundle_ref": ref(), "eligible": {"type": "boolean"}, "hard_filter_reasons": array(s(), 0, True),
            "rank_score": {"type": ["number", "null"], "minimum": 0, "maximum": 1}, "confidence_low": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "certificate_ref": {"oneOf": [ref(), {"type": "null"}]}, "pareto_frontier": {"type": "boolean"},
        }
    )
    schemas["hyperreal_video_engine_route_decision.schema.json"] = record_schema(
        "hyperreal-video-engine-route-decision", "Hyperreal Video Engine Route Decision", "video_engine_route_decision_id",
        {
            "scope": scope, "pass_intent": enum("keyframe_to_video", "image_to_video", "text_to_video", "reference_video_guided", "interpolation", "extension", "localized_span_repair", "temporal_refine", "upscale"),
            "context_ref": ref(), "evaluated_candidates": array(candidate_eval, 1), "selected_bundle_ref": {"oneOf": [ref(), {"type": "null"}]},
            "decision": enum("selected", "branch_compare", "abstain", "blocked"), "ranking_policy_id": s(), "registry_snapshot_id": s(),
            "assignment_probability": {"type": ["number", "null"], "exclusiveMinimum": 0, "maximum": 1}, "production_execution_allowed": {"type": "boolean"},
        },
        ["scope", "pass_intent", "context_ref", "evaluated_candidates", "selected_bundle_ref", "decision", "ranking_policy_id", "registry_snapshot_id", "assignment_probability", "production_execution_allowed"],
        all_of=[{
            "if": {"properties": {"production_execution_allowed": {"const": True}}, "required": ["production_execution_allowed"]},
            "then": {"properties": {"decision": {"const": "selected"}, "selected_bundle_ref": ref()}},
        }],
    )

    schemas["hyperreal_video_generation_candidate.schema.json"] = record_schema(
        "hyperreal-video-generation-candidate", "Hyperreal Video Generation Candidate", "video_generation_candidate_id",
        {
            "scope": scope, "route_decision_ref": ref(), "attempt_ref": ref(), "parent_artifact_refs": refs(), "output_artifact": artifact,
            "frame_manifest_ref": ref(), "generation_parameter_ref": ref(), "seed": {"type": "integer", "minimum": 0},
            "accepted_parent_immutable": {"const": True}, "candidate_only": {"type": "boolean"}, "promotable": {"type": "boolean"},
        },
        ["scope", "route_decision_ref", "attempt_ref", "parent_artifact_refs", "output_artifact", "frame_manifest_ref", "generation_parameter_ref", "seed", "accepted_parent_immutable", "candidate_only", "promotable"],
    )

    track = strict_object(
        {"track_id": s(), "owner": owner, "bbox_xywh": array({"type": "number"}, 4), "mask_ref": ref(), "pose_ref": ref(), "depth_order": {"type": "integer"}, "visibility": {"type": "number", "minimum": 0, "maximum": 1}, "identity_score": {"type": ["number", "null"], "minimum": 0, "maximum": 1}}
    )
    frame = strict_object(
        {"frame_index": {"type": "integer", "minimum": 0}, "pts": {"type": "integer", "minimum": 0}, "artifact": artifact, "tracks": array(track), "camera_state_ref": ref(), "exposure_value": {"type": "number"}, "color_state_ref": ref(), "flow_to_next_ref": {"oneOf": [ref(), {"type": "null"}]}, "defect_ids": array(s(), 0, True)}
    )
    schemas["hyperreal_video_frame_manifest.schema.json"] = record_schema(
        "hyperreal-video-frame-manifest", "Hyperreal Video Per-Frame Manifest", "video_frame_manifest_id",
        {"scope": scope, "canonical_clock": clock, "frames": array(frame, 1), "frame_count": {"type": "integer", "minimum": 1}, "contiguous": {"const": True}, "manifest_sha256": sha()},
        ["scope", "canonical_clock", "frames", "frame_count", "contiguous", "manifest_sha256"],
    )

    continuity_domain = strict_object(
        {"domain": enum("identity", "anatomy", "skin", "hair", "wardrobe", "prop", "environment", "lighting", "camera", "pose", "contact", "fatigue", "breathing", "damage", "wetness", "makeup"), "owner": owner, "state_ref": ref(), "effective_span": clock, "change_reason": s(), "persistence": enum("frame", "shot", "scene", "sequence", "project")}
    )
    schemas["hyperreal_video_continuity_ledger.schema.json"] = record_schema(
        "hyperreal-video-continuity-ledger", "Hyperreal Video Continuity Ledger", "video_continuity_ledger_id",
        {"project_id": s(), "parent_revision_ref": {"oneOf": [ref(), {"type": "null"}]}, "domains": array(continuity_domain, 1), "conflicts": array(strict_object({"conflict_id": s(), "state_ref_a": ref(), "state_ref_b": ref(), "resolution": enum("unresolved", "a_wins", "b_wins", "new_revision")}), 0), "all_conflicts_resolved": {"type": "boolean"}},
        ["project_id", "parent_revision_ref", "domains", "conflicts", "all_conflicts_resolved"],
    )

    schemas["hyperreal_video_temporal_qa_evaluation.schema.json"] = record_schema(
        "hyperreal-video-temporal-qa-evaluation", "Hyperreal Video Temporal QA Evaluation", "video_temporal_qa_evaluation_id",
        {
            "scope": scope, "candidate_ref": ref(), "evaluated_span": clock, "metric_results": array(metric, 1),
            "defects": array(strict_object({"defect_id": s(), "defect_class": s(), "severity": enum("info", "minor", "major", "critical"), "span": clock, "owner": owner, "target_mask_ref": {"oneOf": [ref(), {"type": "null"}]}, "evidence_ref": ref()})),
            "critic_observation_refs": refs(), "calibration_snapshot_id": s(), "decision": enum("accept", "repair", "reroute", "reject", "human_review"),
            "whole_clip_acceptance": {"type": "boolean"}, "uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
        },
        ["scope", "candidate_ref", "evaluated_span", "metric_results", "defects", "critic_observation_refs", "calibration_snapshot_id", "decision", "whole_clip_acceptance", "uncertainty"],
    )

    repair_span = strict_object(
        {"defect_ids": array(s(), 1, True), "target_span": clock, "decode_handle_frames_before": {"type": "integer", "minimum": 1}, "decode_handle_frames_after": {"type": "integer", "minimum": 1}, "write_mask_refs": refs(), "protected_mask_refs": refs(), "boundary_keyframe_refs": refs(), "repair_method": enum("regenerate_span", "inpaint_frames", "flow_guided_refine", "interpolate", "reroute_engine", "color_temporal_blend"), "hypothesis_ref": ref()}
    )
    schemas["hyperreal_video_span_repair_plan.schema.json"] = record_schema(
        "hyperreal-video-span-repair-plan", "Hyperreal Video Local Span Repair Plan", "video_span_repair_plan_id",
        {"scope": scope, "accepted_parent_ref": ref(), "qa_evaluation_ref": ref(), "repairs": array(repair_span, 1), "accepted_parent_immutable": {"const": True}, "smallest_failed_scope_only": {"const": True}, "full_clip_rerender": {"const": False}, "max_attempts": {"type": "integer", "minimum": 1, "maximum": 5}},
        ["scope", "accepted_parent_ref", "qa_evaluation_ref", "repairs", "accepted_parent_immutable", "smallest_failed_scope_only", "full_clip_rerender", "max_attempts"],
    )

    cinematic_sample = strict_object(
        {
            "pts": {"type": "integer", "minimum": 0}, "camera_position_xyz_m": array({"type": "number"}, 3),
            "camera_rotation_xyzw": array({"type": "number"}, 4), "focal_length_mm": {"type": "number", "exclusiveMinimum": 0},
            "focus_distance_m": {"type": "number", "exclusiveMinimum": 0}, "aperture_f": {"type": "number", "exclusiveMinimum": 0},
            "shutter_angle_deg": {"type": "number", "minimum": 0, "maximum": 360}, "iso": {"type": "number", "exclusiveMinimum": 0},
            "white_balance_k": {"type": "number", "minimum": 1000, "maximum": 20000}, "exposure_compensation_ev": {"type": "number"},
            "rolling_shutter_ms": {"type": "number", "minimum": 0}, "lens_distortion_profile_id": s(), "lighting_state_ref": ref(),
        }
    )
    schemas["hyperreal_cinematic_state_timeline.schema.json"] = record_schema(
        "hyperreal-cinematic-state-timeline", "Hyperreal Cinematic Camera, Exposure, Lighting, and Color Timeline", "cinematic_state_timeline_id",
        {"scope": scope, "canonical_clock": clock, "sensor_profile_id": s(), "color_pipeline_id": s(), "input_color_space": s(), "working_color_space": s(), "display_transform_id": s(), "tone_map_id": s(), "grain_policy_id": s(), "samples": array(cinematic_sample, 2), "pts_strictly_increasing": {"const": True}, "unplanned_discontinuities_allowed": {"const": False}},
        ["scope", "canonical_clock", "sensor_profile_id", "color_pipeline_id", "input_color_space", "working_color_space", "display_transform_id", "tone_map_id", "grain_policy_id", "samples", "pts_strictly_increasing", "unplanned_discontinuities_allowed"],
    )

    instance_sample = strict_object(
        {
            "frame_index": {"type": "integer", "minimum": 0}, "pts": {"type": "integer", "minimum": 0},
            "bbox_xywh": array({"type": "number"}, 4), "silhouette_mask_ref": ref(), "pose_ref": ref(), "depth_ref": ref(),
            "visibility": {"type": "number", "minimum": 0, "maximum": 1}, "occluded_by_owner_ids": array(s(), 0, True),
            "identity_observation_ref": ref(), "wardrobe_state_ref": ref(), "surface_state_ref": ref(), "contact_event_ids": array(s(), 0, True),
        }
    )
    schemas["hyperreal_temporal_instance_track.schema.json"] = record_schema(
        "hyperreal-temporal-instance-track", "Hyperreal Per-Character Temporal Instance Track", "temporal_instance_track_id",
        {"scope": scope, "character_instance_id": s(), "character_package_ref": ref(), "provider_person_index": {"type": "integer", "minimum": 0}, "render_order": {"type": "integer", "minimum": 0}, "samples": array(instance_sample, 1), "frame_coverage_complete": {"const": True}, "owner_never_changes": {"const": True}},
        ["scope", "character_instance_id", "character_package_ref", "provider_person_index", "render_order", "samples", "frame_coverage_complete", "owner_never_changes"],
    )

    schemas["hyperreal_video_resource_chunk_plan.schema.json"] = record_schema(
        "hyperreal-video-resource-chunk-plan", "Hyperreal Video Chunk, Resource, Residency, and Recovery Plan", "video_resource_chunk_plan_id",
        {"scope": scope, "route_decision_ref": ref(), "chunks": array(strict_object({"chunk_id": s(), "target_span": clock, "handle_frames_before": {"type": "integer", "minimum": 0}, "handle_frames_after": {"type": "integer", "minimum": 0}, "bundle_ref": ref(), "workflow_release_ref": ref(), "runtime_lock_ref": ref(), "max_vram_mib": {"type": "integer", "minimum": 1}, "max_ram_mib": {"type": "integer", "minimum": 1}, "max_disk_mib": {"type": "integer", "minimum": 1}, "timeout_seconds": {"type": "integer", "minimum": 1}, "safe_preemption": {"type": "boolean"}, "checkpoint_policy_id": s()}), 1), "model_residency_policy_id": s(), "lease_policy_id": s(), "recovery_policy_id": s(), "overlap_reintegration_policy_id": s()},
        ["scope", "route_decision_ref", "chunks", "model_residency_policy_id", "lease_policy_id", "recovery_policy_id", "overlap_reintegration_policy_id"],
    )

    schemas["hyperreal_decoded_video_bridge_qualification.schema.json"] = record_schema(
        "hyperreal-decoded-video-bridge-qualification", "Hyperreal Decoded Video Bridge Qualification", "decoded_video_bridge_qualification_id",
        {"source_bundle_ref": ref(), "target_bundle_ref": ref(), "source_workflow_ref": ref(), "target_workflow_ref": ref(), "source_pixel_format": s(), "target_pixel_format": s(), "source_color_space": s(), "target_color_space": s(), "orientation_policy_id": s(), "alpha_policy_id": s(), "timebase_policy_id": s(), "transform_chain_ref": ref(), "reintegration_policy_id": s(), "roundtrip_metric_results": array(metric, 1), "supported_pass_intents": array(s(), 1, True), "certificate_ref": {"oneOf": [ref(), {"type": "null"}]}, "execution_allowed": {"type": "boolean"}},
        ["source_bundle_ref", "target_bundle_ref", "source_workflow_ref", "target_workflow_ref", "source_pixel_format", "target_pixel_format", "source_color_space", "target_color_space", "orientation_policy_id", "alpha_policy_id", "timebase_policy_id", "transform_chain_ref", "reintegration_policy_id", "roundtrip_metric_results", "supported_pass_intents", "certificate_ref", "execution_allowed"],
        all_of=[{
            "if": {"properties": {"execution_allowed": {"const": True}}, "required": ["execution_allowed"]},
            "then": {"properties": {"status": {"const": "certified"}, "certificate_ref": ref()}},
        }],
    )

    schemas["hyperreal_video_benchmark_result.schema.json"] = record_schema(
        "hyperreal-video-benchmark-result", "Hyperreal Video Benchmark Result", "video_benchmark_result_id",
        {"bundle_ref": ref(), "suite_id": s(), "suite_revision": s(), "partition_id": s(), "holdout": {"type": "boolean"}, "sample_count": {"type": "integer", "minimum": 1}, "metric_results": array(metric, 1), "failure_distribution_ref": ref(), "runtime_profile_ref": ref(), "selection_probability_recorded": {"const": True}},
        ["bundle_ref", "suite_id", "suite_revision", "partition_id", "holdout", "sample_count", "metric_results", "failure_distribution_ref", "runtime_profile_ref", "selection_probability_recorded"],
    )

    schemas["hyperreal_video_promotion_certificate.schema.json"] = record_schema(
        "hyperreal-video-promotion-certificate", "Hyperreal Video Promotion Certificate", "video_promotion_certificate_id",
        {"artifact_ref": ref(), "scope": scope, "approved_span": clock, "qa_evaluation_refs": refs(), "benchmark_refs": refs(), "continuity_ledger_ref": ref(), "allowed_uses": array(enum("preview", "intermediate_parent", "final_video", "av_master"), 1, True), "expires_at": {"type": ["string", "null"], "format": "date-time"}, "revocation_policy_id": s(), "runtime_release_decision_ref": {"oneOf": [ref(), {"type": "null"}]}, "runtime_completion_claimed": {"type": "boolean"}},
        ["artifact_ref", "scope", "approved_span", "qa_evaluation_refs", "benchmark_refs", "continuity_ledger_ref", "allowed_uses", "expires_at", "revocation_policy_id", "runtime_release_decision_ref", "runtime_completion_claimed"],
        all_of=[{
            "if": {"properties": {"runtime_completion_claimed": {"const": True}}, "required": ["runtime_completion_claimed"]},
            "then": {"properties": {"status": {"const": "certified"}, "runtime_release_decision_ref": ref()}},
        }],
    )

    audio_event = strict_object(
        {"event_id": s(), "event_class": enum("dialogue", "breath", "nonverbal_voice", "body_foley", "fabric_foley", "prop_foley", "impact", "ambience", "room_tone", "music", "designed_sfx"), "owner": owner, "span": clock, "visual_source_ref": {"oneOf": [ref(), {"type": "null"}]}, "force_event_ref": {"oneOf": [ref(), {"type": "null"}]}, "material_pair_id": {"type": ["string", "null"]}, "position_track_ref": {"oneOf": [ref(), {"type": "null"}]}, "priority": {"type": "integer", "minimum": 0, "maximum": 100}, "required": {"type": "boolean"}}
    )
    schemas["hyperreal_audio_event_graph.schema.json"] = record_schema(
        "hyperreal-audio-event-graph", "Hyperreal Audio Event Graph", "audio_event_graph_id",
        {"scope": scope, "canonical_clock": clock, "events": array(audio_event, 1), "edges": array(strict_object({"source_event_id": s(), "target_event_id": s(), "relation": enum("precedes", "causes", "ducks", "masks", "layers_with", "excludes", "syncs_to")})), "acyclic_causal_edges": {"const": True}, "all_required_visual_events_bound": {"const": True}},
        ["scope", "canonical_clock", "events", "edges", "acyclic_causal_edges", "all_required_visual_events_bound"],
    )

    audio_candidate = strict_object(
        {
            "source_or_bundle_ref": ref(),
            "origin_class": enum("field_recording", "studio_foley_recording", "voice_performance_recording", "procedural_render", "neural_text_conditioned", "neural_audio_conditioned", "neural_video_conditioned", "hybrid_composite"),
            "realization_action": enum("retrieve_reuse", "record_new", "generate_new", "synthesize_procedural", "assemble_layers"),
            "derivation_state": enum("raw", "segmented", "prepared", "transformed", "layered", "spatially_rendered", "mastered"),
            "eligible": {"type": "boolean"}, "hard_filter_reasons": array(s(), 0, True),
            "rank_score": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "certificate_ref": {"oneOf": [ref(), {"type": "null"}]}, "license_scope_verified": {"type": "boolean"},
            "identity_or_material_match": {"type": "number", "minimum": 0, "maximum": 1},
        }
    )
    schemas["hyperreal_audio_source_route_decision.schema.json"] = record_schema(
        "hyperreal-audio-source-route-decision", "Hyperreal Audio Source Route Decision", "audio_source_route_decision_id",
        {"event_graph_ref": ref(), "event_id": s(), "candidates": array(audio_candidate, 1), "decision": enum("selected", "layered_hybrid", "branch_compare", "abstain", "blocked"), "selected_refs": refs(), "ranking_policy_id": s(), "assignment_probability": {"type": ["number", "null"], "exclusiveMinimum": 0, "maximum": 1}, "production_execution_allowed": {"type": "boolean"}},
        ["event_graph_ref", "event_id", "candidates", "decision", "selected_refs", "ranking_policy_id", "assignment_probability", "production_execution_allowed"],
    )

    schemas["hyperreal_voice_performance_spec.schema.json"] = record_schema(
        "hyperreal-voice-performance-spec", "Hyperreal Character Voice Performance Specification", "voice_performance_spec_id",
        {"scope": scope, "character_instance_id": s(), "voice_package_ref": ref(), "text_normalization_ref": ref(), "pronunciation_lexicon_ref": ref(), "language": s(), "utterance_text_sha256": sha(), "span": clock, "emotion_curve_ref": ref(), "prosody_curve_ref": ref(), "breath_plan_ref": ref(), "phoneme_alignment_required": {"const": True}, "dry_voice_required": {"const": True}, "identity_certificate_ref": ref()},
        ["scope", "character_instance_id", "voice_package_ref", "text_normalization_ref", "pronunciation_lexicon_ref", "language", "utterance_text_sha256", "span", "emotion_curve_ref", "prosody_curve_ref", "breath_plan_ref", "phoneme_alignment_required", "dry_voice_required", "identity_certificate_ref"],
    )

    schemas["hyperreal_nonverbal_vocalization_plan.schema.json"] = record_schema(
        "hyperreal-nonverbal-vocalization-plan", "Hyperreal Nonverbal Vocalization Plan", "nonverbal_vocalization_plan_id",
        {"scope": scope, "character_instance_id": s(), "voice_package_ref": ref(), "events": array(strict_object({"event_id": s(), "kind": enum("breath", "effort", "laugh", "cry", "gasp", "sigh", "cough", "vocal_reaction"), "span": clock, "intensity": {"type": "number", "minimum": 0, "maximum": 1}, "visual_driver_ref": ref(), "continuity_state_ref": ref()}), 1), "identity_certificate_ref": ref(), "overlap_policy_id": s()},
        ["scope", "character_instance_id", "voice_package_ref", "events", "identity_certificate_ref", "overlap_policy_id"],
    )

    schemas["hyperreal_respiratory_performance_timeline.schema.json"] = record_schema(
        "hyperreal-respiratory-performance-timeline", "Hyperreal Respiratory Performance Timeline", "respiratory_performance_timeline_id",
        {"scope": scope, "character_instance_id": s(), "canonical_clock": clock, "continuity_state_ref": ref(), "events": array(strict_object({"respiratory_event_id": s(), "phase": enum("inhale", "hold", "exhale", "recovery", "effort", "speech_breath"), "span": clock, "intensity": {"type": "number", "minimum": 0, "maximum": 1}, "rate_bpm": {"type": "number", "minimum": 1, "maximum": 120}, "visual_chest_motion_ref": ref(), "voice_event_ref": {"oneOf": [ref(), {"type": "null"}]}, "fatigue_state_ref": ref(), "airflow_curve_ref": ref()}), 1), "phase_continuity_validated": {"const": True}},
        ["scope", "character_instance_id", "canonical_clock", "continuity_state_ref", "events", "phase_continuity_validated"],
    )

    schemas["hyperreal_viseme_alignment.schema.json"] = record_schema(
        "hyperreal-viseme-alignment", "Hyperreal Phoneme, Viseme, and Mouth-Ownership Alignment", "viseme_alignment_id",
        {"scope": scope, "character_instance_id": s(), "voice_performance_ref": ref(), "phoneme_alignment_ref": ref(), "mouth_mask_ref": ref(), "entries": array(strict_object({"phoneme": s(), "viseme_id": s(), "span": clock, "confidence": {"type": "number", "minimum": 0, "maximum": 1}, "coarticulation_left": {"type": "number", "minimum": 0, "maximum": 1}, "coarticulation_right": {"type": "number", "minimum": 0, "maximum": 1}, "observed_offset_ms": {"type": ["number", "null"]}, "correction_required": {"type": "boolean"}}), 1), "speaker_owner_verified": {"const": True}, "mouth_owner_verified": {"const": True}},
        ["scope", "character_instance_id", "voice_performance_ref", "phoneme_alignment_ref", "mouth_mask_ref", "entries", "speaker_owner_verified", "mouth_owner_verified"],
    )

    schemas["hyperreal_foley_force_material_event.schema.json"] = record_schema(
        "hyperreal-foley-force-material-event", "Hyperreal Foley Force and Material Event", "foley_force_material_event_id",
        {"scope": scope, "event_id": s(), "span": clock, "source_owner": owner, "target_owner": owner, "contact_ref": ref(), "force_profile_ref": ref(), "source_material_id": s(), "target_material_id": s(), "surface_state_refs": refs(), "gesture_or_motion_ref": ref(), "required_layers": array(enum("transient", "body", "resonance", "debris", "tail", "cloth", "friction"), 1, True), "source_route_decision_ref": ref()},
        ["scope", "event_id", "span", "source_owner", "target_owner", "contact_ref", "force_profile_ref", "source_material_id", "target_material_id", "surface_state_refs", "gesture_or_motion_ref", "required_layers", "source_route_decision_ref"],
    )

    schemas["hyperreal_contact_acoustic_phase_plan.schema.json"] = record_schema(
        "hyperreal-contact-acoustic-phase-plan", "Hyperreal Contact Acoustic Phase Plan", "contact_acoustic_phase_plan_id",
        {"scope": scope, "foley_event_ref": ref(), "phases": array(strict_object({"phase_id": s(), "phase": enum("pre_contact", "attack", "compression", "friction", "body_resonance", "release", "tail", "debris"), "span": clock, "force_curve_ref": ref(), "source_layer_refs": refs(), "gain_envelope_ref": ref(), "spectral_profile_ref": ref(), "position_track_ref": ref()}), 1), "phase_order_validated": {"const": True}, "visual_contact_bound": {"const": True}},
        ["scope", "foley_event_ref", "phases", "phase_order_validated", "visual_contact_bound"],
    )

    schemas["hyperreal_acoustic_scene_spec.schema.json"] = record_schema(
        "hyperreal-acoustic-scene-spec", "Hyperreal Acoustic Scene Specification", "acoustic_scene_spec_id",
        {"scope": scope, "geometry_ref": ref(), "room_profile_id": s(), "listener_track_ref": ref(), "source_track_refs": refs(), "impulse_response_refs": refs(), "speed_of_sound_mps": {"type": "number", "minimum": 300, "maximum": 380}, "early_reflection_policy_id": s(), "late_reverb_policy_id": s(), "occlusion_policy_id": s(), "distance_attenuation_policy_id": s(), "dry_stems_preserved": {"const": True}},
        ["scope", "geometry_ref", "room_profile_id", "listener_track_ref", "source_track_refs", "impulse_response_refs", "speed_of_sound_mps", "early_reflection_policy_id", "late_reverb_policy_id", "occlusion_policy_id", "distance_attenuation_policy_id", "dry_stems_preserved"],
    )

    spatial_object = strict_object(
        {"audio_object_id": s(), "owner": owner, "stem_ref": ref(), "position_track_ref": ref(), "directivity_profile_id": s(), "distance_curve_ref": ref(), "occlusion_curve_ref": ref(), "gain_automation_ref": ref(), "bus_id": s(), "channel_layout": enum("mono_object", "stereo_bed", "ambisonic_bed")}
    )
    schemas["hyperreal_spatial_audio_object_manifest.schema.json"] = record_schema(
        "hyperreal-spatial-audio-object-manifest", "Hyperreal Spatial Audio Object Manifest", "spatial_audio_object_manifest_id",
        {"scope": scope, "canonical_clock": clock, "acoustic_scene_ref": ref(), "objects": array(spatial_object, 1), "listener_render_profile_id": s(), "sample_rate_hz": {"type": "integer", "enum": [48000, 96000]}, "object_ids_unique": {"const": True}},
        ["scope", "canonical_clock", "acoustic_scene_ref", "objects", "listener_render_profile_id", "sample_rate_hz", "object_ids_unique"],
    )

    stem = strict_object(
        {"stem_id": s(), "event_ids": array(s(), 1, True), "owner": owner, "artifact": artifact, "sample_rate_hz": {"type": "integer", "minimum": 8000}, "channels": {"type": "integer", "minimum": 1, "maximum": 16}, "sample_count": {"type": "integer", "minimum": 1}, "start_sample": {"type": "integer", "minimum": 0}, "dry": {"type": "boolean"}, "source_route_decision_ref": ref(), "processing_recipe_ref": {"oneOf": [ref(), {"type": "null"}]}}
    )
    schemas["hyperreal_audio_stem_manifest.schema.json"] = record_schema(
        "hyperreal-audio-stem-manifest", "Hyperreal Audio Stem Manifest", "audio_stem_manifest_id",
        {"scope": scope, "canonical_clock": clock, "stems": array(stem, 1), "stem_ids_unique": {"const": True}, "all_events_accounted": {"const": True}, "nondestructive_lineage": {"const": True}},
        ["scope", "canonical_clock", "stems", "stem_ids_unique", "all_events_accounted", "nondestructive_lineage"],
    )

    schemas["hyperreal_mix_master_recipe.schema.json"] = record_schema(
        "hyperreal-mix-master-recipe", "Hyperreal Mix and Master Recipe", "mix_master_recipe_id",
        {"scope": scope, "stem_manifest_ref": ref(), "spatial_object_manifest_ref": ref(), "bus_graph_ref": ref(), "automation_ref": ref(), "dialogue_priority_policy_id": s(), "loudness_profile_id": s(), "target_lufs": {"type": "number", "minimum": -40, "maximum": -5}, "true_peak_ceiling_dbtp": {"type": "number", "minimum": -12, "maximum": 0}, "minimum_headroom_db": {"type": "number", "minimum": 0}, "sample_rate_hz": {"type": "integer", "enum": [48000, 96000]}, "dither_policy_id": s(), "dry_stems_preserved": {"const": True}, "render_deterministic": {"type": "boolean"}},
        ["scope", "stem_manifest_ref", "spatial_object_manifest_ref", "bus_graph_ref", "automation_ref", "dialogue_priority_policy_id", "loudness_profile_id", "target_lufs", "true_peak_ceiling_dbtp", "minimum_headroom_db", "sample_rate_hz", "dither_policy_id", "dry_stems_preserved", "render_deterministic"],
    )

    schemas["hyperreal_audio_qa_evaluation.schema.json"] = record_schema(
        "hyperreal-audio-qa-evaluation", "Hyperreal Audio QA Evaluation", "audio_qa_evaluation_id",
        {"scope": scope, "artifact_ref": ref(), "stem_manifest_ref": ref(), "evaluated_span": clock, "metric_results": array(metric, 1), "defects": array(strict_object({"defect_id": s(), "defect_class": s(), "severity": enum("info", "minor", "major", "critical"), "span": clock, "owner": owner, "evidence_ref": ref()})), "critic_observation_refs": refs(), "listening_review_ref": {"oneOf": [ref(), {"type": "null"}]}, "decision": enum("accept", "repair", "reroute", "reject", "human_review"), "uncertainty": {"type": "number", "minimum": 0, "maximum": 1}},
        ["scope", "artifact_ref", "stem_manifest_ref", "evaluated_span", "metric_results", "defects", "critic_observation_refs", "listening_review_ref", "decision", "uncertainty"],
    )

    schemas["hyperreal_audio_span_repair_plan.schema.json"] = record_schema(
        "hyperreal-audio-span-repair-plan", "Hyperreal Local Audio Stem and Event Repair Plan", "audio_span_repair_plan_id",
        {"scope": scope, "audio_qa_ref": ref(), "accepted_audio_parent_ref": ref(), "repairs": array(strict_object({"defect_ids": array(s(), 1, True), "event_ids": array(s(), 1, True), "target_span": clock, "stem_ids": array(s(), 1, True), "method": enum("replace_source", "regenerate_event", "edit_transient", "bounded_time_stretch", "gain_automation", "spectral_repair", "declick", "crossfade", "rerender_acoustics", "remix_only"), "handle_samples_before": {"type": "integer", "minimum": 1}, "handle_samples_after": {"type": "integer", "minimum": 1}, "protected_stem_ids": array(s(), 0, True), "hypothesis_ref": ref()}), 1), "accepted_parent_immutable": {"const": True}, "smallest_failed_scope_only": {"const": True}, "full_mix_regeneration": {"const": False}},
        ["scope", "audio_qa_ref", "accepted_audio_parent_ref", "repairs", "accepted_parent_immutable", "smallest_failed_scope_only", "full_mix_regeneration"],
    )

    schemas["hyperreal_av_sync_evaluation.schema.json"] = record_schema(
        "hyperreal-av-sync-evaluation", "Hyperreal Audio Video Synchronization Evaluation", "av_sync_evaluation_id",
        {"scope": scope, "video_ref": ref(), "audio_ref": ref(), "canonical_clock": clock, "event_results": array(strict_object({"event_id": s(), "event_class": s(), "expected_pts": {"type": "integer", "minimum": 0}, "observed_pts": {"type": "integer", "minimum": 0}, "offset_ms": {"type": "number"}, "tolerance_ms": {"type": "number", "minimum": 0}, "drift_ms_per_minute": {"type": "number"}, "passed": {"type": "boolean"}, "evidence_ref": ref()}), 1), "sample_count_expected": {"type": "integer", "minimum": 1}, "sample_count_observed": {"type": "integer", "minimum": 1}, "frame_count_expected": {"type": "integer", "minimum": 1}, "frame_count_observed": {"type": "integer", "minimum": 1}, "container_timestamps_monotonic": {"type": "boolean"}, "decision": enum("accept", "local_repair", "reject")},
        ["scope", "video_ref", "audio_ref", "canonical_clock", "event_results", "sample_count_expected", "sample_count_observed", "frame_count_expected", "frame_count_observed", "container_timestamps_monotonic", "decision"],
    )

    schemas["hyperreal_av_local_repair_plan.schema.json"] = record_schema(
        "hyperreal-av-local-repair-plan", "Hyperreal Local AV Repair Plan", "av_local_repair_plan_id",
        {"scope": scope, "sync_evaluation_ref": ref(), "accepted_video_parent_ref": ref(), "accepted_audio_parent_ref": ref(), "repairs": array(strict_object({"event_ids": array(s(), 1, True), "target_span": clock, "method": enum("shift_event", "bounded_time_stretch", "silence_pad", "crossfade", "regenerate_audio_event", "rerender_mouth_span", "remux_only"), "maximum_time_stretch_ratio": {"type": "number", "minimum": 0.95, "maximum": 1.05}, "handle_samples_before": {"type": "integer", "minimum": 1}, "handle_samples_after": {"type": "integer", "minimum": 1}, "hypothesis_ref": ref()}), 1), "accepted_parents_immutable": {"const": True}, "smallest_failed_scope_only": {"const": True}, "full_av_rerender": {"const": False}},
        ["scope", "sync_evaluation_ref", "accepted_video_parent_ref", "accepted_audio_parent_ref", "repairs", "accepted_parents_immutable", "smallest_failed_scope_only", "full_av_rerender"],
    )

    schemas["hyperreal_audio_av_promotion_certificate.schema.json"] = record_schema(
        "hyperreal-audio-av-promotion-certificate", "Hyperreal Audio and AV Promotion Certificate", "audio_av_promotion_certificate_id",
        {"artifact_refs": refs(), "scope": scope, "approved_span": clock, "audio_qa_refs": refs(), "av_sync_ref": ref(), "mix_recipe_ref": ref(), "listening_review_ref": ref(), "allowed_uses": array(enum("preview", "intermediate_parent", "final_audio", "review_mux", "av_master"), 1, True), "expires_at": {"type": ["string", "null"], "format": "date-time"}, "revocation_policy_id": s(), "runtime_release_decision_ref": {"oneOf": [ref(), {"type": "null"}]}, "runtime_completion_claimed": {"type": "boolean"}},
        ["artifact_refs", "scope", "approved_span", "audio_qa_refs", "av_sync_ref", "mix_recipe_ref", "listening_review_ref", "allowed_uses", "expires_at", "revocation_policy_id", "runtime_release_decision_ref", "runtime_completion_claimed"],
        all_of=[{
            "if": {"properties": {"runtime_completion_claimed": {"const": True}}, "required": ["runtime_completion_claimed"]},
            "then": {"properties": {"status": {"const": "certified"}, "runtime_release_decision_ref": ref()}},
        }],
    )

    schemas["hyperreal_operator_project.schema.json"] = record_schema(
        "hyperreal-operator-project", "Hyperreal Operator Application Project", "operator_project_id",
        {"project_id": s(), "title": s(), "mode": enum("guided", "director", "expert", "diagnostic"), "character_refs": refs(0), "scene_refs": refs(0), "shot_timeline_refs": refs(0), "run_refs": refs(0), "active_revision": {"type": "integer", "minimum": 0}, "autosave_enabled": {"type": "boolean"}, "raw_paths_exposed": {"const": False}, "credentials_exposed": {"const": False}},
        ["project_id", "title", "mode", "character_refs", "scene_refs", "shot_timeline_refs", "run_refs", "active_revision", "autosave_enabled", "raw_paths_exposed", "credentials_exposed"],
    )

    schemas["hyperreal_application_command.schema.json"] = record_schema(
        "hyperreal-application-command", "Hyperreal Operator Application Command", "application_command_id",
        {"actor_id": s(), "role_id": s(), "command": enum("create_project", "save_draft", "publish_character_revision", "publish_scene_revision", "publish_shot_revision", "compile_run", "start_preview", "request_final_render", "cancel_attempt", "request_repair", "approve_candidate", "reject_candidate", "request_promotion", "request_revocation", "retry_reconciliation", "request_model_phase_transition"), "target_refs": refs(), "parameter_schema_id": s(), "parameters_sha256": sha(), "expected_aggregate_version": {"type": "integer", "minimum": 0}, "idempotency_key": s(), "authorization_ref": ref(), "confirmation_level": enum("none", "confirm", "type_to_confirm"), "offline_created": {"type": "boolean"}, "raw_path_or_credentials_present": {"const": False}, "direct_comfyui_mutation": {"const": False}},
        ["actor_id", "role_id", "command", "target_refs", "parameter_schema_id", "parameters_sha256", "expected_aggregate_version", "idempotency_key", "authorization_ref", "confirmation_level", "offline_created", "raw_path_or_credentials_present", "direct_comfyui_mutation"],
        all_of=[
            {
                "if": {
                    "properties": {"offline_created": {"const": True}},
                    "required": ["offline_created"],
                },
                "then": {
                    "properties": {
                        "command": {"enum": ["create_project", "save_draft"]},
                    },
                },
            }
        ],
    )

    schemas["hyperreal_application_command_authorization.schema.json"] = record_schema(
        "hyperreal-application-command-authorization", "Hyperreal Application Command Authorization", "application_command_authorization_id",
        {"command_ref": ref(), "actor_id": s(), "role_ref": ref(), "policy_revision_ref": ref(), "target_scope_refs": refs(), "decision": enum("allow", "deny", "require_confirmation", "require_additional_evidence"), "reason_codes": array(s(), 1, True), "confirmation_token_hash": {"oneOf": [sha(), {"type": "null"}]}, "expires_at": {"type": "string", "format": "date-time"}, "credential_access_granted": {"const": False}, "direct_runtime_authority_granted": {"const": False}},
        ["command_ref", "actor_id", "role_ref", "policy_revision_ref", "target_scope_refs", "decision", "reason_codes", "confirmation_token_hash", "expires_at", "credential_access_granted", "direct_runtime_authority_granted"],
    )

    schemas["hyperreal_application_command_receipt.schema.json"] = record_schema(
        "hyperreal-application-command-receipt", "Hyperreal Application Command Receipt", "application_command_receipt_id",
        {"command_ref": ref(), "authorization_ref": ref(), "accepted_at": {"type": ["string", "null"], "format": "date-time"}, "result": enum("accepted", "rejected", "duplicate", "conflict", "deferred", "completed", "failed"), "correlation_id": s(), "aggregate_ref": ref(), "aggregate_version_before": {"type": "integer", "minimum": 0}, "aggregate_version_after": {"type": ["integer", "null"], "minimum": 0}, "result_ref": {"oneOf": [ref(), {"type": "null"}]}, "error_code": {"type": ["string", "null"]}, "safe_next_command_ids": array(s(), 0, True), "idempotency_replayed": {"type": "boolean"}},
        ["command_ref", "authorization_ref", "accepted_at", "result", "correlation_id", "aggregate_ref", "aggregate_version_before", "aggregate_version_after", "result_ref", "error_code", "safe_next_command_ids", "idempotency_replayed"],
    )

    schemas["hyperreal_application_query.schema.json"] = record_schema(
        "hyperreal-application-query", "Hyperreal Operator Application Query", "application_query_id",
        {"actor_id": s(), "role_id": s(), "query": enum("project_summary", "character_library", "scene_graph", "shot_timeline", "run_dag", "attempt_detail", "artifact_lineage", "qa_report", "candidate_comparison", "repair_history", "model_explanation", "runtime_workers", "queue_projection", "incident_detail", "audit_history"), "filter_schema_id": s(), "filters_sha256": sha(), "cursor": {"type": ["string", "null"]}, "page_size": {"type": "integer", "minimum": 1, "maximum": 500}, "consistency": enum("eventual_projection", "read_your_writes", "authoritative_snapshot"), "raw_paths_or_credentials_requested": {"const": False}},
        ["actor_id", "role_id", "query", "filter_schema_id", "filters_sha256", "cursor", "page_size", "consistency", "raw_paths_or_credentials_requested"],
    )

    schemas["hyperreal_application_query_page.schema.json"] = record_schema(
        "hyperreal-application-query-page", "Hyperreal Application Query Page and Receipt", "application_query_page_id",
        {"query_ref": ref(), "projection_type": s(), "snapshot_event_sequence": {"type": "integer", "minimum": 0}, "freshness_state": enum("live", "catching_up", "stale", "reconciling", "offline"), "item_schema_id": s(), "item_refs": refs(0), "inline_payload_ref": {"oneOf": [ref(), {"type": "null"}]}, "returned_count": {"type": "integer", "minimum": 0}, "next_cursor": {"type": ["string", "null"]}, "has_more": {"type": "boolean"}, "correlation_id": s(), "authoritative_for_promotion": {"const": False}},
        ["query_ref", "projection_type", "snapshot_event_sequence", "freshness_state", "item_schema_id", "item_refs", "inline_payload_ref", "returned_count", "next_cursor", "has_more", "correlation_id", "authoritative_for_promotion"],
    )

    schemas["hyperreal_application_realtime_event.schema.json"] = record_schema(
        "hyperreal-application-realtime-event", "Hyperreal Application Realtime Event and Gap-Recovery Envelope", "application_realtime_event_id",
        {"subscription_id": s(), "connection_epoch": {"type": "integer", "minimum": 0}, "event_sequence": {"type": "integer", "minimum": 0}, "previous_event_sequence": {"type": ["integer", "null"], "minimum": 0}, "event_type": enum("projection_changed", "command_status", "run_progress", "attempt_progress", "artifact_registered", "qa_changed", "incident_changed", "heartbeat", "gap_detected", "resume_required"), "aggregate_ref": ref(), "payload_schema_id": s(), "payload_sha256": sha(), "payload_ref": ref(), "resume_cursor": s(), "gap_detected": {"type": "boolean"}, "authoritative_for_transition": {"const": False}},
        ["subscription_id", "connection_epoch", "event_sequence", "previous_event_sequence", "event_type", "aggregate_ref", "payload_schema_id", "payload_sha256", "payload_ref", "resume_cursor", "gap_detected", "authoritative_for_transition"],
    )

    schemas["hyperreal_application_realtime_resume.schema.json"] = record_schema(
        "hyperreal-application-realtime-resume", "Hyperreal Application Realtime Resume and Gap-Recovery Request", "application_realtime_resume_id",
        {"subscription_id": s(), "actor_id": s(), "last_applied_event_sequence": {"type": "integer", "minimum": 0}, "resume_cursor": s(), "requested_projection_ids": array(s(), 1, True), "gap_policy": enum("replay_events", "refresh_projections", "authoritative_snapshot"), "maximum_replay_events": {"type": "integer", "minimum": 1, "maximum": 100000}, "raw_runtime_access_requested": {"const": False}},
        ["subscription_id", "actor_id", "last_applied_event_sequence", "resume_cursor", "requested_projection_ids", "gap_policy", "maximum_replay_events", "raw_runtime_access_requested"],
    )

    schemas["hyperreal_application_projection.schema.json"] = record_schema(
        "hyperreal-application-projection", "Hyperreal Operator Application Projection", "application_projection_id",
        {"projection_type": s(), "aggregate_ref": ref(), "aggregate_version": {"type": "integer", "minimum": 0}, "event_sequence": {"type": "integer", "minimum": 0}, "generated_at": {"type": "string", "format": "date-time"}, "freshness_state": enum("live", "catching_up", "stale", "reconciling", "offline"), "payload_schema_id": s(), "payload_sha256": sha(), "source_event_refs": refs(), "authoritative_for_promotion": {"const": False}},
        ["projection_type", "aggregate_ref", "aggregate_version", "event_sequence", "generated_at", "freshness_state", "payload_schema_id", "payload_sha256", "source_event_refs", "authoritative_for_promotion"],
    )

    nav_item = strict_object(
        {"route_id": s(), "label": s(), "surface": enum("controller_console", "comfyui_app_mode", "comfyui_frontend_extension"), "parent_route_id": {"type": ["string", "null"]}, "required_role_ids": array(s(), 1, True), "query_ids": array(s(), 0, True), "command_ids": array(s(), 0, True), "empty_state_id": s(), "error_state_ids": array(s(), 1, True), "responsive": {"const": True}}
    )
    schemas["hyperreal_application_navigation_manifest.schema.json"] = record_schema(
        "hyperreal-application-navigation-manifest", "Hyperreal Operator Application Navigation Manifest", "application_navigation_manifest_id",
        {"routes": array(nav_item, 1), "route_ids_unique": {"const": True}, "all_controls_bound": {"const": True}, "default_route_id": s(), "mode_visibility_policy_id": s()},
        ["routes", "route_ids_unique", "all_controls_bound", "default_route_id", "mode_visibility_policy_id"],
    )

    schemas["hyperreal_application_control_definition.schema.json"] = record_schema(
        "hyperreal-application-control-definition", "Hyperreal Application Control Definition", "application_control_definition_id",
        {"control_id": s(), "label": s(), "description": s(), "control_type": enum("text", "number", "select", "multiselect", "toggle", "asset_picker", "character_picker", "timeline", "range", "button", "command_menu", "read_only_metric", "media_viewer"), "value_schema_id": s(), "default_value_ref": {"oneOf": [ref(), {"type": "null"}]}, "validation_policy_id": s(), "visibility_modes": array(enum("guided", "director", "expert", "diagnostic"), 1, True), "required_role_ids": array(s(), 1, True), "sensitive": {"const": False}, "raw_path": {"const": False}, "accessibility_label": s(), "help_topic_id": s()},
        ["control_id", "label", "description", "control_type", "value_schema_id", "default_value_ref", "validation_policy_id", "visibility_modes", "required_role_ids", "sensitive", "raw_path", "accessibility_label", "help_topic_id"],
    )

    schemas["hyperreal_application_control_binding.schema.json"] = record_schema(
        "hyperreal-application-control-binding", "Hyperreal Application Control-to-Domain Command/Query Binding", "application_control_binding_id",
        {"control_ref": ref(), "route_id": s(), "domain_field_schema_id": s(), "read_query_id": {"type": ["string", "null"]}, "write_command_id": {"type": ["string", "null"]}, "parameter_mapping_ref": ref(), "compatibility_gate_ids": array(s(), 0, True), "authority_policy_id": s(), "surface": enum("controller_console", "comfyui_app_mode", "comfyui_frontend_extension"), "binding_test_ref": ref(), "dead_control": {"const": False}},
        ["control_ref", "route_id", "domain_field_schema_id", "read_query_id", "write_command_id", "parameter_mapping_ref", "compatibility_gate_ids", "authority_policy_id", "surface", "binding_test_ref", "dead_control"],
    )

    schemas["hyperreal_timeline_edit_transaction.schema.json"] = record_schema(
        "hyperreal-timeline-edit-transaction", "Hyperreal Operator Timeline Edit Request", "timeline_edit_transaction_id",
        {"project_ref": ref(), "actor_id": s(), "base_timeline_ref": ref(), "expected_revision": {"type": "integer", "minimum": 0}, "operations": array(strict_object({"operation_id": s(), "operation": enum("insert", "move", "trim", "split", "merge", "bind", "unbind", "replace", "annotate"), "track_id": s(), "target_ids": array(s(), 1, True), "span": clock, "payload_schema_id": s(), "payload_sha256": sha()}), 1), "conflict_policy": enum("reject", "rebase_preview", "manual_merge"), "idempotency_key": s()},
        ["project_ref", "actor_id", "base_timeline_ref", "expected_revision", "operations", "conflict_policy", "idempotency_key"],
    )

    schemas["hyperreal_timeline_edit_result.schema.json"] = record_schema(
        "hyperreal-timeline-edit-result", "Hyperreal Operator Timeline Edit Result and Conflict Receipt", "timeline_edit_result_id",
        {"transaction_ref": ref(), "result": enum("applied", "rejected", "conflict", "rebase_preview", "manual_merge_required", "duplicate"), "base_revision": {"type": "integer", "minimum": 0}, "result_revision": {"type": ["integer", "null"], "minimum": 1}, "result_timeline_ref": {"oneOf": [ref(), {"type": "null"}]}, "conflict_refs": refs(0), "merge_preview_ref": {"oneOf": [ref(), {"type": "null"}]}, "undo_transaction_ref": {"oneOf": [ref(), {"type": "null"}]}, "correlation_id": s()},
        ["transaction_ref", "result", "base_revision", "result_revision", "result_timeline_ref", "conflict_refs", "merge_preview_ref", "undo_transaction_ref", "correlation_id"],
    )

    schemas["hyperreal_app_mode_launch_request.schema.json"] = record_schema(
        "hyperreal-app-mode-launch-request", "Hyperreal Controller-Issued ComfyUI App Mode Launch Request", "app_mode_launch_request_id",
        {"actor_id": s(), "launcher_id": s(), "workflow_release_ref": ref(), "runtime_lock_ref": ref(), "input_package_refs": refs(), "allowed_output_schema_ids": array(s(), 1, True), "gateway_token_hash": sha(), "gateway_token_expires_at": {"type": "string", "format": "date-time"}, "controller_callback_id": s(), "production_promotion_allowed": {"const": False}, "direct_controller_database_access": {"const": False}},
        ["actor_id", "launcher_id", "workflow_release_ref", "runtime_lock_ref", "input_package_refs", "allowed_output_schema_ids", "gateway_token_hash", "gateway_token_expires_at", "controller_callback_id", "production_promotion_allowed", "direct_controller_database_access"],
    )

    schemas["hyperreal_app_mode_launch_receipt.schema.json"] = record_schema(
        "hyperreal-app-mode-launch-receipt", "Hyperreal ComfyUI App Mode Launch and Return Receipt", "app_mode_launch_receipt_id",
        {"launch_request_ref": ref(), "result": enum("opened", "submitted", "cancelled", "completed", "failed", "expired"), "comfyui_submission_ref": {"oneOf": [ref(), {"type": "null"}]}, "execution_receipt_ref": {"oneOf": [ref(), {"type": "null"}]}, "returned_artifact_refs": refs(0), "returned_payload_schema_ids": array(s(), 0, True), "callback_receipt_ref": {"oneOf": [ref(), {"type": "null"}]}, "correlation_id": s(), "promotion_performed": {"const": False}},
        ["launch_request_ref", "result", "comfyui_submission_ref", "execution_receipt_ref", "returned_artifact_refs", "returned_payload_schema_ids", "callback_receipt_ref", "correlation_id", "promotion_performed"],
    )

    schemas["hyperreal_artifact_comparison_session.schema.json"] = record_schema(
        "hyperreal-artifact-comparison-session", "Hyperreal Artifact Comparison Session", "artifact_comparison_session_id",
        {
            "scope": scope,
            "candidate_refs": refs(2),
            "comparison_mode": enum("side_by_side", "wipe", "onion_skin", "difference", "flicker", "audio_ab", "audio_null", "av_sync_overlay"),
            "synchronized_playback": {"const": True},
            "blind_labels": {"type": "boolean"},
            "metric_overlay_ids": array(s(), 1, True),
            "route_explanation_refs": refs(),
            "operator_annotations_ref": {"oneOf": [ref(), {"type": "null"}]},
            "decision_command_ref": {"oneOf": [ref(), {"type": "null"}]},
        },
        ["scope", "candidate_refs", "comparison_mode", "synchronized_playback", "blind_labels", "metric_overlay_ids", "route_explanation_refs", "operator_annotations_ref", "decision_command_ref"],
    )

    schemas["hyperreal_repair_review_session.schema.json"] = record_schema(
        "hyperreal-repair-review-session", "Hyperreal Repair Review Session", "repair_review_session_id",
        {"scope": scope, "qa_evaluation_refs": refs(), "accepted_parent_refs": refs(), "repair_plan_ref": ref(), "before_after_session_ref": ref(), "protected_region_overlays": refs(), "boundary_handle_preview_refs": refs(), "hypothesis_explanation_ref": ref(), "allowed_commands": array(enum("approve_candidate", "reject_candidate", "request_repair"), 1, True), "promotion_authority": {"const": False}},
        ["scope", "qa_evaluation_refs", "accepted_parent_refs", "repair_plan_ref", "before_after_session_ref", "protected_region_overlays", "boundary_handle_preview_refs", "hypothesis_explanation_ref", "allowed_commands", "promotion_authority"],
    )

    schemas["hyperreal_runtime_incident_projection.schema.json"] = record_schema(
        "hyperreal-runtime-incident-projection", "Hyperreal Runtime Incident Projection", "runtime_incident_projection_id",
        {"incident_ref": ref(), "severity": enum("info", "warning", "error", "critical"), "state": enum("detected", "contained", "reconciling", "waiting_external", "resolved", "closed"), "affected_refs": refs(), "worker_lease_refs": refs(0), "last_known_receipt_refs": refs(0), "safe_operator_commands": array(s(), 0, True), "automatic_actions": array(s(), 0, True), "data_loss_risk": enum("none", "unknown", "possible", "confirmed"), "promotion_blocked": {"type": "boolean"}},
        ["incident_ref", "severity", "state", "affected_refs", "worker_lease_refs", "last_known_receipt_refs", "safe_operator_commands", "automatic_actions", "data_loss_risk", "promotion_blocked"],
        all_of=[{
            "if": {"properties": {"state": {"enum": ["detected", "contained", "reconciling", "waiting_external"]}}, "required": ["state"]},
            "then": {"properties": {"promotion_blocked": {"const": True}}},
        }],
    )

    schemas["hyperreal_model_explanation_projection.schema.json"] = record_schema(
        "hyperreal-model-explanation-projection", "Hyperreal Model Selection Explanation Projection", "model_explanation_projection_id",
        {"selection_decision_ref": ref(), "selected_bundle_ref": {"oneOf": [ref(), {"type": "null"}]}, "pass_intent": s(), "eligible_count": {"type": "integer", "minimum": 0}, "filtered_reasons": array(strict_object({"bundle_ref": ref(), "reason_codes": array(s(), 1, True)})), "rank_features": array(strict_object({"feature_id": s(), "normalized_value": {"type": "number", "minimum": 0, "maximum": 1}, "weight": {"type": "number"}, "contribution": {"type": "number"}, "evidence_ref": ref()})), "uncertainty": {"type": "number", "minimum": 0, "maximum": 1}, "plain_language_summary": s(), "operator_preference_policy": enum("none", "eligible_candidate_preference_only", "diagnostic_forced_nonpromotable"), "preference_scope_ref": {"oneOf": [ref(), {"type": "null"}]}, "authoritative_for_selection": {"const": False}},
        ["selection_decision_ref", "selected_bundle_ref", "pass_intent", "eligible_count", "filtered_reasons", "rank_features", "uncertainty", "plain_language_summary", "operator_preference_policy", "preference_scope_ref", "authoritative_for_selection"],
    )

    schemas["hyperreal_app_role_permission.schema.json"] = record_schema(
        "hyperreal-app-role-permission", "Hyperreal Operator Application Role Permission", "app_role_permission_id",
        {"role_id": s(), "permissions": array(enum("read_projects", "edit_drafts", "compile_runs", "start_preview", "request_final_render", "cancel_attempt", "review_qa", "request_repair", "approve_candidate", "request_promotion", "request_revocation", "manage_models", "manage_runtime", "manage_policy", "view_diagnostics"), 1, True), "command_ids": array(s(), 0, True), "query_ids": array(s(), 1, True), "credential_access": {"const": False}, "direct_database_write": {"const": False}, "direct_comfyui_queue_write": {"const": False}, "policy_ref": ref()},
        ["role_id", "permissions", "command_ids", "query_ids", "credential_access", "direct_database_write", "direct_comfyui_queue_write", "policy_ref"],
    )

    schemas["hyperreal_application_command_eligibility.schema.json"] = record_schema(
        "hyperreal-application-command-eligibility", "Hyperreal Application Command Eligibility Projection", "application_command_eligibility_id",
        {"actor_id": s(), "role_refs": refs(), "aggregate_ref": ref(), "aggregate_version": {"type": "integer", "minimum": 0}, "command_states": array(strict_object({"command_id": s(), "eligible": {"type": "boolean"}, "disabled_reason_codes": array(s(), 0, True), "confirmation_level": enum("none", "confirm", "type_to_confirm"), "prerequisite_refs": refs(0)}), 1), "projection_event_sequence": {"type": "integer", "minimum": 0}, "freshness_state": enum("live", "catching_up", "stale", "reconciling", "offline"), "authoritative_authorization": {"const": False}},
        ["actor_id", "role_refs", "aggregate_ref", "aggregate_version", "command_states", "projection_event_sequence", "freshness_state", "authoritative_authorization"],
    )

    schemas["hyperreal_application_error_envelope.schema.json"] = record_schema(
        "hyperreal-application-error-envelope", "Hyperreal Application Error Envelope", "application_error_envelope_id",
        {"correlation_id": s(), "error_class": enum("validation", "authorization", "conflict", "dependency_missing", "runtime_unavailable", "submission_ambiguous", "lease_lost", "artifact_missing", "qa_blocked", "promotion_blocked", "model_unqualified", "mask_authority_missing", "projection_stale", "offline"), "error_code": s(), "title": s(), "plain_language_detail": s(), "affected_refs": refs(), "retryable": {"type": "boolean"}, "preserve_operator_input": {"const": True}, "safe_next_command_ids": array(s(), 0, True), "evidence_refs": refs(0), "secret_or_raw_path_present": {"const": False}},
        ["correlation_id", "error_class", "error_code", "title", "plain_language_detail", "affected_refs", "retryable", "preserve_operator_input", "safe_next_command_ids", "evidence_refs", "secret_or_raw_path_present"],
    )

    schemas["hyperreal_application_notification.schema.json"] = record_schema(
        "hyperreal-application-notification", "Hyperreal Application Notification", "application_notification_id",
        {"actor_id": s(), "notification_class": enum("command_result", "review_required", "dependency_blocked", "run_terminal", "incident", "certificate_expiry", "projection_stale", "storage_threshold"), "severity": enum("info", "success", "warning", "error", "critical"), "title": s(), "summary": s(), "target_ref": ref(), "deep_link_route_id": s(), "correlation_id": s(), "deduplication_key": s(), "requires_acknowledgement": {"type": "boolean"}, "secret_or_raw_path_present": {"const": False}},
        ["actor_id", "notification_class", "severity", "title", "summary", "target_ref", "deep_link_route_id", "correlation_id", "deduplication_key", "requires_acknowledgement", "secret_or_raw_path_present"],
    )

    schemas["hyperreal_application_feature_flag_snapshot.schema.json"] = record_schema(
        "hyperreal-application-feature-flag-snapshot", "Hyperreal Application Feature Flag Snapshot", "application_feature_flag_snapshot_id",
        {"application_version": s(), "actor_role_ids": array(s(), 1, True), "flags": array(strict_object({"flag_id": s(), "enabled": {"type": "boolean"}, "release_tier": enum("controller_core", "controller_plus_app_mode", "full_hybrid"), "reason_code": s(), "expires_at": {"type": ["string", "null"], "format": "date-time"}}), 1), "flag_ids_unique": {"const": True}, "policy_ref": ref()},
        ["application_version", "actor_role_ids", "flags", "flag_ids_unique", "policy_ref"],
    )

    schemas["hyperreal_application_accessibility_preferences.schema.json"] = record_schema(
        "hyperreal-application-accessibility-preferences", "Hyperreal Application Accessibility Preferences", "application_accessibility_preferences_id",
        {"actor_id": s(), "reduced_motion": {"type": "boolean"}, "high_contrast": {"type": "boolean"}, "font_scale_percent": {"type": "integer", "minimum": 100, "maximum": 300}, "captions_default": {"type": "boolean"}, "transcripts_default": {"type": "boolean"}, "non_color_status_patterns": {"const": True}, "waveform_alternative": enum("table", "summary", "both"), "timeline_alternative": enum("table", "list", "both"), "keyboard_shortcut_profile_id": s(), "screen_reader_live_updates": enum("off", "important", "all")},
        ["actor_id", "reduced_motion", "high_contrast", "font_scale_percent", "captions_default", "transcripts_default", "non_color_status_patterns", "waveform_alternative", "timeline_alternative", "keyboard_shortcut_profile_id", "screen_reader_live_updates"],
    )

    schemas["hyperreal_comfyui_app_launcher_manifest.schema.json"] = record_schema(
        "hyperreal-comfyui-app-launcher-manifest", "Hyperreal ComfyUI App Mode Launcher Manifest", "comfyui_app_launcher_manifest_id",
        {"launcher_id": s(), "purpose": enum("character_calibration", "mask_inspection", "image_preview", "video_span_preview", "voice_preview", "audio_event_preview"), "canonical_ui_workflow_ref": ref(), "flattened_api_workflow_ref": ref(), "workflow_release_ref": ref(), "compatible_runtime_lock_refs": refs(), "controller_command_id": s(), "input_bindings_ref": ref(), "output_bindings_ref": ref(), "launch_authorization_schema_id": s(), "result_receipt_schema_id": s(), "authority_ceiling": {"const": "unpromoted_candidate_generation_only"}, "cancellation_policy_id": s(), "minimum_frontend_version": s(), "minimum_core_version": s(), "runtime_test_refs": refs(), "accessibility_test_refs": refs()},
        ["launcher_id", "purpose", "canonical_ui_workflow_ref", "flattened_api_workflow_ref", "workflow_release_ref", "compatible_runtime_lock_refs", "controller_command_id", "input_bindings_ref", "output_bindings_ref", "launch_authorization_schema_id", "result_receipt_schema_id", "authority_ceiling", "cancellation_policy_id", "minimum_frontend_version", "minimum_core_version", "runtime_test_refs", "accessibility_test_refs"],
    )

    schemas["hyperreal_multi_character_editor_projection.schema.json"] = record_schema(
        "hyperreal-multi-character-editor-projection", "Hyperreal Multi-Character Spatial Ownership Editor Projection", "multi_character_editor_projection_id",
        {"scope": scope, "instance_cards": array(strict_object({"character_instance_id": s(), "character_package_ref": ref(), "stable_color_token": s(), "stable_pattern_token": s(), "bbox_xywh_normalized": array({"type": "number", "minimum": 0, "maximum": 1}, 4), "skeleton_ref": ref(), "depth_order": {"type": "integer", "minimum": 0}, "render_order": {"type": "integer", "minimum": 0}, "provider_person_index": {"type": "integer", "minimum": 0}, "visibility": {"type": "number", "minimum": 0, "maximum": 1}, "wardrobe_ref": ref(), "voice_ref": ref(), "target_mask_refs": refs(0), "protected_mask_refs": refs(0)}), 1), "contact_graph_ref": ref(), "mode_a_mask_refs": refs(0), "mode_b_draft_mask_refs": refs(0), "transform_roundtrip_refs": refs(0), "validation_issue_refs": refs(0), "projection_only": {"const": True}},
        ["scope", "instance_cards", "contact_graph_ref", "mode_a_mask_refs", "mode_b_draft_mask_refs", "transform_roundtrip_refs", "validation_issue_refs", "projection_only"],
    )

    schemas["hyperreal_release_readiness_projection.schema.json"] = record_schema(
        "hyperreal-release-readiness-projection", "Hyperreal Release Readiness Projection", "release_readiness_projection_id",
        {"candidate_refs": refs(), "gate_results": array(strict_object({"gate_id": s(), "gate_revision": s(), "state": enum("pass", "fail", "blocked", "not_run", "expired"), "blocking": {"type": "boolean"}, "evidence_refs": refs(0), "reason_codes": array(s(), 0, True)}), 1), "all_blocking_gates_pass": {"type": "boolean"}, "promotion_request_eligible": {"type": "boolean"}, "actual_promotion_state": enum("not_requested", "requested", "approved", "rejected", "revoked"), "projection_only": {"const": True}},
        ["candidate_refs", "gate_results", "all_blocking_gates_pass", "promotion_request_eligible", "actual_promotion_state", "projection_only"],
    )

    schemas["hyperreal_operator_audit_export_manifest.schema.json"] = record_schema(
        "hyperreal-operator-audit-export-manifest", "Hyperreal Operator Audit Export Manifest", "operator_audit_export_manifest_id",
        {"requester_id": s(), "scope_refs": refs(), "start_event_sequence": {"type": "integer", "minimum": 0}, "end_event_sequence": {"type": "integer", "minimum": 0}, "included_record_types": array(s(), 1, True), "redaction_policy_id": s(), "credential_material_included": {"const": False}, "raw_absolute_paths_included": {"const": False}, "export_artifact": artifact, "export_sha256": sha(), "completeness_evidence_ref": ref()},
        ["requester_id", "scope_refs", "start_event_sequence", "end_event_sequence", "included_record_types", "redaction_policy_id", "credential_material_included", "raw_absolute_paths_included", "export_artifact", "export_sha256", "completeness_evidence_ref"],
    )

    schemas["hyperreal_application_release_manifest.schema.json"] = record_schema(
        "hyperreal-application-release-manifest", "Hyperreal Operator Application Release Manifest", "application_release_manifest_id",
        {"application_version": s(), "controller_api_revision": s(), "schema_catalog_ref": ref(), "navigation_manifest_ref": ref(), "command_authority_registry_ref": ref(), "comfyui_frontend_min_version": s(), "comfyui_core_min_version": s(), "release_tier": enum("controller_core", "controller_plus_app_mode", "full_hybrid"), "surface_releases": array(strict_object({"surface": enum("controller_console", "comfyui_app_mode", "comfyui_frontend_extension"), "release_ref": ref(), "required_for_tier": {"type": "boolean"}, "test_evidence_refs": refs()}), 1), "contract_test_refs": refs(), "component_test_refs": refs(), "e2e_test_refs": refs(), "accessibility_evidence_refs": refs(), "visual_regression_refs": refs(), "fault_injection_refs": refs(), "performance_evidence_refs": refs(), "release_decision_ref": ref(), "runtime_completion_claimed": {"type": "boolean"}},
        ["application_version", "controller_api_revision", "schema_catalog_ref", "navigation_manifest_ref", "command_authority_registry_ref", "comfyui_frontend_min_version", "comfyui_core_min_version", "release_tier", "surface_releases", "contract_test_refs", "component_test_refs", "e2e_test_refs", "accessibility_evidence_refs", "visual_regression_refs", "fault_injection_refs", "performance_evidence_refs", "release_decision_ref", "runtime_completion_claimed"],
        all_of=[{
            "if": {"properties": {"runtime_completion_claimed": {"const": True}}, "required": ["runtime_completion_claimed"]},
            "then": {"properties": {"status": {"const": "certified"}}},
        }],
    )

    return schemas


def build_registries() -> dict[str, dict[str, Any]]:
    common = {"schema_version": "1.0.0", "updated_at": UPDATED_AT, "runtime_completion_claimed": False}
    return {
        "wave64_hyperreal_video_realism_policy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_video_realism_policy_registry_v1",
            "dimensions": [
                {"id": "identity_temporal_stability", "blocking": True, "metrics": ["view_conditioned_identity_similarity", "track_identity_switch_rate"]},
                {"id": "anatomy_pose_dynamics", "blocking": True, "metrics": ["landmark_error", "joint_acceleration_outlier_rate", "hand_anatomy_failure_rate"]},
                {"id": "surface_texture_lock", "blocking": True, "metrics": ["surface_warp_residual", "pore_hair_detail_flicker", "material_phase_slip"]},
                {"id": "camera_optics", "blocking": True, "metrics": ["camera_path_jerk", "rolling_shutter_consistency", "motion_blur_exposure_consistency", "focus_breathing_discontinuity"]},
                {"id": "lighting_color_exposure", "blocking": True, "metrics": ["luminance_flicker_spectrum", "white_balance_delta", "color_transform_roundtrip_error"]},
                {"id": "motion_physics_contact", "blocking": True, "metrics": ["optical_flow_residual", "contact_slip", "penetration_rate", "secondary_motion_phase_error"]},
                {"id": "composition_ownership", "blocking": True, "metrics": ["instance_merge_rate", "occlusion_order_error", "frame_boundary_violation"]},
                {"id": "long_form_continuity", "blocking": True, "metrics": ["state_ledger_conflict_rate", "wardrobe_prop_drift", "shot_boundary_discontinuity"]},
                {"id": "perceptual_realism", "blocking": True, "metrics": ["calibrated_vlm_realism", "blind_human_preference", "artifact_detection_rate"]},
            ],
            "rule": "no_weighted_average_may_hide_a_blocking_dimension_failure",
        },
        "wave64_hyperreal_video_engine_pass_policy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_video_engine_pass_policy_registry_v1",
            "route_intents": ["keyframe_to_video", "image_to_video", "text_to_video", "reference_video_guided", "interpolation", "extension", "localized_span_repair", "temporal_refine", "upscale"],
            "hard_filters": ["exact_bundle_installed", "workflow_release_compatible", "runtime_lock_compatible", "input_mode_supported", "resolution_duration_supported", "character_reference_supported", "control_maps_supported", "certificate_scope_current", "resource_envelope_available"],
            "rank_features": ["task_quality", "identity_preservation", "temporal_stability", "motion_adherence", "physics_quality", "repair_locality", "cross_engine_continuity", "runtime_cost", "evidence_freshness", "uncertainty"],
            "ties": "bounded_branch_compare", "missing_evidence": "abstain_or_shadow_only", "planned_stack_eligible": False,
        },
        "wave64_hyperreal_motion_physics_policy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_motion_physics_policy_registry_v1",
            "motion_classes": ["primary", "micro", "secondary", "contact", "camera", "stabilization"],
            "required_relations": ["cause_before_response", "mass_damping_lag", "contact_no_slip_unless_declared", "no_interpenetration", "hair_fabric_inertia", "breath_body_voice_phase", "blink_gaze_head_coordination"],
            "screen_space_noise_as_surface_detail": "forbidden",
        },
        "wave64_hyperreal_temporal_defect_and_repair_registry.json": {
            **common, "registry_id": "wave64_hyperreal_temporal_defect_and_repair_registry_v1",
            "defect_classes": ["identity_drift", "anatomy_pop", "texture_swim", "flicker", "camera_jump", "motion_stutter", "contact_slip", "penetration", "mask_boundary", "color_shift", "duplicate_instance", "missing_instance", "shot_boundary", "audio_visual_mismatch"],
            "repair_invariants": ["accepted_parent_immutable", "smallest_failed_span", "handles_required", "boundary_keyframes_protected", "materially_new_hypothesis", "protected_masks_required", "post_repair_whole_clip_qa"],
        },
        "wave64_hyperreal_longform_continuity_registry.json": {
            **common, "registry_id": "wave64_hyperreal_longform_continuity_registry_v1",
            "domains": ["identity", "anatomy", "skin", "hair", "wardrobe", "prop", "environment", "lighting", "camera", "pose", "contact", "fatigue", "breathing", "damage", "wetness", "makeup"],
            "persistence_scopes": ["frame", "shot", "scene", "sequence", "project"], "unresolved_conflict_promotable": False,
        },
        "wave64_hyperreal_audio_source_strategy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_audio_source_strategy_registry_v1",
            "origin_classes": ["field_recording", "studio_foley_recording", "voice_performance_recording", "procedural_render", "neural_text_conditioned", "neural_audio_conditioned", "neural_video_conditioned", "hybrid_composite"],
            "realization_actions": ["retrieve_reuse", "record_new", "generate_new", "synthesize_procedural", "assemble_layers"],
            "derivation_states": ["raw", "segmented", "prepared", "transformed", "layered", "spatially_rendered", "mastered"],
            "best_fit_examples": [
                {"event": "known_short_transient", "preferred": ["retrieve_reuse", "studio_foley_recording"]},
                {"event": "parameterized_repetition", "preferred": ["synthesize_procedural", "assemble_layers"]},
                {"event": "novel_long_semantic_ambience", "preferred": ["generate_new", "assemble_layers"]},
                {"event": "hero_multiphase_contact", "preferred": ["assemble_layers", "record_new"]},
            ],
            "rule": "route_per_event_not_per_project; generated_is_not_assumed_superior",
        },
        "wave64_hyperreal_voice_performance_policy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_voice_performance_policy_registry_v1",
            "stages": ["text_normalization", "pronunciation", "performance_plan", "dry_generation", "alignment", "identity_qa", "nonverbal_layer", "viseme_binding", "acoustic_render", "mix", "av_qa"],
            "identity_metrics": ["speaker_similarity", "cross_utterance_consistency", "emotion_conditioned_identity", "pronunciation_accuracy"],
            "performance_metrics": ["prosody_adherence", "breath_naturalness", "nonverbal_timing", "intelligibility", "artifact_rate"],
            "acoustic_effects_before_dry_promotion": "forbidden",
        },
        "wave64_hyperreal_foley_acoustic_spatial_policy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_foley_acoustic_spatial_policy_registry_v1",
            "foley_features": ["material_pair", "force_curve", "contact_area", "velocity", "surface_state", "body_or_object_resonance", "position", "occlusion"],
            "acoustic_features": ["direct_path", "early_reflections", "late_reverb", "source_directivity", "distance_attenuation", "air_absorption", "obstruction", "listener_motion"],
            "dry_stem_preservation_required": True, "camera_pan_without_geometry_evidence": "diagnostic_only",
        },
        "wave64_hyperreal_mix_master_av_policy_registry.json": {
            **common, "registry_id": "wave64_hyperreal_mix_master_av_policy_registry_v1",
            "mix_checks": ["sample_peak", "true_peak", "integrated_loudness", "short_term_loudness", "loudness_range", "dialogue_intelligibility", "spectral_masking", "phase_correlation", "noise_floor", "click_pop", "loop_seam"],
            "sync_classes": {"dialogue_viseme": 45, "hard_impact": 25, "foley_contact": 35, "breath_body": 80, "ambience": 250},
            "canonical_sample_rates_hz": [48000, 96000], "local_time_stretch_bounds": [0.95, 1.05], "container_duration_is_not_authority": True,
        },
        "wave64_hyperreal_critic_calibration_registry.json": {
            **common, "registry_id": "wave64_hyperreal_critic_calibration_registry_v1",
            "critic_classes": ["deterministic_metric", "vision_geometry", "identity", "temporal", "physics", "audio_signal", "speech", "spatial_audio", "av_sync", "vlm", "human_blind_review"],
            "requirements": ["versioned_dataset", "held_out_partition", "confidence_intervals", "false_accept_rate", "false_reject_rate", "domain_slice_reporting", "drift_monitoring"],
            "llm_or_vlm_self_promotion": False,
        },
        "wave64_operator_application_information_architecture_registry.json": {
            **common, "registry_id": "wave64_operator_application_information_architecture_registry_v1",
            "primary_routes": ["home", "projects", "character_library", "scene_builder", "shot_timeline", "pose_and_masks", "image_workspace", "video_workspace", "audio_workspace", "av_workspace", "runs", "qa_and_compare", "models_and_capabilities", "runtime_and_workers", "assets", "settings_and_admin"],
            "operator_modes": ["guided", "director", "expert", "diagnostic"],
            "default_surface": "controller_console", "workflow_quick_surface": "comfyui_app_mode", "node_debug_surface": "comfyui_frontend_extension_or_native_graph",
        },
        "wave64_operator_command_query_authority_registry.json": {
            **common, "registry_id": "wave64_operator_command_query_authority_registry_v1",
            "command_authority": "validated_command_to_controller_only", "query_authority": "projection_or_authoritative_snapshot", "direct_browser_to_comfyui_prompt": False,
            "never_ui_authority": ["certificate_issue", "qa_self_override", "registry_mutation", "credential_read", "direct_database_write", "direct_artifact_promotion"],
            "destructive_commands_require": ["role_permission", "fresh_aggregate_version", "idempotency_key", "confirmation", "audit_event"],
        },
        "wave64_operator_application_state_error_registry.json": {
            **common, "registry_id": "wave64_operator_application_state_error_registry_v1",
            "view_states": ["loading", "empty", "ready", "dirty", "saving", "queued", "running", "cancelling", "reconciling", "blocked", "failed", "offline", "stale", "completed"],
            "required_error_classes": ["validation", "authorization", "conflict", "dependency_missing", "runtime_unavailable", "submission_ambiguous", "lease_lost", "artifact_missing", "qa_blocked", "promotion_blocked", "model_unqualified", "mask_authority_missing"],
            "rules": ["preserve_user_input", "show_safe_next_action", "never_hide_partial_failure", "never_offer_unsafe_retry", "expose_evidence_and_correlation_id"],
        },
        "wave64_operator_surface_deployment_registry.json": {
            **common, "registry_id": "wave64_operator_surface_deployment_registry_v1",
            "decision": "hybrid_controller_console_plus_small_app_mode_workflows_plus_optional_frontend_extension",
            "controller_console": {"owns": ["projects", "multi_workflow_dag", "timeline", "qa", "compare", "repair", "model_reports", "runtime", "audit"], "required": True},
            "comfyui_app_mode": {"owns": ["single_workflow_inputs", "single_workflow_outputs", "quick_preview", "workflow_share"], "required": True},
            "frontend_extension": {"owns": ["deep_link", "node_diagnostics", "controller_status_badges", "artifact_open"], "required": False},
        },
        "wave64_operator_application_release_test_registry.json": {
            **common, "registry_id": "wave64_operator_application_release_test_registry_v1",
            "test_layers": ["schema", "unit", "component", "contract", "integration", "state_machine", "fault_injection", "visual_regression", "accessibility", "performance", "security", "e2e_media", "usability"],
            "required_faults": ["websocket_disconnect", "controller_restart", "comfyui_restart", "duplicate_command", "stale_version", "lease_loss", "unknown_submission", "artifact_hash_mismatch", "worker_disk_full", "model_unload", "projection_lag"],
            "accessibility_target": "WCAG_2_2_AA", "keyboard_complete": True, "reduced_motion": True, "color_not_sole_signal": True,
        },
        "wave64_operator_role_capability_registry.json": {
            **common, "registry_id": "wave64_operator_role_capability_registry_v1",
            "disclosure_modes_are_not_roles": True,
            "roles": [
                {"role_id": "viewer", "capabilities": ["read_projects", "read_runs", "read_qa", "read_models"]},
                {"role_id": "creator_operator", "capabilities": ["edit_drafts", "publish_domain_revision", "compile_runs", "start_preview", "request_final_render", "cancel_attempt", "request_repair"]},
                {"role_id": "reviewer", "capabilities": ["read_qa", "annotate_review", "approve_candidate", "reject_candidate", "request_repair"]},
                {"role_id": "release_requester", "capabilities": ["request_promotion", "request_revocation", "read_release_readiness"]},
                {"role_id": "runtime_operator", "capabilities": ["read_runtime", "request_reconciliation", "drain_worker", "request_health_probe"]},
                {"role_id": "model_curator", "capabilities": ["read_models", "request_model_staging", "request_model_qualification", "request_model_suspension"]},
                {"role_id": "policy_administrator", "capabilities": ["propose_policy_revision", "request_phase_transition", "manage_role_assignments"]},
                {"role_id": "developer_diagnostic", "capabilities": ["view_diagnostics", "open_native_graph", "run_nonpromotable_diagnostic"]},
            ],
            "browser_certificate_issue": False, "browser_promotion_commit": False, "mode_change_grants_capability": False,
        },
        "wave64_operator_timeline_track_taxonomy_registry.json": {
            **common, "registry_id": "wave64_operator_timeline_track_taxonomy_registry_v1",
            "tracks": ["shot_segments", "reference_video", "camera_lens_focus_exposure", "character_identity", "pose_gaze_expression", "depth_masks_occlusion", "contact_action_force", "surface_wardrobe_continuity", "keyframes", "video_passes", "video_defects_repairs", "dialogue_words_phonemes_visemes", "breath_nonverbal_voice", "foley_sfx", "ambience_room_music", "spatial_objects", "mix_automation", "qa_markers", "promotion_release_markers"],
            "clock_authority": "canonical_rational_media_clock", "draft_undo_only": True, "accepted_artifact_edit_in_place": False,
        },
        "wave64_operator_feature_notification_accessibility_registry.json": {
            **common, "registry_id": "wave64_operator_feature_notification_accessibility_registry_v1",
            "feature_flags": ["controller_console_core", "timeline_editor", "video_temporal_overlays", "audio_stem_workspace", "av_sync_workspace", "model_explanations", "runtime_incidents", "comfyui_app_launchers", "comfyui_frontend_extension"],
            "notification_classes": ["command_result", "review_required", "dependency_blocked", "run_terminal", "incident", "certificate_expiry", "projection_stale", "storage_threshold"],
            "notification_rules": ["deduplicate_by_correlation", "critical_requires_ack", "no_secret_payload", "deep_link_to_evidence", "quiet_hours_never_hide_critical"],
            "preferences": ["reduced_motion", "high_contrast", "font_scale", "caption_default", "transcript_default", "waveform_alternative", "timeline_table_alternative", "keyboard_shortcut_profile"],
            "target": "WCAG_2_2_AA",
        },
        "wave64_operator_canonical_control_binding_registry.json": {
            **common, "registry_id": "wave64_operator_canonical_control_binding_registry_v1",
            "controls": [
                {"control_id": "project.intent", "route": "projects", "read_query": "project_summary", "write_command": "save_draft", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "project.output_kind", "route": "projects", "read_query": "project_summary", "write_command": "save_draft", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "character.instances", "route": "character_library", "read_query": "character_library", "write_command": "save_draft", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "scene.environment_lighting", "route": "scene_builder", "read_query": "scene_graph", "write_command": "save_draft", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "shot.camera", "route": "shot_timeline", "read_query": "shot_timeline", "write_command": "save_draft", "modes": ["director", "expert", "diagnostic"]},
                {"control_id": "shot.pose_action", "route": "shot_timeline", "read_query": "shot_timeline", "write_command": "save_draft", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "mask.authority", "route": "pose_and_masks", "read_query": "artifact_lineage", "write_command": "request_repair", "modes": ["director", "expert", "diagnostic"]},
                {"control_id": "image.route_preference", "route": "image_workspace", "read_query": "model_explanation", "write_command": "save_draft", "modes": ["expert", "diagnostic"]},
                {"control_id": "video.route_preference", "route": "video_workspace", "read_query": "model_explanation", "write_command": "save_draft", "modes": ["expert", "diagnostic"]},
                {"control_id": "audio.route_preference", "route": "audio_workspace", "read_query": "model_explanation", "write_command": "save_draft", "modes": ["expert", "diagnostic"]},
                {"control_id": "timeline.edit", "route": "shot_timeline", "read_query": "shot_timeline", "write_command": "save_draft", "modes": ["director", "expert", "diagnostic"]},
                {"control_id": "run.preview", "route": "runs", "read_query": "run_dag", "write_command": "start_preview", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "run.final_request", "route": "runs", "read_query": "run_dag", "write_command": "request_final_render", "modes": ["director", "expert", "diagnostic"]},
                {"control_id": "run.cancel", "route": "runs", "read_query": "attempt_detail", "write_command": "cancel_attempt", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "qa.compare", "route": "qa_and_compare", "read_query": "candidate_comparison", "write_command": "approve_candidate", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "qa.repair", "route": "qa_and_compare", "read_query": "repair_history", "write_command": "request_repair", "modes": ["guided", "director", "expert", "diagnostic"]},
                {"control_id": "release.promotion_request", "route": "releases", "read_query": "qa_report", "write_command": "request_promotion", "modes": ["director", "expert", "diagnostic"]},
                {"control_id": "runtime.reconcile", "route": "runtime_and_workers", "read_query": "incident_detail", "write_command": "retry_reconciliation", "modes": ["expert", "diagnostic"]},
                {"control_id": "models.phase_request", "route": "models_and_capabilities", "read_query": "model_explanation", "write_command": "request_model_phase_transition", "modes": ["expert", "diagnostic"]},
            ],
            "dead_controls": 0, "raw_path_controls": 0, "direct_comfyui_command_controls": 0,
        },
        "wave64_legacy_app_control_crosswalk_registry.json": {
            **common, "registry_id": "wave64_legacy_app_control_crosswalk_registry_v1",
            "legacy_sources": ["wave05_app_mode_control_surface", "wave10_app_mode_camera_controls", "wave12_app_mode_frame_controls", "wave13_app_mode_mask_controls", "wave14_app_mode_orchestrator_controls", "wave16_app_mode_refine_controls", "wave17_app_mode_body_controls", "wave18_app_mode_surface_controls", "wave19_app_mode_contact_controls", "wave20_app_mode_hard_anatomy_controls", "wave21_app_mode_soft_body_controls", "wave22_app_mode_contact_graph_controls", "wave24_app_mode_instance_controls", "wave34_app_mode_control_registry"],
            "legacy_control_count_observed": 125, "legacy_envelope_shapes_observed": 14,
            "known_contradictions": ["character_max_5_vs_8", "camera_vocabularies_diverge", "qa_default_not_in_allowed_options", "planned_engine_profiles_presented_as_static_choices", "wave34_required_groups_missing"],
            "production_authority": "none_until_every_control_has_canonical_definition_binding_and_test", "migration_complete": False,
        },
        "wave64_legacy_video_audio_authority_deprecation_registry.json": {
            **common, "registry_id": "wave64_legacy_video_audio_authority_deprecation_registry_v1",
            "entries": [
                {"path": "Plan/07_IMPLEMENTATION/scripts/route_video_engine_candidate.py", "classification": "bounded_diagnostic_only", "production_entrypoint_allowed": False},
                {"path": "Plan/07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py", "classification": "legacy_unbound_score_fixture", "production_entrypoint_allowed": False},
                {"path": "Plan/07_IMPLEMENTATION/scripts/score_wave28_micro_motion_evidence.py", "classification": "legacy_unbound_score_fixture", "production_entrypoint_allowed": False},
                {"path": "Plan/07_IMPLEMENTATION/scripts/score_wave29_continuity_evidence.py", "classification": "legacy_unbound_score_fixture", "production_entrypoint_allowed": False},
                {"path": "Plan/07_IMPLEMENTATION/scripts/score_wave33_preview_qa.py", "classification": "legacy_unbound_score_fixture", "production_entrypoint_allowed": False},
                {"path": "Plan/07_IMPLEMENTATION/scripts/check_wave33_final_render_preflight.py", "classification": "legacy_unbound_preflight_fixture", "production_entrypoint_allowed": False},
                {"path": "Plan/08_SCHEMAS/wave06_audio_engine_route_decision.schema.json", "classification": "legacy_engine_id_only_route", "production_entrypoint_allowed": False},
            ],
            "replacement_authorities": ["exact_model_execution_bundle", "workflow_release_manifest", "runtime_lock", "scoped_capability_certificate", "contextual_route_decision", "separate_qa_and_promotion_transaction"],
        },
        "wave64_audio_delivery_and_clock_profile_registry.json": {
            **common, "registry_id": "wave64_audio_delivery_and_clock_profile_registry_v1",
            "profiles": [
                {"profile_id": "canonical_analysis", "sample_rate_hz": 48000, "processing_format": "float32_or_float64", "container_required": False},
                {"profile_id": "lossless_review_evidence", "sample_rate_hz": 48000, "processing_format": "pcm24_or_float32", "container_required": True},
                {"profile_id": "delivery", "sample_rate_hz": 48000, "processing_format": "profile_bound", "container_required": True},
            ],
            "supports": ["rational_video_timebase", "vfr_segment_map", "frame_pts_duration", "sample_clock", "encoder_priming_padding", "retime_edit_list", "cut_epochs", "piecewise_drift"],
            "legacy_16khz_mono_fixture_is_universal_authority": False,
        },
        "wave64_hyperreal_video_audio_app_work_package_registry.json": {
            **common, "registry_id": "wave64_hyperreal_video_audio_app_work_package_registry_v1", "package_id": PACKAGE_ID,
            "row_range": [261, 320], "workstreams": [{"id": wid, "slug": slug, "objective": objective} for wid, slug, objective in WORKSTREAMS],
            "implementation_order": [wid for wid, _, _ in WORKSTREAMS],
            "full_release_external_gates": ["Rows149_220_multimodal_runtime", "Row260_model_intelligence_production_release", "MaskFactory_current_certificate", "human_or_policy_perceptual_release"],
        },
    }


def docs() -> dict[str, str]:
    master = r'''
# Wave64 Hyperreal Video, Audio/AV, and Operator Application Third-Pass Master Plan

Updated: 2026-07-16 America/Chicago

## Decision

Build one durable autonomous media controller over many small, immutable,
versioned ComfyUI API workflows. Treat video, audio, and AV as first-class
evidence-bearing products. Deliver the operator experience as a hybrid:

1. a standalone local controller console for projects, timelines, multi-workflow
   DAGs, QA, comparison, repair, model evidence, workers, and audit history;
2. small ComfyUI App Mode views for one workflow's selected inputs and outputs;
3. an optional ComfyUI frontend extension for deep links, node diagnostics, and
   controller status, never as the durable source of truth.

The old idea of one giant App Mode graph is rejected. App Mode exposes a
workflow's chosen controls and outputs; it does not provide durable
multi-workflow orchestration, aggregate state, certificate authority, or
sample/frame-accurate timeline editing.

## Truthful current state

- Existing Wave26-W31 plans contain valuable concepts but many canonical
  architecture files are only short outlines.
- Existing Wave64 sound and speech packages provide strong bounded components.
- Current video engines, sound engines, speech engines, App surfaces, and LLM/VLM
  roles do not become production-authoritative from planning records.
- The durable controller, full operator application, empirical video/audio
  benchmark program, and end-to-end hyperreal AV release are not built.
- Rows261-320 are additive planned obligations. They do not alter Rows001-260.

## End-to-end product graph

```mermaid
flowchart LR
    O["Operator console"] --> C["Durable controller"]
    C --> P["Project / Character / Scene / Shot packages"]
    P --> K["Keyframe, pose, depth, mask, continuity authority"]
    K --> VR["Per-pass video bundle router"]
    VR --> VG["ComfyUI video workflow releases"]
    VG --> VQ["Frame, temporal, physics, identity QA"]
    VQ --> VX["Localized span repair"]
    P --> AE["Owned audio event graph"]
    AE --> AR["Per-event source / engine router"]
    AR --> AS["Voice, foley, ambience, music, spatial stems"]
    AS --> AQ["Signal, perceptual, identity, acoustic QA"]
    VX --> AV["Canonical frame / PTS / sample assembly"]
    AQ --> AV
    AV --> AX["Localized AV repair and release gates"]
    C --> M["Model reports, workers, incidents, audit"]
    C --> A["Small App Mode workflow launchers"]
```

## What hyperreal video means

Hyperrealism is a blocking scorecard, not a single aesthetic number. A clip
fails when any release-critical dimension fails even if its average is high.

Required dimensions:

1. identity stability across view, expression, occlusion, lighting, and time;
2. anatomy, pose, hands, face, gaze, and joint dynamics;
3. surface-anchored skin, hair, fabric, accessory, and material detail;
4. camera path, lens, exposure, rolling shutter, focus, depth of field, and blur;
5. lighting, shadow, reflection, white balance, and color-transform continuity;
6. primary, micro, secondary, contact, compression, rebound, and settling motion;
7. multi-character ownership, occlusion, separation, and contact reciprocity;
8. environment, prop, wardrobe, fatigue, wetness, damage, and long-form state;
9. calibrated perceptual realism and independent blind preference.

Texture detail must follow the represented surface. Screen-space noise that
looks like pores in one frame and slides in the next is a defect, not detail.

## Video route and multipass policy

Routing happens for every temporal pass, not once per project. Eligible modes
include keyframe-to-video, image-to-video, text-to-video, reference-guided,
interpolation, extension, localized span repair, temporal refinement, and
upscale. The exact selectable unit is a certified model bundle plus workflow
release plus runtime lock.

Hard filters precede ranking. Planned or similarly named engines are not
eligible. Ranking uses task-specific evidence, identity preservation, temporal
stability, motion adherence, physics quality, repair locality, cross-engine
continuity, cost, evidence freshness, and uncertainty. Close candidates may be
branched within a budget. Missing evidence causes abstention or shadow use.

Cross-engine work transfers decoded frames, keyframes, masks, tracks, depth,
flow, pose, metadata, and canonical clocks through certified bridges. It never
transfers incompatible family latents.

## Video repair policy

Accepted outputs are immutable parents. QA localizes defect spans and owners.
A repair receives write masks, protected masks, boundary keyframes, decode
handles, a materially new hypothesis, and a bounded attempt budget. It rewrites
the smallest failed span, reintegrates it, then repeats regional, boundary, and
whole-clip QA. Ambiguous or non-local failures reroute or stop; they do not
silently become full-clip seed loops.

## What hyperreal audio means

Audio is not "generate one soundtrack." The controller compiles an owned event
graph from dialogue, breath, motion, force, contact, material, environment,
camera/listener, and story state. It routes each event independently among:

- recorded/reference material;
- a local retrieved library;
- procedural synthesis;
- neural sound generation;
- qualified character speech synthesis;
- a hybrid layered construction.

Generated sound is not presumed superior. Short physical transients often
benefit from exact library or recorded layers; long semantic ambience may favor
generation; hero contacts may use a force-matched hybrid.

## Voice and performance chain

Character voice is versioned identity authority. The chain is text
normalization, pronunciation, performance plan, dry speech, phoneme alignment,
identity/intelligibility QA, breath and nonverbal layers, viseme binding,
acoustic rendering, mix, and AV QA. Room effects never hide a failed dry voice.
Breathing, effort, gaze, pose, mouth motion, fatigue, and dialogue intent share
the canonical event and continuity state.

## Foley, acoustics, and spatial audio

Foley binds material pairs, force curves, contact area, velocity, surface state,
body/object resonance, position, occlusion, and visual evidence. Acoustic
rendering separates direct path, early reflections, late reverberation,
directivity, distance attenuation, air absorption, and obstruction. Every
important source remains a nondestructive object or stem. Unsupported camera
pan or room claims remain diagnostic, not promotion authority.

## Mix, master, and AV

The mix graph preserves stems and recipes. Release checks include sample and
true peak, integrated and short-term loudness, loudness range, dialogue
intelligibility, spectral masking, phase, noise floor, clicks/pops, and loop
seams. Delivery profiles choose targets; no universal LUFS target is assumed.

One rational media clock maps PTS, frames, and samples. Container-reported
average frame rate is observational metadata, never timing authority. Sync
tolerances vary by event class. Repairs may shift, time-stretch within bounded
limits, pad, crossfade, regenerate one event, repair a mouth span, or remux. The
accepted video and audio parents remain immutable.

## Autonomous intelligence

The LLM may propose project, shot, event, pass, route, and repair plans. It must
cite retrieved registries and evidence, emit strict schemas, report uncertainty,
and abstain when required. Deterministic validators own compatibility and
structural correctness. Calibrated specialist critics observe. Promotion is a
separate policy transaction. No LLM or VLM self-certifies or self-promotes.

## Application product areas

The controller console includes:

- Home and readiness;
- Projects and revisions;
- Character Library;
- Scene Builder;
- Shot and multi-track Timeline;
- Pose, depth, masks, ownership, and contacts;
- Image workspace;
- Video workspace;
- Audio workspace;
- AV assembly workspace;
- Runs, DAG, attempts, queue, and recovery;
- QA, synchronized comparison, annotations, and repair;
- Models, capabilities, benchmarks, and route explanations;
- Runtime workers, locks, leases, storage, and incidents;
- Assets and lineage;
- Settings, policies, roles, and audit.

Guided, Director, Expert, and Diagnostic modes progressively disclose detail.
Raw paths, credentials, internal node IDs, and direct database/runtime mutation
are hidden. Expert mode exposes evidence and exact bundle identity, not unsafe
authority.

## Timeline design

The timeline is the shared editing surface for shots, camera, characters, pose,
masks, contacts, keyframes, video passes, defects, dialogue, voice, breath,
foley, ambience, music, mix automation, and promotion state. Edits are
versioned transactions with optimistic concurrency, undo records, validated
spans, and deterministic recompilation. The UI does not edit generated files in
place.

## Delivery phases

1. Canonical schemas, registries, clocks, and synthetic fixtures.
2. Controller API and projection model with fake ComfyUI/audio adapters.
3. App shell, navigation, project library, and read-only run/DAG views.
4. Character/Scene/Shot/Timeline publishers and typed commands.
5. Single-character video preview, frame manifest, and temporal QA.
6. Two-character ownership/contact video plus local span repair.
7. Audio event graph, source routing, voice, foley, acoustic stems, and QA.
8. Sample-accurate AV assembly and local AV repair.
9. Compare, explain, repair, model, runtime, and incident workspaces.
10. Accessibility, visual regression, fault injection, performance, and security.
11. Empirical engine qualification and shadow autonomous routing.
12. End-to-end release certification after every external gate passes.

## Rows261-320

Fifteen four-row workstreams implement contract, policy, implementation, and
assurance obligations. The final Row320 release depends transitively on every
new row and externally on the existing multimodal runtime, Model Intelligence
production-selection release, current MaskFactory authority, and perceptual
release evidence. Planning work may proceed with synthetic fixtures while the
bulk model library remains deferred.

No planning file, passing static test, or UI mockup proves runtime completion.
'''

    audit = r'''
# Wave64 Hyperreal Video, Audio/AV, and App Third-Pass Gap Audit

Updated: 2026-07-16 America/Chicago

## Verdict

The project contains broad, valuable domain coverage, but coverage count is not
the same as implementation depth. Many original canonical video, audio, and App
documents are short outlines. The strongest runtime evidence remains bounded to
individual lanes such as keyframe/video tests, deterministic audio/mux work,
MMAudio proof, speech controls, and review packets. A unified hyperreal media
runtime and operator application do not yet exist.

## Reconciled evidence and legacy-authority findings

### Video

- The legacy Wave27 video registry/router can describe WAN as proven while the
  newer canonical capability registry correctly leaves an exact production
  bundle unresolved. Production routing must use the newer exact-bundle and
  bucket-scoped certificate authority; broad legacy engine status is diagnostic
  evidence only.
- The currently evidenced WAN lane is a bounded start-image TI2V lane. It does
  not prove multi-anchor keyframes, pose/depth/contact conditioning, temporal
  masks, per-character adapters, generative failed-span repair, moving-camera
  continuity, or multi-character ownership.
- Several Wave28, Wave29, and Wave33 files named as schemas are descriptive
  planning records rather than strict JSON Schema contracts. Their shallow
  validators and caller-supplied aggregate scores cannot authorize production
  execution or promotion.
- Existing temporal scoring can hide missing dimensions or worst-span failures.
  Observation, deterministic gate decision, immutable accepted-parent change,
  and promotion are therefore separated in this package.
- The existing OpenCV short-span lane is useful for bounded deterministic
  defects, but is not evidence of identity-, physics-, contact-, or
  boundary-certified generative video repair.

### Audio and AV

- Genuine MMAudio execution, 48 kHz stereo mixing, and bounded mux correction
  are valuable runtime evidence. They do not yet prove event ownership,
  perceptual acceptance, spatial/room authority, speech continuity, or a full
  promoted AV master.
- Speech-engine candidates and speech controls exist, but candidate creation is
  not voice qualification. Identity, pronunciation, prosody, nonverbal vocal
  behavior, forced alignment, viseme production, room rendering, and downstream
  mix/mux certification remain separate gates.
- Audio provenance needs three orthogonal axes: origin class, realization
  action, and derivation state. A single source label cannot distinguish a
  recorded library asset, a processed derivative, a neural reconstruction, and
  a hybrid layer with enough precision for routing or audit.
- Legacy delivery fixtures must not make 16 kHz mono or one container profile a
  universal production authority. Delivery profiles are explicit and the
  current high-fidelity planning baseline is 48 kHz with profile-specific
  channel, codec, loudness, true-peak, and sync requirements.
- Existing library indexing proves discoverability, not acoustic suitability.
  Assets require content, material, force, perspective, noise, room, license,
  quality, and bucket-specific qualification before automatic selection.

### Operator application

- The earlier App Mode work is a useful control inventory, not a built
  application. It contains incompatible envelope shapes, contradictory control
  definitions, and controls that imply direct rendering or promotion authority.
- ComfyUI App Mode remains a bounded single-workflow input/output surface. The
  durable multi-workflow product is the controller console; optional App Mode
  launchers may only create unpromoted candidates under short-lived authority.
- UI disclosure modes and authorization roles are independent. A browser action
  is always a typed request followed by controller authorization, a durable
  receipt, and projection reconciliation; it never mutates ComfyUI production
  state or promotes an artifact directly.

## Legacy surfaces requiring fail-closed quarantine or migration

1. Broad engine labels and mutable readiness flags that are not bound to an
   immutable model, workflow, runtime, control, hardware, and certificate tuple.
2. Caller-supplied video/audio QA numbers, incomplete averages, and scripts that
   can emit `promote` without analyzer lineage and independent gate authority.
3. Descriptive pseudo-schemas without Draft 2020-12 validation and semantic
   cross-field checks.
4. Legacy App controls such as direct final-render or promotion toggles, raw
   workflow/node/path controls, and browser-to-ComfyUI production mutations.
5. Media-clock assumptions derived from container averages instead of decoded
   PTS/sample evidence and explicit rounding policy.
6. Audio source taxonomies that collapse origin, realization, and derivation.

The generated deprecation registries and legacy App-control crosswalk mark these
surfaces non-authoritative. Implementation must fence or replace them before a
production controller entrypoint is enabled.

## P0 gaps closed at the planning-contract level

1. One canonical frame/PTS/sample clock and typed span contract.
2. Exact per-pass video bundle selection, uncertainty, branching, and abstention.
3. Per-frame identity, ownership, pose, mask, depth, exposure, color, flow, and
   defect manifests.
4. Surface-anchored temporal texture and physical motion scorecards.
5. Immutable-parent localized span repair with handles and boundary QA.
6. Per-event audio source routing across recorded, library, procedural, neural,
   speech, and hybrid methods.
7. Dry voice identity/performance authority separated from room and mix effects.
8. Force/material/contact-aware foley and evidence-bound acoustic/spatial claims.
9. Nondestructive stem/mix/master lineage and event-class AV tolerances.
10. Controller console vs App Mode vs frontend-extension authority decision.
11. Typed application commands, queries, projections, timeline edits,
    comparisons, repair reviews, permissions, incidents, and releases.
12. Objective, critic, human, accessibility, fault, and performance test matrix.

## Remaining implementation gaps

- No production durable controller or event/projection store.
- No released controller API or operator frontend.
- No certified video model bundle or full video benchmark corpus under this plan.
- No complete frame-manifest/track/flow pipeline for every runtime engine.
- No operational multi-character physical/contact video certification.
- No unified audio event compiler and source router across all audio sources.
- No production object/stem acoustic renderer proven against geometry evidence.
- No end-to-end voice-to-viseme-to-room-to-mix-to-mux release proof.
- No calibrated full critic ensemble with held-out false-accept measurements.
- No end-to-end restart, lease-loss, unknown-submission, disk-full, or projection
  lag test through the future operator application.

## Anti-patterns explicitly rejected

- one giant ComfyUI workflow or App Mode application;
- one global engine choice for every video or audio pass;
- treating a planned engine card as eligible;
- treating high spatial detail as temporally stable detail;
- full-clip seed loops for localized failures;
- generating every sound when a qualified source/library/procedural layer is
  more faithful;
- adding room effects before dry voice acceptance;
- using container average frame rate as clock authority;
- allowing a UI, LLM, or critic to promote its own output;
- showing a green aggregate score while a blocking realism dimension fails.

## Readiness statement

Architecture and contract depth are materially strengthened. Runtime and
release readiness remain false until implementation artifacts and empirical
evidence satisfy Rows261-320 and all external gates.
'''

    architecture = r'''
# Wave64 Hyperreal Video, Audio/AV, and Operator Application Control Architecture

Updated: 2026-07-16 America/Chicago

## Service boundaries

The controller owns durable intent, aggregate versions, commands, events,
projections, schedules, model decisions, artifact lineage, QA, repair, and
promotion transactions. ComfyUI workers execute immutable workflow releases.
Audio tools execute immutable stem/mix jobs. The browser owns no durable truth.

Core services:

- Project, Character, Scene, Shot, and Timeline service;
- Planner and strict proposal validator;
- exact-bundle model router;
- workflow compiler and release resolver;
- scheduler, lease/fencing, and worker adapter;
- artifact/CAS and media metadata service;
- video frame/track/flow analyzer;
- audio event/source/stem/mix service;
- QA/critic and calibration service;
- diagnosis and repair service;
- promotion/revocation service;
- query projection and notification service;
- policy, role, audit, and credential broker.

## Command and query boundary

Browser commands carry actor, role, target immutable references, parameter
schema/hash, expected aggregate version, idempotency key, authorization, and
confirmation level. They go only to the controller. Browser queries read
projections or explicit authoritative snapshots. WebSocket/SSE events update
views but never become durable authority. Reconnection uses event sequence and
projection version; stale views visibly enter catching-up or reconciling state.

## ComfyUI boundary

The adapter binds a runtime lock, workflow release, exact bundle, lease/fencing
token, deterministic prompt UUID, idempotency key, API body hash, output
namespace, and receipt. It reconciles queue/history/files/CAS after disconnect.
Native ComfyUI queue and history remain volatile observations. App Mode is used
for selected single-workflow controls and outputs. Subgraphs package stable
within-workflow clusters, not the external pass DAG.

## Media stores

- Append-only event store for decisions and transitions.
- Relational projections for projects, timelines, runs, QA, models, and workers.
- Content-addressed artifact store for immutable media and evidence.
- Search index for model reports, character knowledge, assets, and run evidence.
- Secret store isolated from browser payloads and logs.

## API groups

- `/v1/projects`, `/characters`, `/scenes`, `/shots`, `/timelines`;
- `/v1/runs`, `/passes`, `/attempts`, `/commands`, `/events`;
- `/v1/artifacts`, `/lineage`, `/comparisons`, `/repairs`, `/promotions`;
- `/v1/models`, `/bundles`, `/certificates`, `/benchmarks`, `/explanations`;
- `/v1/video`, `/audio`, `/av`, `/qa`;
- `/v1/workers`, `/leases`, `/queues`, `/incidents`, `/reconciliation`;
- `/v1/policies`, `/roles`, `/audit`, `/health`.

Every mutating route is a typed command. Direct CRUD over authority tables is
forbidden. Long operations return accepted command IDs and are observed through
projections/events.

## Application surfaces

### Controller console

Required for cross-workflow state, timelines, runs, comparisons, repairs, model
reports, runtime operations, and audit. It is the primary application.

### ComfyUI App Mode

Required for focused workflow launchers such as Character calibration, Mask
inspection, image preview, video span preview, voice preview, and audio event
preview. Each launcher receives controller-issued immutable inputs and returns
unpromoted artifacts/receipts.

### Optional frontend extension

Provides controller health, artifact deep links, workflow-release identity,
node/subgraph diagnostics, and navigation back to the controller. It never
duplicates the controller's database or promotion logic.

## Reliability

- optimistic aggregate concurrency;
- transactional outbox;
- at-least-once delivery with idempotent consumers;
- monotonically increasing worker fencing tokens;
- content hashes before artifact registration;
- exactly-once promotion transaction by artifact/scope/policy revision;
- ambiguous submissions block failover and promotion until reconciliation;
- projections may lag but display their freshness;
- operator input is preserved across validation and infrastructure failures.

## Performance tiers

- metadata/query interactions: target p95 below 300 ms locally;
- command acceptance: target p95 below 500 ms locally;
- live progress propagation: target p95 below 1 s;
- synchronized comparison seek: target p95 below 250 ms for proxies;
- timeline with 10,000 events: virtualized and interactable at 60 Hz target;
- full-resolution media is proxied; originals remain immutable and on demand;
- preview and final render queues are separate resource classes.

These are initial design targets and require measured revision.

## Deployment

Run the controller, event/projection store, CAS index, and web UI locally by
default. Local and EC2 ComfyUI/audio workers register through explicit runtime
locks and leases. Credentials stay server-side. Offline operation preserves
local projects and queues commands only when policy permits; it never pretends a
remote worker is available.
'''

    video = r'''
# Wave64 Hyperreal Video Generation and Temporal Intelligence Strategy

## Representation

Every shot binds a rational clock, camera/lens state, approved boundary
keyframes, per-character identities, pose/skeleton, depth, masks, contacts,
surface/material state, lighting/exposure/color state, motion channels, audio
events, and continuity parents. Each decoded frame registers tracks, ownership,
visibility, flow, defects, and immutable artifact identity.

## First-pass selection

Choose the first temporal route from the request and available authority:

- keyframe-to-video when an approved image is the visual authority;
- image-to-video for looser motion around one source;
- reference-guided when choreography/camera timing authority exists;
- text-to-video only when identity/pose authority is intentionally weak;
- interpolation between approved boundaries for controlled transitions;
- extension only with locked overlap handles and continuity QA.

The controller can divide a shot into route segments. A hero face span may use
one engine while a wide motion span uses another, but decoded bridge and
boundary certification are mandatory.

## Motion layers

Primary action, gaze/blink/breath, muscle/effort, contact/compression,
hair/fabric/accessory follow-through, fluids/particles, camera movement,
stabilization, and settling each receive independent amplitude, frequency,
driver, phase, and physical constraint contracts. Reference motion is evidence,
not permission to copy identity or unsupported scene state.

## Temporal multipass order

1. shot proxy and camera/choreography validation;
2. approved boundary and anchor keyframes;
3. base temporal generation;
4. identity and ownership stabilization;
5. anatomy, hands, face, gaze, and mouth stabilization;
6. contact, occlusion, depth, and interaction stabilization;
7. surface/material temporal lock;
8. hair/fabric/secondary-motion refinement;
9. lighting, reflection, exposure, color, blur, and grain continuity;
10. localized defect repair;
11. temporal upscale and delivery encode;
12. regional, boundary, whole-clip, and long-form QA.

The order is a dynamic DAG: a pass is included only when its defect/objective
requires it. Every pass declares targets, protected regions, parents, bridge,
denoise/change budget, metrics, and rollback.

## Multi-character video

Each character keeps a scene instance ID, identity revision, skeleton, depth,
silhouette, masks, visibility, contact roles, and render order. Contact is
reciprocal and time-bound. Occlusion never transfers identity. Repair masks may
overlap only under an explicit conflict policy, and all other characters are
protected by default.

## QA scorecard

Use deterministic geometry/signal metrics, specialist identity and temporal
models, calibrated VLM review, and blind human comparison. Report per-character,
per-region, per-span, per-shot, and project aggregates. Required slices include
camera motion, occlusion, low light, fast motion, dialogue, hands, contact,
multi-character crossings, hair/fabric, reflections, and long-form cuts.

No metric is accepted without a version, threshold, confidence interval,
evidence reference, and calibration snapshot. Blocking failures cannot be
averaged away.
'''

    audio = r'''
# Wave64 Hyperreal Audio, AV Generation, and Spatial Intelligence Strategy

## Event-first architecture

Compile a canonical event graph before generating sound. Events bind source
ownership, visual cause, force/contact/material evidence, position, duration,
priority, continuity, and QA. The graph includes explicit silence and room tone;
the absence of a sound can be intentional evidence.

## Source selection

Represent source choice on three orthogonal axes. `origin_class` distinguishes
field/studio/voice recordings, procedural renders, neural text/audio/video
conditioning, and hybrids. `realization_action` distinguishes reuse, new
recording, neural generation, procedural synthesis, and layer assembly.
`derivation_state` tracks raw, segmented, prepared, transformed, layered,
spatially rendered, and mastered artifacts. Retrieval is an action, not an
origin; a neural asset may later be retrieved without becoming a recording.

Hard-filter sources for event class, duration, transient/loop behavior, sample
rate, channel layout, identity/material match, license/usage scope, installed
availability, certificate, and runtime envelope. Rank eligible candidates using
event-specific benchmark evidence, editability, spatial cleanliness, noise,
artifacts, continuity, cost, and uncertainty. Hybrid layers must name every
component and its purpose.

## Speech and nonverbal voice

Keep dry character speech immutable. Version pronunciation, language, emotion,
prosody, pace, pitch range, breath, effort, and nonverbal events. Align phonemes
and words, derive viseme candidates, and validate the mouth-region owner. Run
identity, intelligibility, pronunciation, timing, artifact, and performance QA
before acoustics. Never repair a voice identity defect with reverb or mix EQ.

## Foley and sound design

Bind transient, body, resonance, friction, debris, cloth, and tail layers to
visual force and material evidence. Repetition uses variation policies that
preserve source identity without obvious sample cycling. Generated layers are
separated from retrieved/recorded truth so future QA can learn by source method.

## Acoustic and spatial rendering

Use object/stem rendering with source/listener tracks, directivity, distance,
occlusion, geometry/IR evidence, early reflections, late reverb, and automation.
Keep dry stems. A panning curve inferred only from camera framing is a draft
unless scene geometry and source tracking support it.

## Mix and mastering

Preserve the stem graph and nondestructive recipe. Dialogue and critical events
receive intelligibility and masking gates. Measure peak, true peak, loudness,
range, dynamics, spectrum, phase, noise, discontinuity, and loop seams against a
versioned delivery profile. Render review and final masters separately.

## AV synchronization

Map all events through the canonical rational clock. Validate expected and
observed PTS, sample positions, frame boundaries, event-class tolerances, drift,
monotonic container timestamps, and exact frame/sample counts. Repair the
smallest event/span. Remuxing must not silently drop a terminal frame or sample.

## Learning

Every use writes an observation containing exact source/bundle, context,
assignment probability, settings, metrics, failures, repair, operator decision,
and promoted outcome. Learning jobs use held-out and shadow partitions to avoid
turning historical selection bias into false evidence.
'''

    app = r'''
# Wave64 Production Operator Application and ComfyUI App Mode Strategy

## Product decision

The primary product is a standalone local controller console backed by the
durable autonomous controller. ComfyUI App Mode provides small workflow-specific
launchers. An optional frontend extension links ComfyUI diagnostics to the
controller. This division preserves ComfyUI's strengths while avoiding hidden
state spread across workflow files and browser sessions.

## Information architecture

### Home

Readiness summary, active projects, current runs, blockers, incidents, pending
reviews, storage/worker health, and safe next actions.

### Projects

Project revisions, deliverables, characters, scenes, timelines, continuity,
policies, budgets, artifacts, and release status. Draft/published revisions are
separate; autosave never publishes.

### Character Library

Identity/body/surface/wardrobe/accessory/voice packages, views, adapters,
benchmarks, continuity history, accepted/failure examples, and per-engine
capability. Multi-character scene instances reference packages; they do not
merge character authority.

### Scene Builder

Environment, lighting, props, surfaces, characters, ownership, spatial layout,
actions, dialogue, audio expectations, and continuity parents. Provide schema
forms plus an evidence-aware natural-language assistant; the assistant proposes
structured changes that the operator reviews.

### Shot Timeline

Multi-track editor for shots, camera, characters, pose, masks, contacts,
keyframes, passes, defects, dialogue, voice, breath, foley, ambience, music,
automation, and promotion. Support zoom, snapping to rational clock boundaries,
range selection, markers, compare, branch/take views, undo, optimistic conflicts,
and read-only artifact overlays.

### Pose and Masks

Per-character skeleton/depth/silhouette, provider person index, render order,
contacts, target/protected masks, ontology, transforms, truth tier, certificate,
and round-trip visualization. Mode B drafts are visibly distinct from approved
Mode A authority.

### Image, Video, Audio, and AV workspaces

Each workspace shows source authority, planned passes, exact selected bundles,
candidate branches, progress, artifacts, metrics, defects, repairs, and release
state. Video adds synchronized frame/flow/track views. Audio adds waveform,
spectrogram, loudness, stems, objects, buses, and automation. AV adds frame,
waveform, phoneme/viseme, event, offset, and drift overlays.

### Runs

Live DAG, pass/attempt state, worker/lease, queue, resource budget, receipts,
logs, lineage, cancellation, reconciliation, and recovery. A stale or ambiguous
attempt is explicit. The UI offers only commands safe for the current state.

### QA and Compare

Synchronized side-by-side, wipe, onion skin, difference, flicker, audio A/B,
null, and AV overlays. Blind labels are available. Metrics link to evidence and
calibration. Operator annotations are immutable records. Approve/reject/repair
are commands, never direct field edits.

### Models and Capabilities

Discovery metadata, exact installed bundles, compatibility, certificates,
benchmarks, performance profiles, failure notes, drift, quarantine, and route
explanations. Make "why selected," "why filtered," uncertainty, and evidence
freshness understandable. Planned models never look production-ready.

### Runtime and Workers

Runtime locks, workers, leases/fencing, queues, VRAM/RAM/disk, model residency,
latency, incidents, receipts, reconciliation, and safe recovery. Credentials and
raw remote commands are never rendered.

## Interaction modes

- Guided: intent, curated choices, previews, plain-language QA.
- Director: scene/shot/timeline/candidate/repair control.
- Expert: exact bundles, parameters within certified envelopes, detailed metrics.
- Diagnostic: node/runtime/evidence detail; always visibly non-promotional.

Mode changes affect visibility, not authority.

## State design

Every page implements loading, empty, ready, dirty, saving, queued, running,
cancelling, reconciling, blocked, failed, offline, stale, and completed states.
Errors preserve input, identify the exact failed authority/dependency, show a
correlation ID, and offer only safe actions. Projection freshness is always
visible when it matters.

## Accessibility and responsive behavior

Target WCAG 2.2 AA, full keyboard navigation, visible focus, accessible names,
semantic landmarks, captions/transcripts, non-color status signals, reduced
motion, scalable text, waveform/spectrogram alternatives, and screen-reader
summaries for charts/timelines. Mobile App Mode remains useful for quick
workflows; the full timeline targets desktop/tablet with a simplified mobile
review experience.

## Application tests

Contract-test every control-to-command/query binding. Component-test every
state. Visual-regress critical screens and media overlays. Accessibility-test
keyboard and assistive semantics. Fault-test disconnects, restarts, stale
versions, duplicate commands, lease loss, ambiguous submissions, corrupt
artifacts, disk full, model unload, and projection lag. E2E-test one-character,
two-character, video repair, voice/foley mix, AV repair, and release paths using
synthetic then certified fixtures.
'''

    adr = r'''
# ADR-W64-HVAA-001: Hybrid Controller Console and ComfyUI App Mode Surfaces

**Status:** Proposed for main-task adoption
**Date:** 2026-07-16

## Context

The system must coordinate characters, scenes, shots, masks, image/video/audio
passes, exact models, workers, QA, repairs, and releases across many workflows.
ComfyUI App Mode is optimized for selected inputs/outputs of one workflow.

## Decision

Use a standalone local controller console as the primary application, small App
Mode workflow launchers for focused execution, and an optional frontend
extension for diagnostic/deep-link integration.

## Options considered

| Option | Multi-workflow state | ComfyUI integration | Complexity | Decision |
|---|---:|---:|---:|---|
| One giant App Mode graph | poor | native | deceptively high | reject |
| Frontend extension only | medium | deepest | high coupling | reject as sole UI |
| Standalone controller only | excellent | indirect | medium | incomplete alone |
| Hybrid console + App Mode + optional extension | excellent | strong | highest initial scope | accept |

## Consequences

- Durable state and promotion remain outside ComfyUI.
- Workflow authors retain focused App Mode experiences.
- The project must version a controller API and projection model.
- Some UI concepts exist in two surfaces, so a generated binding registry and
  contract tests are mandatory.
- Frontend-extension changes cannot break core controller operation.
'''

    implementation = r'''
# Wave64 Hyperreal Video, Audio/AV, and App Implementation Protocol

## Authority order

1. immutable packages and exact references;
2. deterministic schema/semantic validators;
3. registry and policy snapshots;
4. qualified exact model/workflow/runtime bundles;
5. controller command, event, attempt, artifact, QA, and promotion records;
6. calibrated critic observations;
7. operator decisions where policy requires them.

An LLM, VLM, UI projection, ComfyUI history entry, preview, or filename cannot
replace these authorities.

## Implementation rules

- Implement schemas and synthetic fixtures before GPU/media execution.
- Keep the bulk model-library gate independent; synthetic certified fixtures may
  prove controller behavior without pretending real models are qualified.
- Publish canonical clocks before video/audio work.
- Build fake ComfyUI and audio adapters for restart/fault tests.
- Use immutable workflow releases and runtime locks.
- Persist command/outbox before external submission.
- Reconcile after every disconnect or ambiguous receipt.
- Register and hash artifacts before QA.
- Write QA and promotion as separate transactions.
- Repair the smallest failed scope with a new hypothesis.
- Preserve accepted parents, dry stems, and original project revisions.
- Do not expose raw paths, credentials, direct database writes, or direct queue
  mutation to the browser.

## Vertical slices

1. Read-only controller shell with synthetic project/run projections.
2. Typed project/scene/shot publishing and timeline edits.
3. Single-character video preview through fake then real local worker.
4. Frame manifest and temporal QA.
5. Localized video span repair.
6. Two-character ownership/contact video.
7. Audio event graph and hybrid source selection.
8. Character dry voice and alignment.
9. Foley/acoustic/spatial stem render.
10. Mix/master and sample-accurate mux.
11. Local AV repair.
12. Compare/repair/model/runtime application workspaces.
13. Accessibility, resilience, performance, and security release.

## Runtime truth labels

Use `planned`, `implemented_synthetic_only`, `local_runtime_observed`,
`qualified_scope`, `shadow_release`, and `production_release`. Never infer a
higher label from a lower one. Every label binds exact evidence and scope.
'''

    qa = r'''
# Wave64 Hyperreal Video, Audio/AV, and Operator Application QA Protocol

## Test pyramid

- Many schema, semantic, state-machine, policy, and ranking unit/property tests.
- Contract tests for controller, adapters, commands, queries, and projections.
- Integration tests with fake and local ComfyUI/audio workers.
- Fault-injection tests around every external side effect.
- Media benchmark and calibrated critic tests.
- Component, visual-regression, accessibility, and usability tests for the app.
- A small number of end-to-end release tests.

## Mandatory negative tests

- planned, suspended, revoked, expired, or hash-mismatched bundle selection;
- non-contiguous frames, duplicate tracks, identity owner swaps, contact
  asymmetry, clock disagreement, and unresolved continuity conflicts;
- repair outside the failed span, missing handles/protected masks, mutation of
  an accepted parent, and unchanged-hypothesis retry;
- audio event without ownership/clock/source evidence;
- dry voice promotion without identity/alignment evidence;
- spatial claim without position/acoustic evidence;
- frame/sample loss, non-monotonic PTS, excess time stretch, and hidden drift;
- UI dead controls, unauthorized commands, stale aggregate versions, duplicate
  idempotency keys, direct ComfyUI mutation, and projection-as-promotion;
- WebSocket loss, controller/worker restart, lease loss, unknown submission,
  disk full, artifact corruption, queue cancellation, and projection lag.

## Media qualification

Every metric records revision, threshold, direction, value, confidence bounds,
calibration, and evidence. Benchmarks include held-out slices and exact source
context. Report false-accept and false-reject rates. Candidate selection logs
assignment probability so learning does not treat biased history as a random
benchmark.

## Release rule

No aggregate average can hide a blocking failure. Promotion requires current
exact-bundle/runtime/workflow certificates, target/protected/whole-artifact QA,
continuity and clock consistency, calibrated critics, and required human or
policy approval. Static planning tests never satisfy runtime release.
'''

    handoff = r'''
# Hyperreal Video, Audio/AV, and App Third-Pass Main-Session Handoff

Target main task: 019f422f-88b1-7382-872b-21de2089e983

Preserve the additive Wave64 Rows261-320 package and every path in
`WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PRESERVATION_MANIFEST.json`.
Do not delete, clean, renumber, fold into unrelated FLUX.2 evidence, or infer
runtime completion.

Adopt the hybrid application decision: durable standalone controller console,
small workflow-specific ComfyUI App Mode surfaces, and optional frontend
extension. Preserve external controller authority and the existing MaskFactory
boundary.

Rows261-320 add strict video, audio/AV, and application contracts. They do not
change Rows001-260. Planning and synthetic controller work may proceed while
the bulk model library remains deferred. Any real engine execution still needs
an exact qualified bundle, workflow release, runtime lock, and scoped evidence.

Review and record ADOPTED, PARTIALLY_ADOPTED, or REJECTED before implementation
or staging. The package currently claims planning-contract coverage only.
'''

    return {
        "Plan/00_PROJECT_CONTROL/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_MASTER_PLAN.md": master,
        "Plan/01_CURRENT_SYSTEM_REVIEW/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_GAP_AUDIT.md": audit,
        "Plan/02_TARGET_ARCHITECTURE/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_CONTROL_ARCHITECTURE.md": architecture,
        "Plan/02_TARGET_ARCHITECTURE/ADR_WAVE64_HYBRID_CONTROLLER_CONSOLE_AND_COMFYUI_APP_MODE.md": adr,
        "Plan/02_TARGET_ARCHITECTURE/WAVE64_PRODUCTION_OPERATOR_APPLICATION_AND_COMFYUI_APP_MODE_STRATEGY.md": app,
        "Plan/04_VIDEO_GIF_SYSTEM/WAVE64_HYPERREAL_VIDEO_GENERATION_AND_TEMPORAL_INTELLIGENCE_STRATEGY.md": video,
        "Plan/05_AUDIO_SYSTEM/WAVE64_HYPERREAL_AUDIO_AV_GENERATION_AND_SPATIAL_INTELLIGENCE_STRATEGY.md": audio,
        "Plan/Instructions/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_IMPLEMENTATION_PROTOCOL.md": implementation,
        "Plan/Instructions/QA/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_QA_AND_RELEASE_PROTOCOL.md": qa,
        "Plan/Instructions/Hydration_Rehydration/HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_MAIN_SESSION_HANDOFF.md": handoff,
    }


def build_examples() -> dict[str, dict[str, Any]]:
    h = lambda ch: ch * 64
    provenance = {"producer": "wave64_third_pass_fixture_builder", "producer_version": "1.0.0", "source_refs": [], "registry_snapshot_ids": ["wave64_hvaa_fixture_snapshot_v1"], "canonicalization": "rfc8785_jcs"}
    scope = {"project_id": "project_hvaa_demo", "scene_id": "scene_001", "shot_id": "shot_001", "take_id": "take_001"}
    span = {"clock_id": "clock_24fps_48khz", "timebase": {"numerator": 1, "denominator": 24000, "drop_frame": False}, "start_pts": 0, "end_pts_exclusive": 48000, "start_frame": 0, "end_frame_exclusive": 48, "start_sample": 0, "end_sample_exclusive": 96000, "rounding_policy": "exact_only"}
    def iref(record_type: str, record_id: str, n: str) -> dict[str, Any]:
        return {"schema_id": f"https://comfy-ui-main.local/schemas/{record_type.replace('_', '-')}/1.0.0", "record_type": record_type, "record_id": record_id, "revision": "r001", "sha256": h(n), "bytes": 1024, "path_or_uri": f"artifacts/{record_type}/{record_id}.json"}
    route = {
        "schema_version": "1.0.0", "record_type": "hyperreal_video_engine_route_decision", "video_engine_route_decision_id": "route_video_demo_001", "revision": "r001", "status": "blocked", "created_at": UPDATED_AT,
        "scope": scope, "pass_intent": "keyframe_to_video", "context_ref": iref("model_selection_context", "ctx_video_demo", "1"),
        "evaluated_candidates": [{"bundle_ref": iref("model_execution_bundle", "bundle_planned_video", "2"), "eligible": False, "hard_filter_reasons": ["certificate_missing"], "rank_score": None, "confidence_low": None, "certificate_ref": None, "pareto_frontier": False}],
        "selected_bundle_ref": None, "decision": "blocked", "ranking_policy_id": "wave64_video_rank_v1", "registry_snapshot_id": "wave64_hvaa_fixture_snapshot_v1", "assignment_probability": None, "production_execution_allowed": False, "provenance": provenance,
    }
    audio_graph = {
        "schema_version": "1.0.0", "record_type": "hyperreal_audio_event_graph", "audio_event_graph_id": "audio_graph_demo_001", "revision": "r001", "status": "validated", "created_at": UPDATED_AT,
        "scope": scope, "canonical_clock": span,
        "events": [
            {"event_id": "evt_dialogue_001", "event_class": "dialogue", "owner": {"owner_type": "character_instance", "owner_id": "charinst_aria_01"}, "span": span, "visual_source_ref": iref("visual_audio_event_manifest", "visual_evt_dialogue", "3"), "force_event_ref": None, "material_pair_id": None, "position_track_ref": iref("position_track", "pos_aria", "4"), "priority": 100, "required": True},
            {"event_id": "evt_roomtone_001", "event_class": "room_tone", "owner": {"owner_type": "environment", "owner_id": "room_001"}, "span": span, "visual_source_ref": None, "force_event_ref": None, "material_pair_id": None, "position_track_ref": None, "priority": 20, "required": True},
        ],
        "edges": [{"source_event_id": "evt_roomtone_001", "target_event_id": "evt_dialogue_001", "relation": "layers_with"}], "acyclic_causal_edges": True, "all_required_visual_events_bound": True, "provenance": provenance,
    }
    app_command = {
        "schema_version": "1.0.0", "record_type": "hyperreal_application_command", "application_command_id": "cmd_preview_demo_001", "revision": "r001", "status": "validated", "created_at": UPDATED_AT,
        "actor_id": "operator_local_001", "role_id": "director", "command": "start_preview", "target_refs": [iref("operator_project", "project_hvaa_demo", "5")], "parameter_schema_id": "start_preview_parameters_v1", "parameters_sha256": h("6"), "expected_aggregate_version": 7, "idempotency_key": "cmd-preview-demo-001", "authorization_ref": iref("autonomous_tool_authorization", "auth_preview_demo", "7"), "confirmation_level": "confirm", "offline_created": False, "raw_path_or_credentials_present": False, "direct_comfyui_mutation": False, "provenance": provenance,
    }
    comparison = {
        "schema_version": "1.0.0", "record_type": "hyperreal_artifact_comparison_session", "artifact_comparison_session_id": "compare_demo_001", "revision": "r001", "status": "planned", "created_at": UPDATED_AT,
        "scope": scope, "candidate_refs": [iref("multimodal_artifact_manifest", "candidate_a", "8"), iref("multimodal_artifact_manifest", "candidate_b", "9")], "comparison_mode": "av_sync_overlay", "synchronized_playback": True, "blind_labels": True, "metric_overlay_ids": ["identity_temporal_stability", "av_event_offset"], "route_explanation_refs": [iref("model_explanation_projection", "explain_a", "a")], "operator_annotations_ref": None, "decision_command_ref": None, "provenance": provenance,
    }
    repair = {
        "schema_version": "1.0.0", "record_type": "hyperreal_av_local_repair_plan", "av_local_repair_plan_id": "av_repair_demo_001", "revision": "r001", "status": "planned", "created_at": UPDATED_AT,
        "scope": scope, "sync_evaluation_ref": iref("hyperreal_av_sync_evaluation", "sync_demo_001", "b"), "accepted_video_parent_ref": iref("video_artifact", "video_parent_demo", "c"), "accepted_audio_parent_ref": iref("audio_artifact", "audio_parent_demo", "d"),
        "repairs": [{"event_ids": ["evt_dialogue_001"], "target_span": span, "method": "shift_event", "maximum_time_stretch_ratio": 1.0, "handle_samples_before": 480, "handle_samples_after": 480, "hypothesis_ref": iref("failure_diagnosis_and_repair_hypothesis", "hyp_sync_demo", "e")}], "accepted_parents_immutable": True, "smallest_failed_scope_only": True, "full_av_rerender": False, "provenance": provenance,
    }
    launch_request = {
        "schema_version": "1.0.0", "record_type": "hyperreal_app_mode_launch_request", "app_mode_launch_request_id": "launch_video_preview_demo_001", "revision": "r001", "status": "validated", "created_at": UPDATED_AT,
        "actor_id": "operator_local_001", "launcher_id": "video_span_preview_v1", "workflow_release_ref": iref("workflow_release_manifest", "wf_video_span_preview_v1", "f"), "runtime_lock_ref": iref("comfyui_runtime_lock", "runtime_local_fixture_v1", "0"), "input_package_refs": [iref("video_span_repair_plan", "repair_input_demo", "1")], "allowed_output_schema_ids": ["multimodal_artifact_manifest_v1", "comfyui_execution_receipt_v1"], "gateway_token_hash": h("2"), "gateway_token_expires_at": "2026-07-16T21:00:00-05:00", "controller_callback_id": "callback_video_preview_demo_001", "production_promotion_allowed": False, "direct_controller_database_access": False, "provenance": provenance,
    }
    realtime_event = {
        "schema_version": "1.0.0", "record_type": "hyperreal_application_realtime_event", "application_realtime_event_id": "rt_event_demo_001", "revision": "r001", "status": "validated", "created_at": UPDATED_AT,
        "subscription_id": "sub_operator_demo_001", "connection_epoch": 2, "event_sequence": 101, "previous_event_sequence": 100, "event_type": "run_progress", "aggregate_ref": iref("autonomous_multimodal_job", "run_demo_001", "3"), "payload_schema_id": "run_progress_projection_v1", "payload_sha256": h("4"), "payload_ref": iref("run_progress_projection", "run_demo_001_seq101", "4"), "resume_cursor": "cursor-101", "gap_detected": False, "authoritative_for_transition": False, "provenance": provenance,
    }
    multi_character_projection = {
        "schema_version": "1.0.0", "record_type": "hyperreal_multi_character_editor_projection", "multi_character_editor_projection_id": "multi_editor_demo_001", "revision": "r001", "status": "validated", "created_at": UPDATED_AT,
        "scope": scope,
        "instance_cards": [
            {"character_instance_id": "charinst_aria_01", "character_package_ref": iref("character_package_revision", "char_aria_r003", "5"), "stable_color_token": "character_blue", "stable_pattern_token": "diagonal", "bbox_xywh_normalized": [0.10, 0.10, 0.35, 0.80], "skeleton_ref": iref("pose_track", "pose_aria", "6"), "depth_order": 1, "render_order": 1, "provider_person_index": 0, "visibility": 1.0, "wardrobe_ref": iref("wardrobe_state", "wardrobe_aria", "7"), "voice_ref": iref("voice_package", "voice_aria", "8"), "target_mask_refs": [], "protected_mask_refs": [iref("mask_factory_binding", "protect_aria", "9")]},
            {"character_instance_id": "charinst_blake_01", "character_package_ref": iref("character_package_revision", "char_blake_r002", "a"), "stable_color_token": "character_orange", "stable_pattern_token": "dots", "bbox_xywh_normalized": [0.55, 0.10, 0.35, 0.80], "skeleton_ref": iref("pose_track", "pose_blake", "b"), "depth_order": 2, "render_order": 2, "provider_person_index": 1, "visibility": 1.0, "wardrobe_ref": iref("wardrobe_state", "wardrobe_blake", "c"), "voice_ref": iref("voice_package", "voice_blake", "d"), "target_mask_refs": [], "protected_mask_refs": [iref("mask_factory_binding", "protect_blake", "e")]},
        ],
        "contact_graph_ref": iref("contact_graph", "contact_demo", "f"), "mode_a_mask_refs": [iref("mask_factory_binding", "mode_a_demo", "0")], "mode_b_draft_mask_refs": [], "transform_roundtrip_refs": [iref("transform_roundtrip", "roundtrip_demo", "1")], "validation_issue_refs": [], "projection_only": True, "provenance": provenance,
    }
    return {
        "wave64_hyperreal_video_blocked_route.example.json": route,
        "wave64_hyperreal_audio_event_graph.example.json": audio_graph,
        "wave64_hyperreal_application_command.example.json": app_command,
        "wave64_hyperreal_artifact_comparison.example.json": comparison,
        "wave64_hyperreal_av_local_repair.example.json": repair,
        "wave64_hyperreal_app_mode_launch_request.example.json": launch_request,
        "wave64_hyperreal_realtime_event.example.json": realtime_event,
        "wave64_hyperreal_multi_character_editor_projection.example.json": multi_character_projection,
    }


def validate_media_span(span: dict[str, Any], label: str = "span") -> None:
    if span["start_pts"] >= span["end_pts_exclusive"]:
        raise ValueError(f"{label}: start_pts must precede end_pts_exclusive")
    if span.get("start_frame") is not None and span.get("end_frame_exclusive") is not None:
        if span["start_frame"] >= span["end_frame_exclusive"]:
            raise ValueError(f"{label}: frame span is reversed or empty")
    if span.get("start_sample") is not None and span.get("end_sample_exclusive") is not None:
        if span["start_sample"] >= span["end_sample_exclusive"]:
            raise ValueError(f"{label}: sample span is reversed or empty")


def immutable_ref_key(value: dict[str, Any]) -> tuple[str, str, str, str]:
    return value["record_type"], value["record_id"], value["revision"], value["sha256"]


def validate_video_route_record(record: dict[str, Any]) -> None:
    selected = record.get("selected_bundle_ref")
    if record.get("production_execution_allowed"):
        if record.get("decision") != "selected" or not selected:
            raise ValueError("production video route requires one selected bundle")
        matches = [entry for entry in record["evaluated_candidates"] if immutable_ref_key(entry["bundle_ref"]) == immutable_ref_key(selected)]
        if len(matches) != 1:
            raise ValueError("selected video bundle must appear exactly once in evaluated candidates")
        candidate = matches[0]
        if not candidate["eligible"] or not candidate["pareto_frontier"] or candidate["certificate_ref"] is None:
            raise ValueError("production video bundle must be eligible, certified, and Pareto-optimal")
        if candidate["rank_score"] is None or candidate["confidence_low"] is None:
            raise ValueError("production video bundle requires a score and lower confidence bound")


def validate_audio_event_graph_record(record: dict[str, Any]) -> None:
    validate_media_span(record["canonical_clock"], "audio_event_graph.canonical_clock")
    event_ids = [event["event_id"] for event in record["events"]]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("audio event IDs must be unique")
    known = set(event_ids)
    causal: dict[str, list[str]] = {event_id: [] for event_id in known}
    for edge in record["edges"]:
        if edge["source_event_id"] not in known or edge["target_event_id"] not in known:
            raise ValueError("audio event edge references an unknown event")
        if edge["relation"] in {"precedes", "causes"}:
            causal[edge["source_event_id"]].append(edge["target_event_id"])
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("audio causal graph contains a cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in causal[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)
    for node in causal:
        visit(node)
    for event in record["events"]:
        validate_media_span(event["span"], f"audio_event:{event['event_id']}")


def validate_application_command_record(record: dict[str, Any]) -> None:
    if record["direct_comfyui_mutation"] or record["raw_path_or_credentials_present"]:
        raise ValueError("browser command crosses the controller boundary")
    if record.get("offline_created") and record["command"] not in {"create_project", "save_draft"}:
        raise ValueError("offline mode may create or edit local drafts only")
    if record["command"] in {"promote_artifact", "start_final", "revoke_artifact"}:
        raise ValueError("legacy direct-authority UI command is forbidden")


def validate_multi_character_projection_record(record: dict[str, Any]) -> None:
    instances = record["instance_cards"]
    for field in ("character_instance_id", "provider_person_index", "render_order"):
        values = [entry[field] for entry in instances]
        if len(values) != len(set(values)):
            raise ValueError(f"multi-character projection requires unique {field}")
    if not record["projection_only"]:
        raise ValueError("editor projection cannot become authority")


def semantic_validate(rows: list[dict[str, Any]], registries: dict[str, dict[str, Any]], examples: dict[str, dict[str, Any]]) -> None:
    if len(rows) != 60 or [r["row_number"] for r in rows] != list(range(261, 321)):
        raise ValueError("Rows261-320 must contain exactly 60 contiguous rows")
    item_ids = {r["item_id"] for r in rows}
    if len(item_ids) != 60 or len({r["tracker_id"] for r in rows}) != 60:
        raise ValueError("Item and Tracker IDs must be unique")
    for row in rows:
        if row["runtime_completion_claimed"] or row["status"] != STATUS:
            raise ValueError(f"false runtime/status claim in {row['item_id']}")
        for dep in row["dependencies"]:
            if dep.startswith("ITEM-W64-") and dep not in item_ids and dep != "ITEM-W64-220":
                raise ValueError(f"unresolved dependency {dep}")
            if dep in item_ids and int(dep.rsplit("-", 1)[1]) >= row["row_number"]:
                raise ValueError(f"non-prior dependency {dep}")
    # Prove Row320 transitively reaches all new rows through the workstream chain.
    dep_map = {r["item_id"]: [d for d in r["dependencies"] if d in item_ids] for r in rows}
    seen: set[str] = set()
    stack = [rows[-1]["item_id"]]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(dep_map[current])
    if seen != item_ids:
        raise ValueError(f"Row320 is missing transitive dependencies: {sorted(item_ids - seen)}")
    if any(registry.get("runtime_completion_claimed") for registry in registries.values()):
        raise ValueError("registry claims runtime completion")
    route = examples["wave64_hyperreal_video_blocked_route.example.json"]
    validate_video_route_record(route)
    if route["production_execution_allowed"] or route["selected_bundle_ref"] is not None:
        raise ValueError("blocked planned video route became executable")
    command = examples["wave64_hyperreal_application_command.example.json"]
    validate_application_command_record(command)
    if command["direct_comfyui_mutation"] or command["raw_path_or_credentials_present"]:
        raise ValueError("application command crosses controller boundary")
    repair = examples["wave64_hyperreal_av_local_repair.example.json"]
    if not repair["accepted_parents_immutable"] or not repair["smallest_failed_scope_only"] or repair["full_av_rerender"]:
        raise ValueError("AV repair is not local and immutable-parent safe")
    validate_audio_event_graph_record(examples["wave64_hyperreal_audio_event_graph.example.json"])
    validate_multi_character_projection_record(examples["wave64_hyperreal_multi_character_editor_projection.example.json"])


def desired_outputs(project_root: Path) -> dict[str, bytes]:
    rows = build_rows()
    schemas = build_schemas()
    registries = build_registries()
    examples = build_examples()
    semantic_validate(rows, registries, examples)
    outputs: dict[str, bytes] = {}
    for path, content in docs().items():
        outputs[path] = text_bytes(content)
    for name, schema in schemas.items():
        outputs[f"Plan/08_SCHEMAS/{name}"] = canonical_json(schema)
    for name, registry in registries.items():
        outputs[f"Plan/10_REGISTRIES/{name}"] = canonical_json(registry)
    for name, example in examples.items():
        outputs[f"Plan/08_SCHEMAS/examples/{name}"] = canonical_json(example)

    requirements = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID, "updated_at": UPDATED_AT,
        "row_range": [261, 320], "status": STATUS, "runtime_completion_claimed": False,
        "workstreams": [{"id": wid, "slug": slug, "objective": objective} for wid, slug, objective in WORKSTREAMS],
        "rows": rows,
    }
    outputs["Plan/Items/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_REQUIREMENTS.json"] = canonical_json(requirements)
    outputs["Plan/Tracker/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_REQUIREMENTS.json"] = canonical_json(requirements)
    item_fields = ["row_number", "item_id", "tracker_id", "workstream_id", "workstream", "phase", "title", "objective", "dependencies", "required_artifacts", "acceptance_tests", "external_gates", "status", "runtime_completion_claimed", "source_citations"]
    item_rows = [{**r, "dependencies": "|".join(r["dependencies"]), "required_artifacts": "|".join(r["required_artifacts"]), "acceptance_tests": "|".join(r["acceptance_tests"]), "external_gates": "|".join(r["external_gates"]), "source_citations": "|".join(r["source_citations"])} for r in rows]
    outputs["Plan/Items/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_ITEM_ROWS.csv"] = csv_bytes(item_rows, item_fields)
    tracker_fields = [*item_fields, "tracker_state", "next_action", "blocker"]
    tracker_rows = [{**r, "dependencies": "|".join(r["dependencies"]), "required_artifacts": "|".join(r["required_artifacts"]), "acceptance_tests": "|".join(r["acceptance_tests"]), "external_gates": "|".join(r["external_gates"]), "source_citations": "|".join(r["source_citations"]), "tracker_state": "planned_not_started", "next_action": "main_task_review_and_formal_adoption", "blocker": "runtime_and_empirical_evidence_not_yet_implemented"} for r in rows]
    outputs["Plan/Tracker/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_TRACKER_ROWS.csv"] = csv_bytes(tracker_rows, tracker_fields)

    coverage = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID, "updated_at": UPDATED_AT,
        "status": "planning_contract_coverage_pass", "rows": len(rows), "schemas": len(schemas),
        "registries": len(registries), "examples": len(examples), "documents": len(docs()),
        "row320_transitively_depends_on_rows261_319": True, "runtime_completion_claimed": False,
        "runtime_execution_allowed": False, "production_application_built": False,
        "model_or_engine_qualification_performed": False,
    }
    coverage_bytes = canonical_json(coverage)
    outputs["Plan/Instructions/QA/Evidence/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PLANNING_COVERAGE.json"] = coverage_bytes
    outputs["Plan/Tracker/Evidence/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PLANNING_COVERAGE.json"] = coverage_bytes

    static_sources = [
        "Plan/07_IMPLEMENTATION/scripts/build_wave64_hyperreal_video_audio_app_third_pass_package.py",
        "Plan/Instructions/QA/Scripts/test_wave64_hyperreal_video_audio_app_third_pass_package.py",
        "Plan/Items/README.md", "Plan/Tracker/README.md",
        "Plan/Items/Waves/Wave64/README.md", "Plan/Tracker/Waves/Wave64/README.md",
        "Plan/Instructions/WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md",
    ]
    manifest_entries = []
    for path, content in sorted(outputs.items()):
        manifest_entries.append({"path": path, "sha256": sha256_bytes(content), "bytes": len(content), "source": "generated"})
    for path in static_sources:
        full = project_root / path
        if full.exists():
            content = full.read_bytes()
            manifest_entries.append({"path": path, "sha256": sha256_bytes(content), "bytes": len(content), "source": "static_preserved"})
    manifest = {
        "schema_version": "1.0.0", "package_id": PACKAGE_ID, "updated_at": UPDATED_AT,
        "status": "intentional_dirty_or_untracked_project_work_preserve_pending_main_task_adoption",
        "runtime_completion_claimed": False, "entries": sorted(manifest_entries, key=lambda entry: entry["path"]),
    }
    outputs["Plan/Instructions/Hydration_Rehydration/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PRESERVATION_MANIFEST.json"] = canonical_json(manifest)
    return outputs


def write_or_check(project_root: Path, mode: str) -> dict[str, Any]:
    outputs = desired_outputs(project_root)
    mismatches: list[str] = []
    for relative, expected in outputs.items():
        path = project_root / relative
        if mode == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        elif not path.exists():
            mismatches.append(f"missing:{relative}")
        elif path.read_bytes() != expected:
            mismatches.append(f"changed:{relative}")
    if mismatches:
        raise RuntimeError("; ".join(mismatches))
    schemas = build_schemas()
    registries = build_registries()
    examples = build_examples()
    return {
        "status": "PASS", "mode": mode, "package_id": PACKAGE_ID, "rows": len(build_rows()),
        "schemas": len(schemas), "registries": len(registries), "examples": len(examples),
        "generated_files_excluding_manifest": len(outputs) - 1, "runtime_completion_claimed": False,
        "runtime_execution_allowed": False, "production_application_built": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = write_or_check(args.root.resolve(), "write" if args.write else "check")
    except Exception as exc:  # fail closed for CLI use
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
