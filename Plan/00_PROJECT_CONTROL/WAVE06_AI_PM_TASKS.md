# Wave 06 AI Project Manager Tasks

## Wave
Wave 06 — Engine registry and router

## Goal
Route Flux, Flux2, SDXL/RealVisXL, Pony, SD1.5, Z-Image, video, and audio engines safely.

## New user requirement added in Wave 06
Flux2 must be included as a first-class planned engine family. The project manager must also cover which additional engines/checkpoints should be added, held for review, or avoided.

## Required AI project-manager actions
1. Treat `wave42_working_tracker...csv` and `Plans.zip` as ongoing mutable upstream sources, not frozen truth.
2. Keep the current Main Flow as a runtime-bound source/staging canvas, not the final engine architecture.
3. Add Flux2 to the engine registry as a planned first-class family with separate variants:
   - `flux2_dev_local`
   - `flux2_klein_preview`
   - optional API variants behind cost gates
4. Create strict compatibility rules:
   - no cross-family LoRA mixing
   - no direct latent/model bridge across engine families
   - image bridges only
   - runtime proof before promotion
5. Define route decisions by pass type:
   - base image
   - identity/reference
   - body shape
   - skin/fabric detail
   - contact/deformation
   - multi-character
   - video
   - audio/AV sync
6. Create recommendation status for engines/checkpoints:
   - ADD
   - KEEP
   - SPECIALTY ONLY
   - REVIEW
   - HOLD
   - BLOCK
7. Update QA so engine selection is testable and auditable before EC2 cost is incurred.

## Non-negotiable rule
A model being present in a folder, S3 bucket, Civitai metadata table, or disabled ComfyUI catalog node does not make it production-ready. It becomes routeable only after metadata, path, compatibility, object_info, model-loading, output-file, and QA proof are recorded.
