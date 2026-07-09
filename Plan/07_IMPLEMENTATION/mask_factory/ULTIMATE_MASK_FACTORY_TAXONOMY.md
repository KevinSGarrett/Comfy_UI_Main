# Wave70 Ultimate Mask Factory Taxonomy

Purpose: define the source-cited mask taxonomy that the autonomous Comfy_UI_Main build must use before Mask Factory work can be considered complete for hyperrealistic image, video, and audio generation.

Current evidence boundary: the existing W69 evidence proves only one narrow local face-skin no-mouth micro mask. It does not certify broad body, clothing, interaction, temporal, audio-linked, body regions, or soft-body deformation coverage.

Global rule: every mask type is both an edit target and a protection contract. A localized mask cannot pass if whole-artifact visual, temporal, or audio QA finds unrelated full-frame or full-duration defects. A generated output that remains visually stable does not prove the mask is semantically aligned.

Promotion rule: no mask type is complete until it has source-cited contract, generated mask or map, preview overlay, semantic mask-alignment QA, protected-neighbor checks, quality score, workflow routing proof, generated-output proof, strict whole-artifact QA, reference-image matrix proof for generalized readiness, and target-runtime evidence before final certification.

Mask-alignment rule: the preview overlay must be anatomically honest for the named `mask_type_id`. If the overlay is too broad, shifted, shaped like a shortcut polygon, includes protected neighbors, or covers a different region than the label claims, the row must be `mask_alignment_needs_revision` or `mask_alignment_fail` even if low-denoise generated-output QA passes.

Strict overlay rule: face-detail masks must be reviewed zoomed against the source image before any local pass status. Generic ovals, V-shapes, triangles, broad identity polygons, and half-target masks are not acceptable for detailed anatomical labels. Full-region labels such as `mf70_nose` must cover the full visible target and must not overlap protected neighbors such as inner eye, philtrum, lips, mouth, broad cheeks, hairline, clothing, or background.

Protected-boundary registry rule: protected regions must be checked against canonical source-derived boundaries for the current source image/matrix slot, following `Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md`. Generated editable masks from prior rows are not canonical boundary sources unless explicitly promoted as `canonical_boundary_layer_pass`. If one mask is wrong, later masks must not inherit that wrong region; both are judged against the canonical boundary registry and protected-overlap matrix.

Reference-image matrix rule: the current MOD-17 portrait is a single anchor image only. It may prove local plumbing and a narrow source-specific overlay, but it cannot prove a universal mask. Generalized or certification-directed mask work must follow `Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md` and `Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_REFERENCE_IMAGE_MATRIX.md`, including multiple subjects, angles, expressions, visibility cases, occlusion cases, and sufficient resolution/zoom crops for small anatomy. Hardcoded coordinates from one portrait must not be promoted as a generalized mask generator.


Soft-body rule: soft-body, gravity, collision, morphing, jiggle, ripple, and rebound masks are deformation or protection maps. They must preserve skeletal anchors, face identity, hands, clothing seams, jewelry, other characters, support surfaces, and temporal continuity.

## Core Identity Face

Source key prefix: W70:core_identity_face

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_face_full_instance | face | full_face_identity_region | edit_or_protect_identity_region | hairline; neck; ears; background; clothing |
| mf70_face_identity_critical | face | identity_critical_triangle | edit_or_protect_identity_region | eyes; nose; mouth; jawline; hairline |
| mf70_expression_region | face | brows_eyes_cheeks_mouth_expression | edit_or_protect_identity_region | identity_anchor; hairline; teeth; background |
| mf70_forehead_skin | face | forehead_skin | edit_or_protect_identity_region | eyebrows; hairline; eyes; background |
| mf70_cheeks_skin | face | left_right_cheeks_skin | edit_or_protect_identity_region | eyes; nose; mouth; hairline; jawline |
| mf70_jawline_chin | face | jawline_chin_contour | edit_or_protect_identity_region | mouth; neck; hair; clothing |
| mf70_ears | face | left_right_ears | edit_or_protect_identity_region | hair; jawline; background; jewelry |
| mf70_skin_tone_continuity | skin | global_visible_skin_tone_continuity | edit_or_protect_identity_region | identity_anchor; clothing; background |

