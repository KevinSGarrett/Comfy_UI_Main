# Wave 04 — Active Runtime Lane Deconstruction

## Purpose

This document tells the AI project manager which parts of the current main flow are actually wired to terminal outputs and how those lanes should be treated during future extraction.

## Lane treatment rules

1. A lane is considered **wired** if it has a `SaveImage` terminal and all upstream links are internally valid.
2. A lane is considered **production-ready** only after runtime proof, model-load proof, prompt/input proof, creative QA, and promotion evidence pass.
3. Smoke lanes must not be promoted as production primary lanes.
4. Fixed-input lanes must be converted into parameterized modules.
5. Any lane name/model mismatch must be corrected before module extraction.

## Active lane groups

### 1. Base image lanes

These lanes produce initial images or support base image generation.

- Primary/current base-labeled lane.
- Z-Image family lane.
- Flux Schnell smoke/test lane.

Required action:

- Separate true production base lanes from smoke lanes.
- Verify engine compatibility.
- Replace hardcoded prompt blocks with scene-plan inputs.
- Expose width/height/batch/seed/sampler settings through the pass planner.

### 2. Refine and bridge lanes

The current flow includes a bridge/refine lane that uses an upstream generated image and re-encodes it for refinement.

Required action:

- Rename the lane based on actual upstream source.
- Make all engine bridges image-based, not model/latent-mixed.
- Log source image hash, target model family, denoise, prompt, negative prompt, and final image hash.

### 3. Inpaint/detail lane

The current inpaint/detail lane is wired but uses fixed image and mask inputs.

Required action:

- Replace fixed `LoadImage` and `LoadImageMask` with pass planner inputs.
- Feed previous pass output into inpaint.
- Feed Mask Factory output into inpaint.
- Require mask preview, mask overlay, feather/grow/blur policy, and before/after crop QA.

### 4. Identity/reference lane

The current IPAdapter lane is a standalone staged identity smoke lane.

Required action:

- Convert into per-character identity module.
- Require `character_id`, face reference image, optional body/outfit reference, person/face mask, and identity QA.
- For multiple characters, never use a single global reference pass without masks/regions.

### 5. ControlNet/camera/edge lane

The current ControlNet lane is wired with a static control image.

Required action:

- Convert into a generated control-map module.
- Add Canny/depth/normal/DWPose/OpenPose preprocessing in future waves.
- Save control map artifacts and link them to the final output manifest.

### 6. Upscale lane

The current upscale lane is wired from the base image output.

Required action:

- Convert to final polish/upscale module.
- Require source image hash, upscaler model hash/path, dimensions before/after, visual artifact QA, and crop QA.

## Machine-readable lane inventory

See:

- `10_REGISTRIES/main_flow_wave04_runtime_lanes.json`
- `10_REGISTRIES/main_flow_wave04_runtime_lanes.csv`
