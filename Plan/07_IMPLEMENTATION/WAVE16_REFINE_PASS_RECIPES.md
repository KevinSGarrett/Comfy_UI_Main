# Wave 16 — Refine Pass Recipes

## Recipe 1 — Flux/Flux2 base to SDXL detail

```text
Input: approved Flux/Flux2 base image
Target: SDXL/RealVisXL
Denoise: 0.10–0.25
Use: light global polish or regional detail
QA: identity/pose/frame/environment preserved
```

## Recipe 2 — Z-Image base to SDXL refine

```text
Input: approved Z-Image output
Target: SDXL/RealVisXL
Denoise: 0.10–0.25
Use: realism consolidation and material detail
QA: base composition preserved
```

## Recipe 3 — SDXL same-family inpaint detail

```text
Input: approved SDXL/RealVisXL base
Target: SDXL/RealVisXL
Denoise: 0.12–0.30
Use: face, hands, skin/material, fabric, contact edges
QA: mask ownership and no bleed
```

## Recipe 4 — Pony masked specialty

```text
Input: approved SDXL or Pony-compatible base/crop
Target: Pony-SDXL specialty
Denoise: 0.08–0.22
Use: specialty concept only
QA: realism regression and identity drift
```

## Recipe 5 — SD1.5 tiny repair

```text
Input: approved image crop
Target: SD1.5
Denoise: 0.06–0.16
Use: tiny artifact cleanup only
QA: localized diff only
```

## Recipe 6 — Upscale after refinement

```text
Input: promoted refined image
Target: upscale model
Denoise: 0.00
Use: resolution/sharpness only
QA: no halos, no distortions
```