## Face Detail Subregions

Source key prefix: W70:face_detail_subregions

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_eyes_full | eyes | both_eyes_full_region | edit_or_protect_facial_detail | pupils; iris; eyelids; eyelashes; eyebrows; skin |
| mf70_left_eye | eyes | left_eye_full_region | edit_or_protect_facial_detail | pupil; iris; eyelids; eyelashes; skin |
| mf70_right_eye | eyes | right_eye_full_region | edit_or_protect_facial_detail | pupil; iris; eyelids; eyelashes; skin |
| mf70_pupils_iris_sclera | eyes | pupils_iris_sclera | edit_or_protect_facial_detail | eyelids; eyelashes; catchlights; skin |
| mf70_eyelids | eyes | upper_lower_eyelids | edit_or_protect_facial_detail | iris; sclera; eyelashes; skin |
| mf70_eyelashes | eyes | upper_lower_eyelashes | edit_or_protect_facial_detail | eyelids; iris; skin; background |
| mf70_under_eye | eyes | under_eye_skin | edit_or_protect_facial_detail | eyes; eyelids; cheeks; nose |
| mf70_eyebrows | brows | left_right_eyebrows | edit_or_protect_facial_detail | forehead; eyes; hairline; skin |
| mf70_nose | nose | full_nose_bridge_tip_nostrils | edit_or_protect_facial_detail | eyes; cheeks; mouth; skin |
| mf70_mouth_lips | mouth | outer_mouth_lips | edit_or_protect_facial_detail | teeth; tongue; chin; cheeks; skin |
| mf70_teeth | mouth | teeth | edit_or_protect_facial_detail | lips; tongue; inner_mouth; face_skin |
| mf70_tongue_inner_mouth | mouth | tongue_inner_mouth | edit_or_protect_facial_detail | teeth; lips; chin; face_skin |
| mf70_makeup_cosmetics | face | eyeliner_lipstick_blush_makeup | edit_or_protect_facial_detail | identity_anchor; eyes; lips; skin_tone |

## Hair, Scalp, Skin Marks

Source key prefix: W70:hair_scalp_skin_marks

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_hair_full | hair | full_hair_volume | edit_or_protect_identity_surface_detail | face; ears; neck; background; clothing |
| mf70_hairline_edges | hair | hairline_edges | edit_or_protect_identity_surface_detail | forehead; face_identity; background |
| mf70_hair_strands_flyaways | hair | strands_flyaways | edit_or_protect_identity_surface_detail | face; background; clothing |
| mf70_scalp | scalp | visible_scalp | edit_or_protect_identity_surface_detail | hair; forehead; background |
| mf70_facial_hair | facial_hair | beard_mustache_stubble | edit_or_protect_identity_surface_detail | mouth; jawline; cheeks; skin |
| mf70_tattoos_scars_freckles_moles | skin_marks | tattoos_scars_freckles_moles_birthmarks | edit_or_protect_identity_surface_detail | skin_tone; body_shape; clothing |
| mf70_tanlines_pressure_marks | skin_marks | tanlines_pressure_marks | edit_or_protect_identity_surface_detail | skin_tone; clothing_edges; contact_shadow |

## Skin Surface Zones And Limbs

