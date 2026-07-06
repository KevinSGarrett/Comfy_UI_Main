# Wave 16 — Low-Denoise Refine Policy

Low denoise is the main protection against corrupting the approved base image.

In this system, denoise is treated as a semantic risk dial:

```text
very low denoise = polish / preserve
medium denoise = local rewrite risk
high denoise = regeneration, not refinement
```

## Default denoise bands

| Refine type | Recommended | Warn above | Block above |
|---|---:|---:|---:|
| Global light polish | 0.08–0.18 | 0.20 | 0.28 |
| Cross-engine bridge | 0.10–0.25 | 0.28 | 0.35 |
| Regional inpaint/detail | 0.12–0.30 | 0.32 | 0.40 |
| Identity-sensitive face/hands | 0.06–0.18 | 0.20 | 0.28 |
| Fabric/contact edges | 0.12–0.28 | 0.30 | 0.36 |
| Pony specialty masked | 0.08–0.22 | 0.24 | 0.28 |
| SD1.5 tiny repair | 0.06–0.16 | 0.18 | 0.20 |

## Hard rule

Any pass above its block threshold must be reclassified as regeneration or reconstruction.

It cannot claim that it is preserving the original base image.

## Why global full-frame refinement is risky

Global full-frame refinement can improve lighting and texture, but it can also shift:

- face identity;
- body shape;
- hand pose;
- character count;
- crop boundary;
- camera angle;
- clothing/fabric details;
- environment layout;
- object placement.

That is why global refinement should remain very low denoise and should run before any regional high-detail pass.

## Current Main Flow anchors

The uploaded Main Flow contains two important low-denoise anchors:

- a regional SDXL inpaint/detail sampler at denoise 0.28;
- a cross-engine-to-SDXL refine sampler at denoise 0.22.

Wave 16 uses those as static templates, not as final proof. Runtime output evidence is still required.

## Rerun strategy

When a refine pass fails because it changed too much, the rerun should not simply try again with the same settings.

Rerun should normally do one or more of the following:

1. reduce denoise;
2. tighten mask boundaries;
3. reduce or remove specialty LoRA/profile influence;
4. switch back to same-family SDXL/RealVisXL refinement;
5. stop if identity, pose, or composition drift repeats.

## Promotion requirement

No refined output is promoted unless the evidence manifest shows:

- input image hash;
- output image hash;
- source engine;
- target engine;
- denoise value;
- mask contract if used;
- before/after drift report;
- QA score;
- rerun history.
