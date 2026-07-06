# Wave 17 — Body Correction Workflow Build Instructions

## Workflow template requirements
A body correction workflow must expose:
- input image,
- input mask,
- target prompt,
- negative prompt,
- denoise,
- steps,
- CFG,
- checkpoint/engine family,
- output prefix.

## Recommended first workflow
Start from the SDXL inpaint/detail branch because the Main Flow already has:
- `VAEEncodeForInpaint`,
- mask input,
- KSampler at denoise 0.28,
- SaveImage output prefix for SDXL inpaint/detail.

## Body correction output naming
Use an output prefix such as:

```text
Main_Flow/Body_Shape_Correction/<character_id>/<pass_id>
```

## Required artifacts
- input source image,
- mask PNG files,
- patched workflow JSON,
- ComfyUI prompt_id/history,
- output image,
- evidence JSON,
- QA score report.

## Do not do this
- Do not patch every body LoRA into the graph.
- Do not use body correction in the base lane.
- Do not use full-image denoise 1.0 for body correction.
- Do not let unverified video/audio lanes promote image-body correction results.
