# Wave 16 — Flux, SDXL, Z-Image, and Pony Bridging Strategy

## Flux/Flux2 to SDXL

Use this when Flux/Flux2 creates the best base image but SDXL/RealVisXL has better detail/inpaint/LoRA coverage.

Pattern:

```text
Flux/Flux2 base image
→ save decoded image
→ SDXL img2img/inpaint template
→ low denoise
→ QA
```

## Z-Image to SDXL

Use this when Z-Image produces strong initial composition or concept structure.

Pattern:

```text
Z-Image decoded image
→ VAEEncode or image load into SDXL template
→ low-denoise SDXL refine
→ QA
```

The current Main Flow already contains a static Z-Image/Flux-family to SDXL refine structure with a low-denoise sampler.

## SDXL to Pony

Use this only for masked specialty passes.

Pattern:

```text
SDXL approved base
→ tight mask or crop
→ Pony specialty pass
→ strict drift QA
→ optional SDXL cleanup
```

## Pony to SDXL

Use this when Pony produced a useful specialty detail but the result needs realism cleanup.

Pattern:

```text
Pony specialty output
→ SDXL low-denoise cleanup
→ realism/style regression QA
```

## Flux/Flux2 as refiner

Hold by default. Allow only after a local workflow proves it can preserve input images through actual image-conditioning/reference-conditioning behavior.

## Fallback order

The fallback order is:

1. same-family SDXL low-denoise rerun;
2. tighter masked SDXL pass;
3. Pony masked specialty pass if specifically justified;
4. SDXL cleanup;
5. tiny SD1.5 repair as last resort;
6. stop and return to planner if high-severity drift repeats.
