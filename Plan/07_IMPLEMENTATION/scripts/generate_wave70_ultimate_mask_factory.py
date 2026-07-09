from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
MASK_FACTORY_ROOT = PLAN / "07_IMPLEMENTATION" / "mask_factory"
ITEMS_ROOT = PLAN / "Items"
TRACKER_ROOT = PLAN / "Tracker"

PLAN_TAXONOMY_MD = MASK_FACTORY_ROOT / "ULTIMATE_MASK_FACTORY_TAXONOMY.md"
PLAN_TAXONOMY_JSON = MASK_FACTORY_ROOT / "ULTIMATE_MASK_FACTORY_TAXONOMY.json"
PLAN_COVERAGE_CSV = MASK_FACTORY_ROOT / "ULTIMATE_MASK_COVERAGE_MATRIX.csv"
PLAN_PROMOTION_GATES_MD = MASK_FACTORY_ROOT / "ULTIMATE_MASK_FACTORY_PROMOTION_GATES.md"
WAVE70_SCOPE_MD = PLAN / "Instructions" / "Waves" / "Wave70" / "WAVE70_SCOPE.md"

ITEMS_WAVE_DIR = ITEMS_ROOT / "Waves" / "Wave70"
TRACKER_WAVE_DIR = TRACKER_ROOT / "Waves" / "Wave70"

ITEMS_MASTER_CSV = ITEMS_ROOT / "wave70_ultimate_mask_factory_itemized_list.csv"
ITEMS_WAVE_CSV = ITEMS_WAVE_DIR / "WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv"
ITEMS_REQUIREMENTS_JSON = ITEMS_WAVE_DIR / "WAVE70_ULTIMATE_MASK_FACTORY_REQUIREMENTS.json"
ITEMS_REPORT_JSON = ITEMS_ROOT / "Reports" / "wave70_ultimate_mask_factory_coverage_report.json"

TRACKER_MASTER_CSV = TRACKER_ROOT / "wave70_ultimate_mask_factory_tracker.csv"
TRACKER_WAVE_CSV = TRACKER_WAVE_DIR / "WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv"
TRACKER_REQUIREMENTS_JSON = TRACKER_WAVE_DIR / "WAVE70_ULTIMATE_MASK_FACTORY_REQUIREMENTS.json"
TRACKER_REPORT_JSON = TRACKER_ROOT / "Reports" / "wave70_ultimate_mask_factory_coverage_report.json"