Source key prefix: W70:skin_surface_zones_and_limbs

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_neck | neck | front_side_back_neck | edit_or_protect_anatomy_region | face; hair; clothing_collar; jewelry |
| mf70_shoulders | shoulders | left_right_shoulders | edit_or_protect_anatomy_region | neck; upper_arms; clothing; background |
| mf70_chest_upper_torso | torso | chest_upper_torso_skin | edit_or_protect_anatomy_region | neck; clothing; arms; background |
| mf70_abdomen_stomach | torso | abdomen_stomach_skin | edit_or_protect_anatomy_region | chest; waist; clothing; hands |
| mf70_belly_button_umbilicus | torso | belly_button_umbilicus | edit_or_protect_anatomy_region | abdomen; waist; clothing; hands |
| mf70_waist_hips | torso | waist_hips_contour | edit_or_protect_anatomy_region | abdomen; pelvis; clothing; thighs |
| mf70_back | torso | back_skin_and_shape | edit_or_protect_anatomy_region | neck; shoulders; hips; clothing |
| mf70_left_arm | arms | left_full_arm | edit_or_protect_anatomy_region | shoulder; elbow; wrist; clothing; background |
| mf70_right_arm | arms | right_full_arm | edit_or_protect_anatomy_region | shoulder; elbow; wrist; clothing; background |
| mf70_left_upper_arm | arms | left_upper_arm | edit_or_protect_anatomy_region | shoulder; elbow; clothing; background |
| mf70_right_upper_arm | arms | right_upper_arm | edit_or_protect_anatomy_region | shoulder; elbow; clothing; background |
| mf70_left_forearm | arms | left_forearm | edit_or_protect_anatomy_region | elbow; wrist; hand; clothing |
| mf70_right_forearm | arms | right_forearm | edit_or_protect_anatomy_region | elbow; wrist; hand; clothing |
| mf70_elbows | arms | left_right_elbows | edit_or_protect_anatomy_region | upper_arm; forearm; clothing |
| mf70_wrists | arms | left_right_wrists | edit_or_protect_anatomy_region | hands; forearms; watch_jewelry; clothing_cuff |
| mf70_hands_full | hands | both_hands_full | edit_or_protect_anatomy_region | fingers; wrists; held_objects; other_body_parts |
| mf70_left_hand | hands | left_hand_full | edit_or_protect_anatomy_region | fingers; wrist; held_objects; contact_patch |
| mf70_right_hand | hands | right_hand_full | edit_or_protect_anatomy_region | fingers; wrist; held_objects; contact_patch |
| mf70_fingers | hands | all_fingers | edit_or_protect_anatomy_region | knuckles; fingernails; palms; held_objects |
| mf70_fingertips_fingernails | hands | fingertips_fingernails | edit_or_protect_anatomy_region | fingers; held_objects; skin |
| mf70_palms_knuckles | hands | palms_knuckles | edit_or_protect_anatomy_region | fingers; wrist; held_objects |
| mf70_thighs | legs | left_right_thighs | edit_or_protect_anatomy_region | hips; knees; clothing; support_surface |
| mf70_knees | legs | left_right_knees | edit_or_protect_anatomy_region | thighs; calves; clothing |
| mf70_calves | legs | left_right_calves | edit_or_protect_anatomy_region | knees; ankles; clothing; background |
| mf70_ankles | feet | left_right_ankles | edit_or_protect_anatomy_region | calves; feet; socks_shoes |
| mf70_feet_full | feet | both_feet_full | edit_or_protect_anatomy_region | toes; ankles; floor; shoes_socks |
| mf70_toes_toenails | feet | toes_toenails | edit_or_protect_anatomy_region | feet; floor; shoes_socks |

## Clothing, Material, Accessories

