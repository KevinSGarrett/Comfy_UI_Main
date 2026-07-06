# Wave 16 — Image Refine and Engine Bridging Architecture

Wave 16 adds the image-refine and safe engine-bridge layer that sits after base image generation and before final upscaling, video handoff, audio/visual synchronization, or promotion.

The goal is not simply to run more models. The goal is to preserve the approved base image while allowing very controlled improvements.

```text
approved base image
→ base preservation manifest
→ optional image-based engine bridge
→ low-denoise refine pass
→ regional/masked detail pass
→ corruption/drift QA
→ rerun/fallback/stop decision
→ promoted image artifact
```

## Why this wave matters

Base generation and refinement have different jobs.

Base generation decides the broad subject, identity, pose, camera, framing, environment, and composition. Refinement should not re-decide those things unless the Scene Director explicitly requests a rebuild.

Wave 16 therefore treats refinement as a controlled operation with strict evidence:

- the input image must be hashed and frozen;
- the intended changed region must be known;
- the target engine family must be compatible;
- denoise must stay inside policy;
- output QA must compare the result against the original base image.

## Engine bridging rule

Cross-engine movement is image-based only.

Allowed bridge objects:

- decoded image files;
- masks;
- crops;
- control maps;
- reference-pack manifests;
- QA evidence manifests.

Forbidden bridge objects:

- direct latent tensors between unrelated engines;
- model objects;
- CLIP objects;
- VAE objects unless explicitly part of a proven target template;
- LoRA stacks from a different engine family.

This prevents the system from accidentally mixing Flux, Flux2, SDXL, Pony, SD1.5, and Z-Image components in ways that appear to run but corrupt the image.

## Primary supported bridge pattern

The preferred production bridge pattern is:

```text
Flux / Flux2 / Z-Image base
→ save decoded image
→ load image into SDXL/RealVisXL img2img or inpaint template
→ low denoise
→ QA for identity, pose, frame, and mask preservation
```

The current Main Flow already contains a static example of this concept in the Flux-family/Z-Image to SDXL refine lane. It is not promoted until runtime proof confirms that the source image is preserved and the target engine family is correctly loaded.

## Same-family refinement

Same-family SDXL/RealVisXL refinement is the safest general-purpose refinement path because the existing system has a large SDXL model/LoRA inventory and an inpaint/detail lane. Same-family refinement should still follow the same rules:

- keep denoise low;
- use masks for local details;
- record before/after evidence;
- fail if identity, pose, frame, or environment changes unexpectedly.

## Pony specialty refinement

Pony should be a specialty masked pass, not a normal global realism refiner.

Use Pony only when the Scene Director or model router identifies a specific specialty concept that SDXL/Flux cannot handle adequately. Pony refinement must be masked, low-denoise, and must pass realism-regression QA.

## Flux and Flux2 as refiners

Flux and Flux2 are first-class base-generation targets. For refinement, they remain gated until local image-to-image/reference-conditioning proof exists. This avoids marking an unproven Flux/Flux2 edit path as production-ready.

## SD1.5 legacy repair

SD1.5 is last-resort tiny artifact repair only. It should never be used as a full-frame refiner over a high-quality Flux, Flux2, Z-Image, or SDXL base.

## Wave 16 locked architecture

```text
Base image approval is the anchor.
Refine passes may improve local quality.
Refine passes may not silently replace identity, pose, camera, character count,
environment, framing, or base composition.
```
