# Wave 17 — Engine Bridge Boundaries for Body Correction

## Purpose
Body correction can use Flux-family, Flux2-ready, SDXL/RealVisXL, Z-Image bridge, or Pony specialty passes only when the engine bridge rules are respected.

## Cross-engine body correction rule
Cross-engine correction must be image-based only:

```text
approved base image
→ save image artifact
→ load image into target engine refine/inpaint workflow
→ apply owned masks
→ low-denoise correction
→ save candidate
→ QA
```

Never pass latent/model objects directly across Flux, SDXL, Pony, SD1.5, Z-Image, or other engine families.

## Same-engine LoRA rule
A body-shape LoRA can only be selected when:
- the LoRA engine family matches the target pass engine,
- the LoRA is not rejected/superseded,
- the LoRA belongs to a pass-specific profile,
- it is used in a named pass, not globally enabled,
- the correction still passes QA.

## Recommended default
For body-shape correction, start with SDXL/RealVisXL inpaint/refine because the current Main Flow already has low-denoise SDXL anchors. Use Flux/Flux2 body passes only after their body-refine runtime templates are proven.
