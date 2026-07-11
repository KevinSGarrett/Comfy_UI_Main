# Image Review Checklist

- Artifact ID: selected_inpaint_target_runtime_20260710
- Output Path: Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260710T210240-0500/images/11_codex_sdxl_realvisxl_inpaint_detail_micro_nomouth_v4_00001_.png
- Workflow / Prompt Reference: Plan/07_IMPLEMENTATION/workflow_templates/base_generation/sdxl_realvisxl_inpaint_detail_lane/workflow.api.json; runtime_artifacts/g9_20260709T030509/r/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/prompt_request.json
- Model / LoRA Context: sdxl_realvisxl_inpaint_detail_lane / RealVisXL V5.0

## Scores
- Face realism: 9/10
- Eye quality: 9/10
- Skin texture: 9/10
- Hands/fingers: not visible
- Feet/toes: not visible
- Hair realism: 9/10
- Teeth/mouth quality: 9/10
- Body proportions: not visible
- Pose accuracy: 9/10
- Clothing/fabric: 9/10
- Contact points: not visible
- Object/body collisions: 9/10
- Deformation realism: 9/10
- Soft-body cues: not applicable
- Anatomy consistency: 9/10
- Lighting: 9/10
- Shadows: 9/10
- Reflections: not applicable
- Background coherence: 9/10
- Camera/lens realism: 9/10
- Texture detail: 9/10
- Artifacting: 9/10
- Prompt compliance: 9/10

## Defects
- None observed in the bounded target-runtime smoke.
- Runtime note: the log contains a database-lock warning from the helper process and an ONNX device-discovery warning; neither caused a prompt or image defect.

## Decision
- Pass target-runtime smoke with notes. This does not promote the input mask, certify the full route, or activate Wave71+.
