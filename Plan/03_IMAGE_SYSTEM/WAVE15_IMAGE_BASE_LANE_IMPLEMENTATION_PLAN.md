# Wave 15 — Image Base Lane Implementation Plan

## Implementation stages

1. Build clean API-format templates for each base lane.
2. Validate each template against `/object_info`.
3. Register model/checkpoint/LoRA family compatibility.
4. Patch prompts, seeds, sampler settings, latent size, and SaveImage prefix.
5. Submit dry-run-first ComfyUI execution.
6. Collect `/history` and output files.
7. Score output evidence.
8. Fallback or promote as a base candidate.

## Current Main Flow lanes used as source

The current Main Flow provides these source lanes:

- SDXL/RealVisXL base
- Z-Image base
- SDXL/RealVisXL upscale
- SDXL inpaint/detail
- Flux-to-SDXL refine
- Flux Schnell smoke
- IPAdapter reference lane
- ControlNet Canny lane

Wave 15 uses these as source evidence for what exists in the current canvas, not as automatic proof that they are production-ready.

## Minimum base output evidence

Every base output must include:

- File path
- SHA256
- Byte size
- Image dimensions
- Format
- Lane ID
- Prompt version
- Scene plan ID
- Model/checkpoint IDs
- LoRA stack ID
- QA report ID
