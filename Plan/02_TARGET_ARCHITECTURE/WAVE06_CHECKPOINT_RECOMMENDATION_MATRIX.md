# Wave 06 Engine and Checkpoint Recommendation Matrix

## Recommendation statuses
| Status | Meaning |
|---|---|
| ADD | Add to the planned system now and create proof tasks |
| KEEP | Keep because it already supports current architecture |
| SPECIALTY ONLY | Keep but route only for narrow use cases |
| REVIEW | Add to evaluation queue, not production |
| HOLD | Do not spend major effort unless a specific need appears |
| BLOCK | Do not route until metadata/proof requirements are met |

## Recommended adds
### Flux2
Add as a first-class planned engine family. Use Flux2 dev for quality/reference/editing tests and Flux2 klein for fast previews. It must not be considered proven until runtime proof exists.

### Wan2.2
Add as primary video candidate because it is an advanced open video generation family. It should be benchmarked on keyframe-to-motion, shot consistency, and frame repair.

### HunyuanVideo 1.5
Add as efficient video candidate because it is positioned as a lower-barrier video route. Test it against Wan2.2 for motion coherence, identity drift, and cost.

### LTX-2
Add as an audio-video review candidate because it can potentially unify video and synchronized audio. It should not replace separate audio lanes until AV QA proves it.

## Recommended keeps
### SDXL / RealVisXL
Keep as the core specialty/refine/detail/inpaint route. This is the most important family for your existing Civitai-driven LoRA organization.

### Flux1
Keep as a stable existing Flux-family route. Flux1 remains useful while Flux2 is being proven.

### Z-Image
Keep as an experimental/proxy lane because it already appears in the current flow. Do not promote it above Flux2/Flux1/SDXL unless comparative QA proves it.

## Specialty only
### Pony-SDXL
Keep for cases where a Pony-specific checkpoint or LoRA is uniquely useful. Do not use Pony as a blind replacement for SDXL/Flux hyperrealism.

### SD1.5
Keep only for legacy specialty assets. It should not be a primary modern hyperrealism engine.

## Review candidates
### Qwen-Image
Review for text rendering, complex instruction following, and precise image editing. Add only if ComfyUI support and local runtime proof are clean.

### Stable Diffusion 3.5 Large/Medium
Review as a comparison engine for complex prompts and typography. Keep it separate from SDXL because SD3.5 is a different model family.

### HunyuanImage 3.0 style candidates
Review only if the local/ComfyUI ecosystem becomes practical for your pipeline. Do not let it distract from Flux2/SDXL/video/audio waves unless it clearly solves a needed gap.

## Block by default
Block any model/checkpoint/LoRA that does not have:

- filename
- hash
- source
- Civitai model/version ID if from Civitai
- base model family
- engine family
- local/S3/EC2 path
- compatible workflow template
- runtime proof
- QA proof
- promotion status

This is especially important because the current system has hundreds of model assets and catalog nodes. A file existing in the library is not the same as being routeable.
