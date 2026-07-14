# Image Review Checklist

- Artifact ID: OPENPOSE-V6-TARGET-RUNTIME-61596842-SEED711470303
- Output Path: Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260713T193658-0500/images/9_op_fullbody_walk_v6_robust_711470303_00001_.png
- Workflow / Prompt Reference: runtime_artifacts/run_packages/openpose_v6_target_runtime_61596842_20260713T192933-0500/lane_files/workflow.api.json; PromptProfiles/base_generation/controlnet_openpose_v1_robustness/openpose_v6_full_body_walking_robustness_seed711470303.json
- Model / LoRA Context: RealVisXL V5.0 + OpenPoseXL2 / seed 711470303

## Scores
- Face realism: pass_at_whole_image_scale
- Eye quality: pass_at_whole_image_scale
- Skin texture: pass
- Hands/fingers: pass_at_whole_image_scale_only
- Feet/toes: not_authority_scored_shoes_visible
- Hair realism: pass
- Teeth/mouth quality: not_applicable_no_teeth_emphasis
- Body proportions: pass_at_whole_image_scale
- Pose accuracy: pass
- Clothing/fabric: pass
- Contact points: not_authority_scored
- Object/body collisions: pass_none_observed
- Deformation realism: pass_no_major_deformation
- Soft-body cues: not_authority_scored
- Anatomy consistency: pass_at_whole_image_scale
- Lighting: pass
- Shadows: pass
- Reflections: pass_no_blocking_issue
- Background coherence: pass
- Camera/lens realism: pass
- Texture detail: pass
- Artifacting: pass_no_major_artifact
- Prompt compliance: pass_with_footwear_color_note

## Defects
- Black shoes with white soles were generated instead of fully white footwear.
- Detailed finger, foot, toe, contact, and mask geometry remain outside this bounded review.

## Decision
- Pass with footwear-color note for the exact bounded OpenPose target-runtime configuration. See `W64_OPENPOSE_V6_TARGET_RUNTIME_VISUAL_QA_61596842_20260713T200300-0500.json`.