ITEMS_HEADER = [
    "Item_ID",
    "Item_Wave",
    "Item_Type",
    "Item_Title",
    "Item_Category",
    "Item_Domain",
    "Owner_Domain",
    "Autonomous_Required",
    "Human_Input_Allowed",
    "Human_Work_Allowed",
    "Codex_Action",
    "Implementation_Target",
    "Deliverable_Type",
    "Acceptance_Criteria",
    "QA_Gates_Required",
    "Visual_Review_Required",
    "Visual_Review_Method",
    "Test_Required",
    "Evidence_Required",
    "Runtime_Proof_Required",
    "EC2_Allowed",
    "Blocker_Policy",
    "Source_Plan_Root",
    "Citation_File",
    "Citation_Full_Path",
    "Citation_Section",
    "Citation_Line_Start",
    "Citation_Line_End",
    "Citation_Excerpt",
    "Source_Package",
    "Source_Type",
    "Source_File_Size",
    "Priority",
    "Risk_Level",
    "Status",
    "Created_From",
    "Notes",
    "Source_Key",
    "Source_File_Relative",
    "Coverage_Level",
    "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]

TRACKER_HEADER = [
    "Tracker_ID",
    "Wave",
    "Phase",
    "Workstream",
    "Priority",
    "Risk_Level",
    "Owner_Role",
    "Environment",
    "Status",
    "Task_Name",
    "Detailed_Action",
    "Completion_Criteria",
    "Acceptance_Evidence",
    "Dependency_Prerequisite",
    "Validation_Method",
    "Output_Artifact",
    "Source_Path",
    "Related_Source_Paths",
    "Package_Top_Level_Directory",
    "Autonomous_Execution_Mode",
    "Human_Input_Allowed",
    "Human_Work_Allowed",
    "Codex_Desktop_Action",
    "QA_Strictness",
    "Visual_Review_Required",
    "Visual_Review_Method",
    "Test_Required",
    "Runtime_Proof_Required",
    "EC2_Allowed",
    "Preview_Required",
    "Final_Render_Gate",
    "Evidence_Path",
    "Citation_File",
    "Citation_Full_Path",
    "Citation_Section",
    "Citation_Line_Start",
    "Citation_Line_End",
    "Citation_Excerpt",
    "Source_Package",
    "Source_Type",
    "Source_Item_ID",
    "Blocker_Policy",
    "Rerun_Policy",
    "Status_Decision",
    "Notes",
    "Source_Key",
    "Source_File_Relative",
    "Coverage_Level",
    "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]

COVERAGE_HEADER = [
    "mask_type_id",
    "tier",
    "region_group",
    "body_part",
    "subregion",
    "mask_role",
    "owner_scope",
    "scale",
    "edit_allowed",
    "protect_required",
    "body_regions",
    "required_for_images",
    "required_for_video",
    "required_for_audio_sync",
    "soft_body_role",
    "deformation_type",
    "gravity_sensitive",
    "collision_sensitive",
    "multi_character_allowed",
    "temporal_required",
    "allowed_workflow_routes",
    "protected_regions",
    "required_evidence",
    "qa_gates",
    "promotion_rule",
    "status",
    "item_id",
    "tracker_id",
    "source_key",
    "source_file_relative",
    "citation_section",
    "citation_line_start",
    "citation_line_end",
]


GLOBAL_QA_GATES = [
    "mask_contract_schema_pass",
    "owner_instance_assignment_pass",
    "mask_png_or_map_generated",
    "preview_overlay_generated",
    "semantic_mask_alignment_pass",
    "protected_neighbor_check_pass",
    "quality_score_minimum_85",
    "workflow_routing_manifest_pass",
    "generated_output_proof_required",
    "strict_whole_artifact_visual_qa_pass",
    "reference_image_matrix_pass",
    "model_backed_geometry_authority_pass",
    "source_derived_landmark_or_segmentation_pass",
    "wave70_mask_geometry_gate_pass",
    "wave70_mask_promotion_gate_pass",
]

TEMPORAL_QA_GATES = [
    "frame_grid_review_pass",
    "playback_review_pass",
    "temporal_drift_check_pass",
    "repair_span_isolation_pass",
    "loop_boundary_or_cut_integrity_pass",
]

AUDIO_QA_GATES = [
    "full_duration_playback_review_pass",
    "audio_event_visual_alignment_pass",
    "clipping_noise_mix_balance_pass",
    "av_sync_and_drift_check_pass",
]

SOFT_BODY_QA_GATES = [
    "pose_aware_deformation_map_pass",
    "gravity_direction_check_pass",
    "collision_contact_check_pass",
    "anchor_region_protection_pass",
    "shape_identity_continuity_pass",
]

def row(
    mask_type_id: str,
    tier: str,
    region_group: str,
    body_part: str,
    subregion: str,
    mask_role: str,
    protected_regions: list[str],
    *,
    owner_scope: str = "single_character",
    scale: str = "minor",
    body_regions: bool = False,
    required_for_images: bool = True,
    required_for_video: bool = True,
    required_for_audio_sync: bool = False,
    soft_body_role: str = "none",
    deformation_type: str = "none",
    gravity_sensitive: bool = False,
    collision_sensitive: bool = False,
    multi_character_allowed: bool = False,
    temporal_required: bool = False,
    allowed_workflow_routes: list[str] | None = None,
    extra_qa_gates: list[str] | None = None,
) -> dict[str, object]:
    routes = allowed_workflow_routes or [
        "regional_inpaint",
        "controlnet_guidance",
        "reference_attention",
        "mask_protected_negative",
    ]
    qa_gates = list(GLOBAL_QA_GATES)
    if temporal_required or required_for_video:
        qa_gates.extend(TEMPORAL_QA_GATES)
    if required_for_audio_sync:
        qa_gates.extend(AUDIO_QA_GATES)
    if soft_body_role != "none" or deformation_type != "none":
        qa_gates.extend(SOFT_BODY_QA_GATES)
    if extra_qa_gates:
        qa_gates.extend(extra_qa_gates)
    qa_gates = list(dict.fromkeys(qa_gates))
    return {
        "mask_type_id": mask_type_id,
        "tier": tier,
        "region_group": region_group,
        "body_part": body_part,
        "subregion": subregion,
        "mask_role": mask_role,
        "owner_scope": owner_scope,
        "scale": scale,
        "edit_allowed": "true",
        "protect_required": "true",
        "body_regions": "true" if body_regions else "false",
        "required_for_images": "true" if required_for_images else "false",
        "required_for_video": "true" if required_for_video else "false",
        "required_for_audio_sync": "true" if required_for_audio_sync else "false",
        "soft_body_role": soft_body_role,
        "deformation_type": deformation_type,
        "gravity_sensitive": "true" if gravity_sensitive else "false",
        "collision_sensitive": "true" if collision_sensitive else "false",
        "multi_character_allowed": "true" if multi_character_allowed else "false",
        "temporal_required": "true" if temporal_required else "false",
        "allowed_workflow_routes": routes,
        "protected_regions": protected_regions,
        "required_evidence": [
            "mask_contract_json",
            "mask_artifact_png_or_map_json",
            "mask_preview_overlay",
            "quality_score_json",
            "workflow_patch_manifest",
            "generated_output_artifact",
            "whole_artifact_qa_report",
            "target_runtime_evidence_before_final_certification",
        ],
        "qa_gates": qa_gates,
        "promotion_rule": "not_complete_until_local_proof_runtime_routing_generated_output_and_whole_artifact_qa_pass",
        "status": "required_not_complete",
    }


def build_taxonomy() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    add = rows.append

    # Tier 1: identity and core face anatomy.
    for mask_id, body, sub, scale, protected in [
        ("mf70_face_full_instance", "face", "full_face_identity_region", "major", ["hairline", "neck", "ears", "background", "clothing"]),
        ("mf70_face_identity_critical", "face", "identity_critical_triangle", "minor", ["eyes", "nose", "mouth", "jawline", "hairline"]),
        ("mf70_expression_region", "face", "brows_eyes_cheeks_mouth_expression", "minor", ["identity_anchor", "hairline", "teeth", "background"]),
        ("mf70_forehead_skin", "face", "forehead_skin", "minor", ["eyebrows", "hairline", "eyes", "background"]),
        ("mf70_cheeks_skin", "face", "left_right_cheeks_skin", "minor", ["eyes", "nose", "mouth", "hairline", "jawline"]),
        ("mf70_jawline_chin", "face", "jawline_chin_contour", "minor", ["mouth", "neck", "hair", "clothing"]),
        ("mf70_ears", "face", "left_right_ears", "micro", ["hair", "jawline", "background", "jewelry"]),
        ("mf70_skin_tone_continuity", "skin", "global_visible_skin_tone_continuity", "major", ["identity_anchor", "clothing", "background"]),
    ]:
        add(row(mask_id, "tier_1_core_identity_anatomy", "core_identity_face", body, sub, "edit_or_protect_identity_region", protected, scale=scale))

    # Tier 1b: fine facial detail.
    for mask_id, body, sub, scale, protected in [
        ("mf70_eyes_full", "eyes", "both_eyes_full_region", "micro", ["pupils", "iris", "eyelids", "eyelashes", "eyebrows", "skin"]),
        ("mf70_left_eye", "eyes", "left_eye_full_region", "micro", ["pupil", "iris", "eyelids", "eyelashes", "skin"]),
        ("mf70_right_eye", "eyes", "right_eye_full_region", "micro", ["pupil", "iris", "eyelids", "eyelashes", "skin"]),
        ("mf70_pupils_iris_sclera", "eyes", "pupils_iris_sclera", "nano", ["eyelids", "eyelashes", "catchlights", "skin"]),
        ("mf70_eyelids", "eyes", "upper_lower_eyelids", "nano", ["iris", "sclera", "eyelashes", "skin"]),
        ("mf70_eyelashes", "eyes", "upper_lower_eyelashes", "nano", ["eyelids", "iris", "skin", "background"]),
        ("mf70_under_eye", "eyes", "under_eye_skin", "micro", ["eyes", "eyelids", "cheeks", "nose"]),
        ("mf70_eyebrows", "brows", "left_right_eyebrows", "micro", ["forehead", "eyes", "hairline", "skin"]),
        ("mf70_nose", "nose", "full_nose_bridge_tip_nostrils", "micro", ["eyes", "cheeks", "mouth", "skin"]),
        ("mf70_mouth_lips", "mouth", "outer_mouth_lips", "micro", ["teeth", "tongue", "chin", "cheeks", "skin"]),
        ("mf70_teeth", "mouth", "teeth", "nano", ["lips", "tongue", "inner_mouth", "face_skin"]),
        ("mf70_tongue_inner_mouth", "mouth", "tongue_inner_mouth", "nano", ["teeth", "lips", "chin", "face_skin"]),
        ("mf70_makeup_cosmetics", "face", "eyeliner_lipstick_blush_makeup", "micro", ["identity_anchor", "eyes", "lips", "skin_tone"]),
    ]:
        add(row(mask_id, "tier_1_core_identity_anatomy", "face_detail_subregions", body, sub, "edit_or_protect_facial_detail", protected, scale=scale))

    # Tier 1c: hair, scalp, marks, and skin identity continuity.
    for mask_id, body, sub, scale, protected in [
        ("mf70_hair_full", "hair", "full_hair_volume", "major", ["face", "ears", "neck", "background", "clothing"]),
        ("mf70_hairline_edges", "hair", "hairline_edges", "micro", ["forehead", "face_identity", "background"]),
        ("mf70_hair_strands_flyaways", "hair", "strands_flyaways", "nano", ["face", "background", "clothing"]),
        ("mf70_scalp", "scalp", "visible_scalp", "micro", ["hair", "forehead", "background"]),
        ("mf70_body_hair", "body_hair", "visible_body_hair", "micro", ["skin", "clothing", "background"]),
        ("mf70_facial_hair", "facial_hair", "beard_mustache_stubble", "micro", ["mouth", "jawline", "cheeks", "skin"]),
        ("mf70_tattoos_scars_freckles_moles", "skin_marks", "tattoos_scars_freckles_moles_birthmarks", "micro", ["skin_tone", "body_shape", "clothing"]),
        ("mf70_tanlines_pressure_marks", "skin_marks", "tanlines_pressure_marks", "micro", ["skin_tone", "clothing_edges", "contact_shadow"]),
    ]:
        add(row(mask_id, "tier_1_core_identity_anatomy", "hair_scalp_skin_marks", body, sub, "edit_or_protect_identity_surface_detail", protected, scale=scale))

    # Tier 2: body skin zones and limb anatomy.
    for mask_id, body, sub, scale, protected in [
        ("mf70_neck", "neck", "front_side_back_neck", "minor", ["face", "hair", "clothing_collar", "jewelry"]),
        ("mf70_shoulders", "shoulders", "left_right_shoulders", "major", ["neck", "upper_arms", "clothing", "background"]),
        ("mf70_chest_upper_torso", "torso", "chest_upper_torso_skin", "major", ["neck", "clothing", "arms", "background"]),
        ("mf70_abdomen_stomach", "torso", "abdomen_stomach_skin", "major", ["chest", "waist", "clothing", "hands"]),
        ("mf70_belly_button_umbilicus", "torso", "belly_button_umbilicus", "micro", ["abdomen", "waist", "clothing", "hands"]),
        ("mf70_waist_hips", "torso", "waist_hips_contour", "major", ["abdomen", "pelvis", "clothing", "thighs"]),
        ("mf70_back", "torso", "back_skin_and_shape", "major", ["neck", "shoulders", "hips", "clothing"]),
        ("mf70_left_arm", "arms", "left_full_arm", "major", ["shoulder", "elbow", "wrist", "clothing", "background"]),
        ("mf70_right_arm", "arms", "right_full_arm", "major", ["shoulder", "elbow", "wrist", "clothing", "background"]),
        ("mf70_left_upper_arm", "arms", "left_upper_arm", "minor", ["shoulder", "elbow", "clothing", "background"]),
        ("mf70_right_upper_arm", "arms", "right_upper_arm", "minor", ["shoulder", "elbow", "clothing", "background"]),
        ("mf70_left_forearm", "arms", "left_forearm", "minor", ["elbow", "wrist", "hand", "clothing"]),
        ("mf70_right_forearm", "arms", "right_forearm", "minor", ["elbow", "wrist", "hand", "clothing"]),
        ("mf70_elbows", "arms", "left_right_elbows", "minor", ["upper_arm", "forearm", "clothing"]),
        ("mf70_wrists", "arms", "left_right_wrists", "minor", ["hands", "forearms", "watch_jewelry", "clothing_cuff"]),
        ("mf70_hands_full", "hands", "both_hands_full", "major", ["fingers", "wrists", "held_objects", "other_body_parts"]),
        ("mf70_left_hand", "hands", "left_hand_full", "major", ["fingers", "wrist", "held_objects", "contact_patch"]),
        ("mf70_right_hand", "hands", "right_hand_full", "major", ["fingers", "wrist", "held_objects", "contact_patch"]),
        ("mf70_fingers", "hands", "all_fingers", "micro", ["knuckles", "fingernails", "palms", "held_objects"]),
        ("mf70_fingertips_fingernails", "hands", "fingertips_fingernails", "nano", ["fingers", "held_objects", "skin"]),
        ("mf70_palms_knuckles", "hands", "palms_knuckles", "micro", ["fingers", "wrist", "held_objects"]),
        ("mf70_thighs", "legs", "left_right_thighs", "major", ["hips", "knees", "clothing", "support_surface"]),
        ("mf70_knees", "legs", "left_right_knees", "minor", ["thighs", "calves", "clothing"]),
        ("mf70_calves", "legs", "left_right_calves", "major", ["knees", "ankles", "clothing", "background"]),
        ("mf70_ankles", "feet", "left_right_ankles", "minor", ["calves", "feet", "socks_shoes"]),
        ("mf70_feet_full", "feet", "both_feet_full", "major", ["toes", "ankles", "floor", "shoes_socks"]),
        ("mf70_toes_toenails", "feet", "toes_toenails", "nano", ["feet", "floor", "shoes_socks"]),
        ("mf70_body_skin_visible", "skin", "all_visible_body_skin_excluding_face", "major", ["face", "hair", "clothing", "background"]),
    ]:
        add(row(mask_id, "tier_1_core_identity_anatomy", "skin_surface_zones_and_limbs", body, sub, "edit_or_protect_anatomy_region", protected, scale=scale))

    # Tier 3: clothing, material, and accessories.
    for mask_id, body, sub, scale, protected in [
        ("mf70_clothing_full_item", "clothing", "full_clothing_item_instance", "major", ["skin", "body_shape", "background", "accessories"]),
        ("mf70_shirt_top", "clothing", "shirt_top_blouse_jacket", "major", ["neck", "arms", "torso_skin", "hair"]),
        ("mf70_pants_skirt_dress", "clothing", "pants_skirt_dress", "major", ["waist", "legs", "support_surface", "background"]),
        ("mf70_sleeves_collars_cuffs_hems", "clothing_detail", "sleeves_collars_cuffs_hems", "micro", ["skin", "wrists", "neck", "fabric_body"]),
        ("mf70_straps_buttons_zippers", "clothing_detail", "straps_buttons_zippers", "nano", ["skin", "fabric", "jewelry"]),
        ("mf70_fabric_folds_seams", "clothing_detail", "fabric_folds_seams", "micro", ["skin", "body_shape", "lighting", "contact_shadow"]),
        ("mf70_sheer_transparent_fabric", "material", "transparent_sheer_fabric", "micro", ["skin", "clothing_edge", "identity", "background"]),
        ("mf70_wet_stretched_compressed_fabric", "material", "wet_stretched_compressed_fabric", "micro", ["skin", "body_shape", "fabric_folds", "lighting"]),
        ("mf70_shoes_socks_gloves", "clothing", "shoes_socks_gloves", "minor", ["feet", "hands", "floor", "clothing"]),
        ("mf70_jewelry_piercings", "accessories", "jewelry_piercings", "nano", ["skin", "hair", "clothing", "reflection"]),
        ("mf70_glasses", "accessories", "glasses", "micro", ["eyes", "nose", "ears", "reflections"]),
        ("mf70_watches_belts_bags", "accessories", "watches_belts_bags", "minor", ["skin", "clothing", "hands", "background"]),
        ("mf70_hats_hair_accessories", "accessories", "hats_hair_accessories", "minor", ["hair", "forehead", "background"]),
    ]:
        add(row(mask_id, "tier_2_clothing_material_accessory", "clothing_material_accessories", body, sub, "edit_or_protect_material_or_accessory", protected, scale=scale))

    # Tier 4: support surfaces, scene objects, shadows, camera safety.
    for mask_id, body, sub, scale, protected in [
        ("mf70_support_surface_bed", "support_surface", "bed_mattress", "major", ["body_contact", "blanket", "shadow", "background"]),
        ("mf70_support_surface_chair_couch", "support_surface", "chair_couch", "major", ["body_contact", "clothing", "shadow", "background"]),
        ("mf70_support_surface_floor_wall_table", "support_surface", "floor_wall_table", "major", ["feet", "hands", "objects", "shadow"]),
        ("mf70_blanket_pillow_fabric_support", "support_surface", "blanket_pillow_fabric_support", "major", ["body_contact", "clothing", "hair", "shadow"]),
        ("mf70_held_objects_props", "props", "held_objects_props", "minor", ["hands", "fingers", "body", "background"]),
        ("mf70_object_between_body", "props", "object_between_body_regions", "minor", ["body_a", "body_b", "contact_shadow", "occlusion_boundary"]),
        ("mf70_background_objects", "scene", "background_objects", "major", ["foreground_character", "depth_layer", "lighting"]),
        ("mf70_foreground_character_instance", "scene", "foreground_character_instance", "major", ["background", "support_surface", "shadow"]),
        ("mf70_background_depth_layer", "scene", "background_depth_layer", "major", ["foreground_character", "reflection", "lighting"]),
        ("mf70_crop_safety_head_hands_feet", "camera", "crop_safety_head_hands_feet", "major", ["frame_edge", "full_character", "background"]),
        ("mf70_frame_edge_risk", "camera", "frame_edge_risk_regions", "minor", ["hands", "feet", "hair", "props"]),
        ("mf70_mirror_reflection", "scene", "mirror_reflection", "major", ["reflected_identity", "lighting", "background"]),
        ("mf70_shadow_only", "lighting", "shadow_only_regions", "minor", ["body", "support_surface", "background"]),
        ("mf70_contact_shadow_cast_shadow", "lighting", "contact_and_cast_shadows", "micro", ["skin", "clothing", "support_surface", "props"]),
        ("mf70_lighting_correction", "lighting", "localized_lighting_correction", "major", ["identity", "skin_tone", "clothing_color", "background"]),
        ("mf70_reflection_highlight", "lighting", "reflections_highlights", "micro", ["eyes", "jewelry", "glasses", "wet_fabric", "skin"]),
    ]:
        add(row(mask_id, "tier_3_contact_occlusion_support_surface", "scene_camera_lighting_support", body, sub, "edit_or_protect_scene_physics_region", protected, scale=scale))

    # Tier 5: contact, occlusion, and multi-character interaction.
    for mask_id, body, sub, scale, owner, protected in [
        ("mf70_contact_patch_generic", "contact", "generic_contact_patch", "micro", "single_or_multi_character", ["both_sides_of_contact", "shadow", "background"]),
        ("mf70_pressure_compression_patch", "contact", "pressure_compression_patch", "micro", "single_or_multi_character", ["contact_owner_a", "contact_owner_b", "material_edge"]),
        ("mf70_occlusion_boundary", "occlusion", "occlusion_boundary", "micro", "single_or_multi_character", ["foreground_owner", "background_owner", "edge_detail"]),
        ("mf70_limb_over_limb", "occlusion", "limb_over_limb", "minor", "single_or_multi_character", ["limb_a", "limb_b", "contact_shadow", "skin_tone"]),
        ("mf70_hand_grip", "hands", "hand_grip_on_object_or_body", "micro", "single_or_multi_character", ["fingers", "object_or_body", "wrist", "contact_shadow"]),
        ("mf70_hand_on_body", "interaction", "hand_on_body_contact", "micro", "single_or_multi_character", ["hand_owner", "body_owner", "fingers", "skin", "shadow"]),
        ("mf70_hand_on_object", "interaction", "hand_on_object_contact", "micro", "single_or_multi_character", ["hand", "object", "fingers", "shadow"]),
        ("mf70_body_on_bed_chair", "interaction", "body_on_support_surface_contact", "minor", "single_or_multi_character", ["body", "support_surface", "clothing", "shadow"]),
        ("mf70_multi_character_instance_a", "multi_character", "character_a_full_instance", "major", "multi_character", ["character_b", "background", "shared_contact"]),
        ("mf70_multi_character_instance_b", "multi_character", "character_b_full_instance", "major", "multi_character", ["character_a", "background", "shared_contact"]),
        ("mf70_multi_character_body_part_owner", "multi_character", "per_character_body_part_owner", "minor", "multi_character", ["other_character", "clothing", "contact_shadow"]),
        ("mf70_shared_contact_patch", "multi_character", "shared_contact_patch", "micro", "multi_character", ["character_a", "character_b", "occlusion_boundary"]),
        ("mf70_character_a_touching_b", "multi_character", "character_a_touching_character_b", "micro", "multi_character", ["character_a_hand", "character_b_body", "identity_anchors"]),
        ("mf70_character_a_occluding_b", "multi_character", "character_a_occluding_character_b", "minor", "multi_character", ["character_a", "character_b", "edge_boundary"]),
        ("mf70_character_separation_boundary", "multi_character", "character_separation_boundary", "micro", "multi_character", ["character_a", "character_b", "background"]),
        ("mf70_identity_protection_per_person", "multi_character", "identity_protection_per_person", "major", "multi_character", ["other_person_identity", "hair", "clothing"]),
        ("mf70_clothing_accessory_ownership_per_person", "multi_character", "clothing_accessory_ownership_per_person", "minor", "multi_character", ["other_person", "shared_contact", "background"]),
    ]:
        add(row(mask_id, "tier_4_multi_character_interaction", "contact_occlusion_multi_character", body, sub, "contact_or_ownership_mask", protected, owner_scope=owner, scale=scale, multi_character_allowed=True, collision_sensitive=True, required_for_audio_sync=mask_id in {"mf70_hand_grip", "mf70_hand_on_body", "mf70_hand_on_object", "mf70_body_on_bed_chair", "mf70_shared_contact_patch"}))

    # Tier 6: soft-body, deformation, morphing, gravity, collision, and mesh controls.
    for mask_id, body, sub, scale, role, deformation, gravity, collision, multi, protected in [
        ("mf70_abdomen_soft_body_weight", "soft_body", "abdomen_stomach_soft_body_weight_map", "major", "soft_body_weight", "breath_sag_stretch_rebound", True, True, False, ["ribcage_anchor", "waist", "clothing", "hands"]),
        ("mf70_thigh_soft_body_weight", "soft_body", "thigh_soft_body_weight_map", "major", "soft_body_weight", "compression_gravity_rebound", True, True, False, ["hips", "knees", "clothing", "support_surface"]),
        ("mf70_upper_arm_soft_body_weight", "soft_body", "upper_arm_soft_body_weight_map", "minor", "soft_body_weight", "compression_sag_rebound", True, True, False, ["shoulder", "elbow", "clothing"]),
        ("mf70_cheek_face_soft_body_weight", "soft_body", "cheek_face_softness_weight_map", "micro", "soft_body_weight", "expression_softness_identity_preserving", False, False, False, ["eyes", "mouth", "jawline", "identity_anchor"]),
        ("mf70_body_morph_torso_shape", "morph", "torso_shape_morph_region", "major", "morph_region", "body_shape_morph", True, False, False, ["skeletal_anchor", "skin_marks", "clothing_edges"]),
        ("mf70_body_morph_waist_hips", "morph", "waist_hips_shape_morph_region", "major", "morph_region", "body_shape_morph", True, False, False, ["abdomen", "pelvis", "thighs", "clothing"]),
        ("mf70_body_morph_limbs", "morph", "arms_legs_shape_morph_region", "major", "morph_region", "body_part_shape_morph", True, False, False, ["joints", "hands", "feet", "clothing"]),
        ("mf70_face_morph_identity_guard", "morph", "face_shape_morph_identity_guard", "minor", "morph_guard", "face_morph_identity_preserving", False, False, False, ["eyes", "mouth", "nose", "jawline", "hairline"]),
        ("mf70_gravity_sag_field", "deformation", "pose_aware_gravity_sag_field", "major", "deformation_field", "gravity_sag", True, False, False, ["skeletal_anchor", "support_contact", "clothing"]),
        ("mf70_collision_compression_field", "deformation", "collision_compression_field", "minor", "deformation_field", "collision_compression", True, True, True, ["contact_owner_a", "contact_owner_b", "surface_edge"]),
        ("mf70_ripple_rebound_decay_field", "deformation", "ripple_rebound_decay_field", "minor", "deformation_field", "jiggle_ripple_rebound_decay", True, True, True, ["anchor_regions", "contact_patch", "clothing"]),
        ("mf70_soft_body_mesh_control_lattice", "deformation", "soft_body_mesh_control_lattice", "major", "mesh_control", "mesh_lattice_deformation", True, True, True, ["skeletal_anchor", "identity_anchor", "hands", "feet"]),
        ("mf70_multi_character_soft_body_contact_pair", "deformation", "multi_character_soft_body_contact_pair", "minor", "contact_deformation", "multi_character_collision_compression", True, True, True, ["character_a_anchor", "character_b_anchor", "identity_regions"]),
        ("mf70_protected_skeletal_joint_anchor", "protected_anchor", "skeletal_joint_anchor_regions", "major", "protected_anchor", "none", False, False, True, ["shoulders", "elbows", "wrists", "hips", "knees", "ankles"]),
        ("mf70_protected_hands_fingers_anchor", "protected_anchor", "hands_fingers_anchor_regions", "major", "protected_anchor", "none", False, False, True, ["hands", "fingers", "fingernails", "held_objects"]),
        ("mf70_protected_clothing_seam_anchor", "protected_anchor", "clothing_seam_anchor_regions", "micro", "protected_anchor", "none", False, True, True, ["seams", "buttons", "zippers", "fabric_folds"]),
    ]:
        add(row(mask_id, "tier_5_soft_body_deformation", "soft_body_deformation_morphing", body, sub, "soft_body_deformation_or_protected_anchor", protected, scale=scale, soft_body_role=role, deformation_type=deformation, gravity_sensitive=gravity, collision_sensitive=collision, multi_character_allowed=multi, temporal_required=True, required_for_audio_sync=collision or mask_id in {"mf70_abdomen_soft_body_weight", "mf70_ripple_rebound_decay_field", "mf70_multi_character_soft_body_contact_pair"}))

    # Tier 7: video/temporal masks.
    for mask_id, body, sub, scale, protected in [
        ("mf70_per_frame_propagated_mask", "video", "per_frame_propagated_mask", "temporal", ["source_mask", "owner_instance", "frame_edges"]),
        ("mf70_mask_drift_detection", "video", "mask_drift_detection_region", "temporal", ["identity", "body_part", "background"]),
        ("mf70_occlusion_enter_exit", "video", "occlusion_enter_exit_frames", "temporal", ["foreground", "background", "contact_patch"]),
        ("mf70_motion_blur_region", "video", "motion_blur_region", "temporal", ["body_part", "edge_detail", "background"]),
        ("mf70_contact_persistence_frames", "video", "frame_to_frame_contact_persistence", "temporal", ["contact_owner_a", "contact_owner_b", "shadow"]),
        ("mf70_visibility_state_body_part", "video", "body_part_visibility_state", "temporal", ["owner_instance", "occluder", "background"]),
        ("mf70_continuity_clothing_hair_accessory_skinmarks", "video", "clothing_hair_accessory_skinmark_continuity", "temporal", ["identity", "body_shape", "lighting"]),
        ("mf70_repair_span_bad_frames_only", "video", "bad_frame_repair_span_only", "temporal", ["good_frames_before_after", "identity", "motion"]),
    ]:
        add(row(mask_id, "tier_6_temporal_video_propagation", "video_temporal_masks", body, sub, "temporal_tracking_or_repair_mask", protected, scale=scale, temporal_required=True, allowed_workflow_routes=["video_mask_propagation", "temporal_repair", "frame_grid_review", "playback_review"], extra_qa_gates=["no_single_frame_only_certification"]))

    # Tier 8: audio-linked event masks.
    for mask_id, body, sub, scale, protected in [
        ("mf70_audio_footstep_contact", "audio_event", "footstep_contact_region", "audio", ["foot", "floor", "shadow", "timing_anchor"]),
        ("mf70_audio_hand_contact", "audio_event", "hand_contact_region", "audio", ["hand", "object_or_body", "timing_anchor"]),
        ("mf70_audio_clothing_rustle", "audio_event", "clothing_rustle_region", "audio", ["fabric", "body_motion", "contact_patch"]),
        ("mf70_audio_object_impact", "audio_event", "object_impact_region", "audio", ["object", "surface", "hand", "timing_anchor"]),
        ("mf70_audio_bed_chair_couch_compression", "audio_event", "support_surface_compression_region", "audio", ["body", "support_surface", "fabric"]),
        ("mf70_audio_mouth_dialogue", "audio_event", "mouth_dialogue_region", "audio", ["mouth", "lips", "teeth", "face_identity"]),
        ("mf70_audio_breath_chest_motion", "audio_event", "breath_chest_motion_region", "audio", ["chest", "neck", "clothing", "face"]),
        ("mf70_audio_event_visual_alignment", "audio_event", "audio_event_to_visual_contact_alignment", "audio", ["event_source", "contact_patch", "timeline"]),
    ]:
        add(row(mask_id, "tier_7_audio_linked_event_masks", "audio_linked_masks", body, sub, "audio_visual_event_alignment_mask", protected, scale=scale, required_for_video=True, required_for_audio_sync=True, temporal_required=True, allowed_workflow_routes=["audio_event_alignment", "foley_timing", "av_sync_review", "visual_contact_review"]))

    # Tier 9: body region masks. These are ordinary mask targets under the same gates as every other row.
    for mask_id, body, sub, scale, protected in [
        ("mf70_multi_character_anatomy_separation", "body_regions", "multi_character_body_regions_separation", "minor", ["character_a", "character_b", "shared_contact", "identity"]),
    ]:
        add(row(mask_id, "tier_1_core_identity_anatomy", "body_regions", body, sub, "body_region_mask", protected, owner_scope="single_or_multi_character", scale=scale, body_regions=True, multi_character_allowed=mask_id == "mf70_multi_character_anatomy_separation", allowed_workflow_routes=["mask_factory_local_first"], extra_qa_gates=["whole_body_geometry_authority_pass", "body_region_geometry_pass", "protected_overlap_matrix_pass"]))

    return rows


def as_bool_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def join_list(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("/", "\\")


def write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for source_row in rows:
            writer.writerow({key: source_row.get(key, "") for key in header})


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_markdown(taxonomy_rows: list[dict[str, object]]) -> tuple[list[str], dict[str, dict[str, int | str]]]:
    lines: list[str] = []
    line_map: dict[str, dict[str, int | str]] = {}

    def add_line(text: str = "") -> None:
        lines.append(text)

    add_line("# Wave70 Ultimate Mask Factory Taxonomy")
    add_line("")
    add_line("Purpose: define the source-cited mask taxonomy that the autonomous Comfy_UI_Main build must use before Mask Factory work can be considered complete for hyperrealistic image, video, and audio generation.")
    add_line("")
    add_line("Current evidence boundary: the existing W69 evidence proves only one narrow local face-skin no-mouth micro mask. It does not certify broad body, clothing, interaction, temporal, audio-linked, body regions, or soft-body deformation coverage.")
    add_line("")
    add_line("Global rule: every mask type is both an edit target and a protection contract. A localized mask cannot pass if whole-artifact visual, temporal, or audio QA finds unrelated full-frame or full-duration defects.")
    add_line("")
    add_line("Promotion rule: no mask type is complete until it has source-cited contract, generated mask or map, preview overlay, protected-neighbor checks, quality score, workflow routing proof, generated-output proof, strict whole-artifact QA, and target-runtime evidence before final certification.")
    add_line("")
    add_line("Body-region rule: body-region mask types are ordinary mask targets. They use the same source-derived geometry, protected-neighbor, reference-matrix, and hard promotion gates as every other body part.")
    add_line("")
    add_line("Soft-body rule: soft-body, gravity, collision, morphing, jiggle, ripple, and rebound masks are deformation or protection maps. They must preserve skeletal anchors, face identity, hands, clothing seams, jewelry, other characters, support surfaces, and temporal continuity.")
    add_line("")

    grouped: dict[str, list[dict[str, object]]] = {}
    for item in taxonomy_rows:
        grouped.setdefault(str(item["region_group"]), []).append(item)

    group_titles = {
        "core_identity_face": "Core Identity Face",
        "face_detail_subregions": "Face Detail Subregions",
        "hair_scalp_skin_marks": "Hair, Scalp, Skin Marks",
        "skin_surface_zones_and_limbs": "Skin Surface Zones And Limbs",
        "clothing_material_accessories": "Clothing, Material, Accessories",
        "scene_camera_lighting_support": "Scene, Camera, Lighting, Support",
        "contact_occlusion_multi_character": "Contact, Occlusion, Multi-Character",
        "soft_body_deformation_morphing": "Soft Body, Deformation, Morphing",
        "video_temporal_masks": "Video Temporal Masks",
        "audio_linked_masks": "Audio Linked Masks",
    }

    for group_key, rows in grouped.items():
        section_start = len(lines) + 1
        title = group_titles.get(group_key, group_key.replace("_", " ").title())
        add_line(f"## {title}")
        add_line("")
        add_line(f"Source key prefix: W70:{group_key}")
        add_line("")
        add_line("Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.")
        add_line("")
        add_line("| mask_type_id | body_part | subregion | role | protected_regions |")
        add_line("| --- | --- | --- | --- | --- |")
        for item in rows:
            add_line(
                "| {mask_type_id} | {body_part} | {subregion} | {mask_role} | {protected} |".format(
                    mask_type_id=item["mask_type_id"],
                    body_part=item["body_part"],
                    subregion=item["subregion"],
                    mask_role=item["mask_role"],
                    protected=join_list(item["protected_regions"]),
                )
            )
        add_line("")
        section_end = len(lines)
        line_map[group_key] = {
            "section": title,
            "line_start": section_start,
            "line_end": section_end,
        }

    return lines, line_map


def build_promotion_gates_md() -> list[str]:
    return [
        "# Wave70 Ultimate Mask Factory Promotion Gates",
        "",
        "These gates are mandatory for autonomous Mask Factory development. They are written for AI execution, not human convenience.",
        "",
        "## Non-Negotiable Done Definition",
        "",
        "A mask type is not complete until all of the following are true:",
        "",
        "1. The mask type has a stable mask_type_id in ULTIMATE_MASK_COVERAGE_MATRIX.csv.",
        "2. The mask request compiles into a contract JSON with owner_character_id, target_region, scale, protected_regions, allowed_routes, and evidence_paths.",
        "3. A mask artifact is generated as a PNG, alpha map, segmentation map, deformation map, temporal map, or audio-event map appropriate to the mask role.",
        "4. A preview overlay exists and shows target coverage plus protected-neighbor boundaries.",
        "5. Protected-neighbor checks pass. The edit cannot alter protected eyes, mouth, hands, identity anchors, clothing seams, jewelry, other characters, support objects, background, or body-region areas unless the target contract explicitly names them.",
        "6. Quality score is at least 85 and any domain-specific stricter threshold passes.",
        "7. Workflow patch/routing evidence proves the mask was attached to the intended ComfyUI node, input, pass, and output prefix.",
        "8. A generated output artifact exists. Mask-only proof is not final proof.",
        "9. Whole-artifact visual QA passes for images. Localized target-region review alone is insufficient.",
        "10. For video/GIF masks, frame-grid plus playback QA passes and temporal drift is checked across the full clip.",
        "11. For audio-linked masks, full-duration playback, AV sync, event timing, clipping/noise, and mix-balance checks pass.",
        "12. For soft-body/deformation masks, gravity, collision, rebound/ripple, anchor protection, and shape identity continuity pass.",
        "14. Target-runtime evidence exists before final certification. Local proof is useful but is not target-runtime certification.",
        "",
        "## Anti-Loop Rule",
        "",
        "Do not refresh Wave65, indexes, hydration, or generic validators just because Wave70 exists. Only rerun Wave65 if Plan source files are added or renamed after this Wave70 package, and only once for that changed source set.",
        "",
        "## Whole-Artifact Review Rule",
        "",
        "Every generated image, video, GIF, or audio artifact must be reviewed as a whole artifact. A task focused on feet cannot pass if hands are broken. A task focused on mouth timing cannot pass if face identity, eyes, hands, clothing ownership, background, or audio sync fails elsewhere in the artifact.",
        "",
        "## Cost-Control Rule",
        "",
        "Prefer local ComfyUI validation for mask contracts, previews, overlays, low-resolution image proof, and iterative QA. EC2 is allowed only for bounded target-runtime proof when AWS/Git/model/readiness/cost-control gates pass.",
    ]


def enrich_rows(taxonomy_rows: list[dict[str, object]], line_map: dict[str, dict[str, int | str]]) -> list[dict[str, object]]:
    md_size = PLAN_TAXONOMY_MD.stat().st_size
    enriched: list[dict[str, object]] = []
    for index, item in enumerate(taxonomy_rows, start=1):
        item = dict(item)
        group = str(item["region_group"])
        source = line_map[group]
        item_id = f"ITEM-W70-{index:04d}"
        tracker_id = f"TRK-W70-{index:04d}"
        source_key = f"W70:{group}:{item['mask_type_id']}"
        item["item_id"] = item_id
        item["tracker_id"] = tracker_id
        item["source_key"] = source_key
        item["source_file_relative"] = rel(PLAN_TAXONOMY_MD)
        item["citation_section"] = source["section"]
        item["citation_line_start"] = source["line_start"]
        item["citation_line_end"] = source["line_end"]
        item["source_file_size"] = md_size
        enriched.append(item)
    return enriched


def build_coverage_rows(enriched_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    coverage_rows: list[dict[str, object]] = []
    for item in enriched_rows:
        coverage_rows.append(
            {
                "mask_type_id": item["mask_type_id"],
                "tier": item["tier"],
                "region_group": item["region_group"],
                "body_part": item["body_part"],
                "subregion": item["subregion"],
                "mask_role": item["mask_role"],
                "owner_scope": item["owner_scope"],
                "scale": item["scale"],
                "edit_allowed": item["edit_allowed"],
                "protect_required": item["protect_required"],
                "body_regions": item["body_regions"],
                "required_for_images": item["required_for_images"],
                "required_for_video": item["required_for_video"],
                "required_for_audio_sync": item["required_for_audio_sync"],
                "soft_body_role": item["soft_body_role"],
                "deformation_type": item["deformation_type"],
                "gravity_sensitive": item["gravity_sensitive"],
                "collision_sensitive": item["collision_sensitive"],
                "multi_character_allowed": item["multi_character_allowed"],
                "temporal_required": item["temporal_required"],
                "allowed_workflow_routes": join_list(item["allowed_workflow_routes"]),
                "protected_regions": join_list(item["protected_regions"]),
                "required_evidence": join_list(item["required_evidence"]),
                "qa_gates": join_list(item["qa_gates"]),
                "promotion_rule": item["promotion_rule"],
                "status": item["status"],
                "item_id": item["item_id"],
                "tracker_id": item["tracker_id"],
                "source_key": item["source_key"],
                "source_file_relative": item["source_file_relative"],
                "citation_section": item["citation_section"],
                "citation_line_start": item["citation_line_start"],
                "citation_line_end": item["citation_line_end"],
            }
        )
    return coverage_rows


def item_acceptance(item: dict[str, object]) -> str:
    return (
        f"{item['mask_type_id']} is complete only after contract, owner assignment, generated mask/map, preview overlay, "
        "protected-neighbor proof, quality score >=85, workflow routing proof, generated output, whole-artifact visual QA, "
        "target-runtime evidence before final certification"
    )


def item_notes(item: dict[str, object]) -> str:
    notes = [
        f"Body part: {item['body_part']}",
        f"Subregion: {item['subregion']}",
        f"Protected: {join_list(item['protected_regions'])}",
    ]
    if item["body_regions"] == "true":
        notes.append("Body-region target: ordinary mask target under the same source-derived geometry gates.")
    if item["soft_body_role"] != "none" or item["deformation_type"] != "none":
        notes.append("Soft-body/deformation: require gravity/collision/anchor/continuity checks.")
    if item["required_for_audio_sync"] == "true":
        notes.append("Audio-linked: require full-duration AV/event alignment QA.")
    return " | ".join(notes)


def build_item_rows(enriched_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in enriched_rows:
        rows.append(
            {
                "Item_ID": item["item_id"],
                "Item_Wave": "70",
                "Item_Type": "ultimate_mask_factory_requirement",
                "Item_Title": f"Ultimate Mask Factory coverage for {item['mask_type_id']}",
                "Item_Category": "Mask Factory Coverage",
                "Item_Domain": item["region_group"],
                "Owner_Domain": "mask_factory",
                "Autonomous_Required": "TRUE",
                "Human_Input_Allowed": "FALSE",
                "Human_Work_Allowed": "FALSE",
                "Codex_Action": "Implement or block this mask type with source-cited evidence; do not mark complete from taxonomy coverage alone.",
                "Implementation_Target": item["mask_type_id"],
                "Deliverable_Type": "mask_contract_preview_overlay_routing_generated_output_strict_qa",
                "Acceptance_Criteria": item_acceptance(item),
                "QA_Gates_Required": join_list(item["qa_gates"]),
                "Visual_Review_Required": "TRUE",
                "Visual_Review_Method": "strict_whole_artifact_plus_target_region_overlay_review",
                "Test_Required": "TRUE",
                "Evidence_Required": join_list(item["required_evidence"]),
                "Runtime_Proof_Required": "TRUE",
                "EC2_Allowed": "FALSE",
                "Blocker_Policy": "If local proof cannot be produced, record a blocker with exact mask_type_id, missing dependency, and evidence path; do not spin on docs.",
                "Source_Plan_Root": str(PLAN),
                "Citation_File": PLAN_TAXONOMY_MD.name,
                "Citation_Full_Path": str(PLAN_TAXONOMY_MD),
                "Citation_Section": item["citation_section"],
                "Citation_Line_Start": item["citation_line_start"],
                "Citation_Line_End": item["citation_line_end"],
                "Citation_Excerpt": f"Wave70 section defines {item['mask_type_id']} with protected-neighbor and promotion requirements.",
                "Source_Package": "Wave70 Ultimate Mask Factory",
                "Source_Type": "Plan Source",
                "Source_File_Size": item["source_file_size"],
                "Priority": "P1" if item["body_regions"] == "false" else "P2",
                "Risk_Level": "High" if item["body_regions"] == "true" or item["soft_body_role"] != "none" or item["required_for_audio_sync"] == "true" else "Medium",
                "Status": "Required_Not_Complete",
                "Created_From": "generate_wave70_ultimate_mask_factory.py",
                "Notes": item_notes(item),
                "Source_Key": item["source_key"],
                "Source_File_Relative": item["source_file_relative"],
                "Coverage_Level": "direct_wave70_mask_factory_requirement",
                "Coverage_Audit_Status": "source_cited_required_not_complete",
                "Ultra_Source_Coverage_Record": f"{item['source_key']}#L{item['citation_line_start']}-L{item['citation_line_end']}",
            }
        )
    return rows


def build_tracker_rows(enriched_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in enriched_rows:
        evidence_path = f"Plan\\Instructions\\QA\\Evidence\\Mask_Factory\\Wave70\\{item['mask_type_id']}.json"
        rows.append(
            {
                "Tracker_ID": item["tracker_id"],
                "Wave": "70",
                "Phase": "Wave70 Ultimate Mask Factory",
                "Workstream": item["region_group"],
                "Priority": "P1" if item["body_regions"] == "false" else "P2",
                "Risk_Level": "High" if item["body_regions"] == "true" or item["soft_body_role"] != "none" or item["required_for_audio_sync"] == "true" else "Medium",
                "Owner_Role": "autonomous_codex_mask_factory_builder",
                "Environment": "local_first_target_runtime_before_final",
                "Status": "Required_Not_Complete",
                "Task_Name": f"Prove Mask Factory mask type {item['mask_type_id']}",
                "Detailed_Action": (
                    f"Create contract, mask/map, preview overlay, protected-neighbor checks, routing proof, generated output, "
                    f"and strict QA for {item['mask_type_id']}."
                ),
                "Completion_Criteria": item_acceptance(item),
                "Acceptance_Evidence": evidence_path,
                "Dependency_Prerequisite": "Wave70 taxonomy row exists; local ComfyUI/mask tooling available; body region rows require explicit geometry gate evidence.",
                "Validation_Method": join_list(item["qa_gates"]),
                "Output_Artifact": evidence_path,
                "Source_Path": item["source_file_relative"],
                "Related_Source_Paths": f"{rel(PLAN_COVERAGE_CSV)}; {rel(PLAN_PROMOTION_GATES_MD)}",
                "Package_Top_Level_Directory": "Plan",
                "Autonomous_Execution_Mode": "source_cited_local_first_strict_qa",
                "Human_Input_Allowed": "FALSE",
                "Human_Work_Allowed": "FALSE",
                "Codex_Desktop_Action": "Run local proof first; use EC2 only for bounded target-runtime certification when gates pass.",
                "QA_Strictness": "strict_whole_artifact_and_domain_specific",
                "Visual_Review_Required": "TRUE",
                "Visual_Review_Method": "whole_artifact_plus_target_region_overlay_review; do not pass localized edits with unrelated whole-frame defects",
                "Test_Required": "TRUE",
                "Runtime_Proof_Required": "TRUE",
                "EC2_Allowed": "FALSE",
                "Preview_Required": "TRUE",
                "Final_Render_Gate": "Blocked until generated-output proof and whole-artifact QA pass.",
                "Evidence_Path": evidence_path,
                "Citation_File": PLAN_TAXONOMY_MD.name,
                "Citation_Full_Path": str(PLAN_TAXONOMY_MD),
                "Citation_Section": item["citation_section"],
                "Citation_Line_Start": item["citation_line_start"],
                "Citation_Line_End": item["citation_line_end"],
                "Citation_Excerpt": f"Wave70 section defines {item['mask_type_id']} with protected-neighbor and promotion requirements.",
                "Source_Package": "Wave70 Ultimate Mask Factory",
                "Source_Type": "Plan Source",
                "Source_Item_ID": item["item_id"],
                "Blocker_Policy": "If proof cannot advance, write exact blocker and switch to the next source-cited local-first mask row instead of repeating hydration or validators.",
                "Rerun_Policy": "Rerun only when the mask contract, artifact, workflow route, prompt, model, runtime, or QA artifact changed.",
                "Status_Decision": "required_not_complete_until_evidence_passes",
                "Notes": item_notes(item),
                "Source_Key": item["source_key"],
                "Source_File_Relative": item["source_file_relative"],
                "Coverage_Level": "direct_wave70_mask_factory_tracker_requirement",
                "Coverage_Audit_Status": "source_cited_required_not_complete",
                "Ultra_Source_Coverage_Record": f"{item['source_key']}#L{item['citation_line_start']}-L{item['citation_line_end']}",
            }
        )
    return rows


def counts_by_key(rows: list[dict[str, object]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in rows:
        value = str(item[key])
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def update_manifest(path: Path, wave_row_count: int, csv_path: Path, report_path: Path) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    included = payload.get("included_waves", [])
    if 70 not in included:
        included.append(70)
        payload["included_waves"] = sorted(included)
        if isinstance(payload.get("row_count"), int):
            payload["row_count"] = payload["row_count"] + wave_row_count
    payload["current_ultimate_mask_factory_wave"] = "Wave70"
    payload["current_ultimate_mask_factory_csv"] = rel(csv_path)
    payload["current_ultimate_mask_factory_report"] = rel(report_path)
    payload["current_ultimate_mask_factory_row_count"] = wave_row_count
    payload["ultimate_mask_factory_rule"] = (
        "Wave70 rows are required_not_complete until contract, mask/map, overlay, protected-neighbor, routing, generated-output, "
        "whole-artifact QA, and target-runtime evidence pass."
    )
    write_json(path, payload)


def main() -> None:
    taxonomy_rows = build_taxonomy()

    md_lines, line_map = build_markdown(taxonomy_rows)
    write_text(PLAN_TAXONOMY_MD, md_lines)
    write_text(PLAN_PROMOTION_GATES_MD, build_promotion_gates_md())

    enriched_rows = enrich_rows(taxonomy_rows, line_map)
    coverage_rows = build_coverage_rows(enriched_rows)
    item_rows = build_item_rows(enriched_rows)
    tracker_rows = build_tracker_rows(enriched_rows)

    write_csv(PLAN_COVERAGE_CSV, COVERAGE_HEADER, coverage_rows)
    write_csv(ITEMS_MASTER_CSV, ITEMS_HEADER, item_rows)
    write_csv(ITEMS_WAVE_CSV, ITEMS_HEADER, item_rows)
    write_csv(TRACKER_MASTER_CSV, TRACKER_HEADER, tracker_rows)
    write_csv(TRACKER_WAVE_CSV, TRACKER_HEADER, tracker_rows)

    generated_at = datetime.now(timezone.utc).isoformat()
    taxonomy_payload = {
        "schema_version": "1.0",
        "wave": 70,
        "generated_at_utc": generated_at,
        "purpose": "Authoritative Mask Factory taxonomy for hyperrealistic image, video, and audio generation.",
        "current_evidence_boundary": "Existing W69 proof covers only one narrow local face-skin no-mouth micro mask; all Wave70 rows start required_not_complete.",
        "mask_type_count": len(enriched_rows),
        "groups": counts_by_key(enriched_rows, "region_group"),
        "tiers": counts_by_key(enriched_rows, "tier"),
        "body_region_count": sum(1 for item in enriched_rows if item["body_regions"] == "true"),
        "soft_body_or_deformation_count": sum(1 for item in enriched_rows if item["soft_body_role"] != "none" or item["deformation_type"] != "none"),
        "audio_linked_count": sum(1 for item in enriched_rows if item["required_for_audio_sync"] == "true"),
        "temporal_required_count": sum(1 for item in enriched_rows if item["temporal_required"] == "true" or item["required_for_video"] == "true"),
        "completion_rule": "No row is complete from taxonomy presence alone. Evidence must pass per row.",
        "taxonomy": enriched_rows,
    }
    write_json(PLAN_TAXONOMY_JSON, taxonomy_payload)

    requirements_payload = {
        "schema_version": "1.0",
        "wave": 70,
        "generated_at_utc": generated_at,
        "row_count": len(enriched_rows),
        "source_files": [rel(PLAN_TAXONOMY_MD), rel(PLAN_COVERAGE_CSV), rel(PLAN_PROMOTION_GATES_MD), rel(WAVE70_SCOPE_MD)],
        "global_qa_gates": GLOBAL_QA_GATES,
        "temporal_qa_gates": TEMPORAL_QA_GATES,
        "audio_qa_gates": AUDIO_QA_GATES,
        "soft_body_qa_gates": SOFT_BODY_QA_GATES,
        "anti_loop_rule": "Do not rerun generic coverage/hydration work unless source files or proof artifacts changed.",
    }
    write_json(ITEMS_REQUIREMENTS_JSON, requirements_payload)
    write_json(TRACKER_REQUIREMENTS_JSON, requirements_payload)

    report_payload = {
        "schema_version": "1.0",
        "wave": 70,
        "generated_at_utc": generated_at,
        "result": "pass_generated_required_not_complete_rows",
        "row_count": len(enriched_rows),
        "items_rows": len(item_rows),
        "tracker_rows": len(tracker_rows),
        "coverage_rows": len(coverage_rows),
        "groups": counts_by_key(enriched_rows, "region_group"),
        "tiers": counts_by_key(enriched_rows, "tier"),
        "body_region_count": taxonomy_payload["body_region_count"],
        "soft_body_or_deformation_count": taxonomy_payload["soft_body_or_deformation_count"],
        "audio_linked_count": taxonomy_payload["audio_linked_count"],
        "temporal_required_count": taxonomy_payload["temporal_required_count"],
        "required_files": {
            "plan_taxonomy_md": rel(PLAN_TAXONOMY_MD),
            "plan_taxonomy_json": rel(PLAN_TAXONOMY_JSON),
            "plan_coverage_csv": rel(PLAN_COVERAGE_CSV),
            "plan_promotion_gates_md": rel(PLAN_PROMOTION_GATES_MD),
            "wave70_scope_md": rel(WAVE70_SCOPE_MD),
            "items_master_csv": rel(ITEMS_MASTER_CSV),
            "items_wave_csv": rel(ITEMS_WAVE_CSV),
            "tracker_master_csv": rel(TRACKER_MASTER_CSV),
            "tracker_wave_csv": rel(TRACKER_WAVE_CSV),
        },
        "known_boundary": "Generated taxonomy/ledger coverage does not prove any mask row complete. It creates required work rows and strict evidence gates.",
    }
    write_json(ITEMS_REPORT_JSON, report_payload)
    write_json(TRACKER_REPORT_JSON, report_payload)

    update_manifest(ITEMS_ROOT / "Manifests" / "items_package_manifest.json", len(item_rows), ITEMS_MASTER_CSV, ITEMS_REPORT_JSON)
    update_manifest(TRACKER_ROOT / "Manifests" / "tracker_package_manifest.json", len(tracker_rows), TRACKER_MASTER_CSV, TRACKER_REPORT_JSON)

    print(json.dumps({"generated_wave": 70, "mask_type_count": len(enriched_rows), "items_rows": len(item_rows), "tracker_rows": len(tracker_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