Source key prefix: W70:clothing_material_accessories

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_clothing_full_item | clothing | full_clothing_item_instance | edit_or_protect_material_or_accessory | skin; body_shape; background; accessories |
| mf70_shirt_top | clothing | shirt_top_blouse_jacket | edit_or_protect_material_or_accessory | neck; arms; torso_skin; hair |
| mf70_pants_skirt_dress | clothing | pants_skirt_dress | edit_or_protect_material_or_accessory | waist; legs; support_surface; background |
| mf70_sleeves_collars_cuffs_hems | clothing_detail | sleeves_collars_cuffs_hems | edit_or_protect_material_or_accessory | skin; wrists; neck; fabric_body |
| mf70_straps_buttons_zippers | clothing_detail | straps_buttons_zippers | edit_or_protect_material_or_accessory | skin; fabric; jewelry |
| mf70_fabric_folds_seams | clothing_detail | fabric_folds_seams | edit_or_protect_material_or_accessory | skin; body_shape; lighting; contact_shadow |
| mf70_sheer_transparent_fabric | material | transparent_sheer_fabric | edit_or_protect_material_or_accessory | skin; clothing_edge; identity; background |
| mf70_wet_stretched_compressed_fabric | material | wet_stretched_compressed_fabric | edit_or_protect_material_or_accessory | skin; body_shape; fabric_folds; lighting |
| mf70_underwear_swimwear | clothing | underwear_swimwear | edit_or_protect_material_or_accessory | skin; body_shape; clothing_edges; background |
| mf70_shoes_socks_gloves | clothing | shoes_socks_gloves | edit_or_protect_material_or_accessory | feet; hands; floor; clothing |
| mf70_jewelry_piercings | accessories | jewelry_piercings | edit_or_protect_material_or_accessory | skin; hair; clothing; reflection |
| mf70_glasses | accessories | glasses | edit_or_protect_material_or_accessory | eyes; nose; ears; reflections |
| mf70_watches_belts_bags | accessories | watches_belts_bags | edit_or_protect_material_or_accessory | skin; clothing; hands; background |
| mf70_hats_hair_accessories | accessories | hats_hair_accessories | edit_or_protect_material_or_accessory | hair; forehead; background |

## Scene, Camera, Lighting, Support

Source key prefix: W70:scene_camera_lighting_support

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_support_surface_bed | support_surface | bed_mattress | edit_or_protect_scene_physics_region | body_contact; blanket; shadow; background |
| mf70_support_surface_chair_couch | support_surface | chair_couch | edit_or_protect_scene_physics_region | body_contact; clothing; shadow; background |
| mf70_support_surface_floor_wall_table | support_surface | floor_wall_table | edit_or_protect_scene_physics_region | feet; hands; objects; shadow |
| mf70_blanket_pillow_fabric_support | support_surface | blanket_pillow_fabric_support | edit_or_protect_scene_physics_region | body_contact; clothing; hair; shadow |
| mf70_held_objects_props | props | held_objects_props | edit_or_protect_scene_physics_region | hands; fingers; body; background |
| mf70_object_between_body | props | object_between_body_regions | edit_or_protect_scene_physics_region | body_a; body_b; contact_shadow; occlusion_boundary |
| mf70_background_objects | scene | background_objects | edit_or_protect_scene_physics_region | foreground_character; depth_layer; lighting |
| mf70_foreground_character_instance | scene | foreground_character_instance | edit_or_protect_scene_physics_region | background; support_surface; shadow |
| mf70_background_depth_layer | scene | background_depth_layer | edit_or_protect_scene_physics_region | foreground_character; reflection; lighting |
| mf70_crop_safety_head_hands_feet | camera | crop_safety_head_hands_feet | edit_or_protect_scene_physics_region | frame_edge; full_character; background |
| mf70_frame_edge_risk | camera | frame_edge_risk_regions | edit_or_protect_scene_physics_region | hands; feet; hair; props |
| mf70_mirror_reflection | scene | mirror_reflection | edit_or_protect_scene_physics_region | reflected_identity; lighting; background |
| mf70_shadow_only | lighting | shadow_only_regions | edit_or_protect_scene_physics_region | body; support_surface; background |
| mf70_contact_shadow_cast_shadow | lighting | contact_and_cast_shadows | edit_or_protect_scene_physics_region | skin; clothing; support_surface; props |
| mf70_lighting_correction | lighting | localized_lighting_correction | edit_or_protect_scene_physics_region | identity; skin_tone; clothing_color; background |
| mf70_reflection_highlight | lighting | reflections_highlights | edit_or_protect_scene_physics_region | eyes; jewelry; glasses; wet_fabric; skin |

## Contact, Occlusion, Multi-Character

