# Wave 16 — Image Refine Pass Implementation Plan

Wave 16 turns refinement into a controlled pass system.

## Pass categories

1. Base preservation check
2. Global low-denoise polish
3. Cross-engine low-denoise bridge
4. Regional inpaint/detail
5. Pony masked specialty pass
6. Flux/Flux2 future specialty pass
7. SD1.5 tiny repair
8. Upscale/export

## Runtime order

The default order is:

```text
base image QA
→ image bridge if needed
→ low-denoise SDXL global polish
→ regional masked detail
→ specialty masked pass if justified
→ SDXL cleanup if specialty pass drifted
→ upscale/export
→ final QA/promotion
```

## Required input artifacts

A refine pass requires:

- approved base image;
- base image hash;
- scene plan;
- character bible binding;
- environment/world binding;
- camera/framing contract;
- mask plan if local;
- engine route decision;
- denoise policy decision;
- QA gates.

## Required output artifacts

A refine pass outputs:

- refined image;
- patch manifest;
- engine bridge manifest;
- before/after drift report;
- mask ownership report if masked;
- QA score report;
- rerun record.

## Current Main Flow anchors

The current Main Flow provides useful static anchors:

- SDXL inpaint/detail lane;
- Flux-family/Z-Image to SDXL refine lane;
- upscale lane;
- IPAdapter and ControlNet staging.

Wave 16 does not blindly promote these lanes. It turns them into named contracts that must run with evidence.
