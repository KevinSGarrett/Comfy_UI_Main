# Image Review Checklist

- Artifact ID: codex_realvisxl_local_bounded_smoke_helper_00002
- Output Path: Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_local_bounded_smoke_v1_20260706T210854-0500/images/codex_realvisxl_local_bounded_smoke_00002_.png
- Workflow / Prompt Reference: runtime_artifacts/run_packages/realvisxl_local_bounded_smoke_v1/RUN_PACKAGE_MANIFEST.json; runtime_artifacts/run_packages/realvisxl_local_bounded_smoke_v1/prompt_request.json
- Model / LoRA Context: sdxl_realvisxl_base_lane / local helper RealVisXL V5.0 smoke / realvisxlV50_v50Bakedvae.safetensors

## Scores
- Face realism: 9
- Eye quality: 8
- Skin texture: 9
- Hands/fingers: not_visible
- Feet/toes: not_visible
- Hair realism: 8
- Teeth/mouth quality: 8
- Body proportions: 8
- Pose accuracy: 9
- Clothing/fabric: 8
- Contact points: not_visible
- Object/body collisions: 9
- Deformation realism: 8
- Soft-body cues: 8
- Anatomy consistency: 8
- Lighting: 9
- Shadows: 8
- Reflections: not_applicable
- Background coherence: 9
- Camera/lens realism: 9
- Texture detail: 8
- Artifacting: 8
- Prompt compliance: 9

## Defects
- No blocker-level visual defects found.
- Minor limitation: local helper smoke is intentionally 512x512 and 10 steps; fine hair edges and the shadowed eye are slightly soft.

## Decision
- Pass with notes for reusable local run-package helper smoke. Not promoted as EC2 target proof or final portfolio quality.