Source key prefix: W70:contact_occlusion_multi_character

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_contact_patch_generic | contact | generic_contact_patch | contact_or_ownership_mask | both_sides_of_contact; shadow; background |
| mf70_pressure_compression_patch | contact | pressure_compression_patch | contact_or_ownership_mask | contact_owner_a; contact_owner_b; material_edge |
| mf70_occlusion_boundary | occlusion | occlusion_boundary | contact_or_ownership_mask | foreground_owner; background_owner; edge_detail |
| mf70_limb_over_limb | occlusion | limb_over_limb | contact_or_ownership_mask | limb_a; limb_b; contact_shadow; skin_tone |
| mf70_hand_grip | hands | hand_grip_on_object_or_body | contact_or_ownership_mask | fingers; object_or_body; wrist; contact_shadow |
| mf70_hand_on_body | interaction | hand_on_body_contact | contact_or_ownership_mask | hand_owner; body_owner; fingers; skin; shadow |
| mf70_hand_on_object | interaction | hand_on_object_contact | contact_or_ownership_mask | hand; object; fingers; shadow |
| mf70_multi_character_instance_a | multi_character | character_a_full_instance | contact_or_ownership_mask | character_b; background; shared_contact |
| mf70_multi_character_instance_b | multi_character | character_b_full_instance | contact_or_ownership_mask | character_a; background; shared_contact |
| mf70_multi_character_body_part_owner | multi_character | per_character_body_part_owner | contact_or_ownership_mask | other_character; clothing; contact_shadow |
| mf70_shared_contact_patch | multi_character | shared_contact_patch | contact_or_ownership_mask | character_a; character_b; occlusion_boundary |
| mf70_character_a_touching_b | multi_character | character_a_touching_character_b | contact_or_ownership_mask | character_a_hand; character_b_body; identity_anchors |
| mf70_character_a_occluding_b | multi_character | character_a_occluding_character_b | contact_or_ownership_mask | character_a; character_b; edge_boundary |
| mf70_character_separation_boundary | multi_character | character_separation_boundary | contact_or_ownership_mask | character_a; character_b; background |
| mf70_identity_protection_per_person | multi_character | identity_protection_per_person | contact_or_ownership_mask | other_person_identity; hair; clothing |
| mf70_clothing_accessory_ownership_per_person | multi_character | clothing_accessory_ownership_per_person | contact_or_ownership_mask | other_person; shared_contact; background |

## Soft Body, Deformation, Morphing

Source key prefix: W70:soft_body_deformation_morphing

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_abdomen_soft_body_weight | soft_body | abdomen_stomach_soft_body_weight_map | soft_body_deformation_or_protected_anchor | ribcage_anchor; waist; clothing; hands |
| mf70_thigh_soft_body_weight | soft_body | thigh_soft_body_weight_map | soft_body_deformation_or_protected_anchor | hips; knees; clothing; support_surface |
| mf70_upper_arm_soft_body_weight | soft_body | upper_arm_soft_body_weight_map | soft_body_deformation_or_protected_anchor | shoulder; elbow; clothing |
| mf70_cheek_face_soft_body_weight | soft_body | cheek_face_softness_weight_map | soft_body_deformation_or_protected_anchor | eyes; mouth; jawline; identity_anchor |
| mf70_face_morph_identity_guard | morph | face_shape_morph_identity_guard | soft_body_deformation_or_protected_anchor | eyes; mouth; nose; jawline; hairline |
| mf70_gravity_sag_field | deformation | pose_aware_gravity_sag_field | soft_body_deformation_or_protected_anchor | skeletal_anchor; support_contact; clothing |
| mf70_collision_compression_field | deformation | collision_compression_field | soft_body_deformation_or_protected_anchor | contact_owner_a; contact_owner_b; surface_edge |
| mf70_ripple_rebound_decay_field | deformation | ripple_rebound_decay_field | soft_body_deformation_or_protected_anchor | anchor_regions; contact_patch; clothing |
| mf70_soft_body_mesh_control_lattice | deformation | soft_body_mesh_control_lattice | soft_body_deformation_or_protected_anchor | skeletal_anchor; identity_anchor; hands; feet |
| mf70_multi_character_soft_body_contact_pair | deformation | multi_character_soft_body_contact_pair | soft_body_deformation_or_protected_anchor | character_a_anchor; character_b_anchor; identity_regions |
| mf70_protected_skeletal_joint_anchor | protected_anchor | skeletal_joint_anchor_regions | soft_body_deformation_or_protected_anchor | shoulders; elbows; wrists; hips; knees; ankles |
| mf70_protected_hands_fingers_anchor | protected_anchor | hands_fingers_anchor_regions | soft_body_deformation_or_protected_anchor | hands; fingers; fingernails; held_objects |
| mf70_protected_clothing_seam_anchor | protected_anchor | clothing_seam_anchor_regions | soft_body_deformation_or_protected_anchor | seams; buttons; zippers; fabric_folds |

## Video Temporal Masks

Source key prefix: W70:video_temporal_masks

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_per_frame_propagated_mask | video | per_frame_propagated_mask | temporal_tracking_or_repair_mask | source_mask; owner_instance; frame_edges |
| mf70_mask_drift_detection | video | mask_drift_detection_region | temporal_tracking_or_repair_mask | identity; body_part; background |
| mf70_occlusion_enter_exit | video | occlusion_enter_exit_frames | temporal_tracking_or_repair_mask | foreground; background; contact_patch |
| mf70_motion_blur_region | video | motion_blur_region | temporal_tracking_or_repair_mask | body_part; edge_detail; background |
| mf70_contact_persistence_frames | video | frame_to_frame_contact_persistence | temporal_tracking_or_repair_mask | contact_owner_a; contact_owner_b; shadow |
| mf70_visibility_state_body_part | video | body_part_visibility_state | temporal_tracking_or_repair_mask | owner_instance; occluder; background |
| mf70_continuity_clothing_hair_accessory_skinmarks | video | clothing_hair_accessory_skinmark_continuity | temporal_tracking_or_repair_mask | identity; body_shape; lighting |
| mf70_repair_span_bad_frames_only | video | bad_frame_repair_span_only | temporal_tracking_or_repair_mask | good_frames_before_after; identity; motion |

## Audio Linked Masks

Source key prefix: W70:audio_linked_masks

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_audio_footstep_contact | audio_event | footstep_contact_region | audio_visual_event_alignment_mask | foot; floor; shadow; timing_anchor |
| mf70_audio_hand_contact | audio_event | hand_contact_region | audio_visual_event_alignment_mask | hand; object_or_body; timing_anchor |
| mf70_audio_clothing_rustle | audio_event | clothing_rustle_region | audio_visual_event_alignment_mask | fabric; body_motion; contact_patch |
| mf70_audio_object_impact | audio_event | object_impact_region | audio_visual_event_alignment_mask | object; surface; hand; timing_anchor |
| mf70_audio_bed_chair_couch_compression | audio_event | support_surface_compression_region | audio_visual_event_alignment_mask | body; support_surface; fabric |
| mf70_audio_mouth_dialogue | audio_event | mouth_dialogue_region | audio_visual_event_alignment_mask | mouth; lips; teeth; face_identity |
| mf70_audio_breath_chest_motion | audio_event | breath_chest_motion_region | audio_visual_event_alignment_mask | chest; neck; clothing; face |
| mf70_audio_event_visual_alignment | audio_event | audio_event_to_visual_contact_alignment | audio_visual_event_alignment_mask | event_source; contact_patch; timeline |

## Body Region Anatomy

Source key prefix: W70:body_regions

Required completion: every row in this section needs a mask contract, owner assignment, preview overlay, protected-neighbor proof, routing proof, generated-output proof, and strict whole-artifact QA before it can move beyond required_not_complete.

| mask_type_id | body_part | subregion | role | protected_regions |
| --- | --- | --- | --- | --- |
| mf70_multi_character_anatomy_separation | body_regions | multi_character_body_regions_separation | body_region_mask | character_a; character_b; shared_contact; identity |
