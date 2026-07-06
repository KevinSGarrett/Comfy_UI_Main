# Wave 05 — Main Flow to Module Extraction Instructions

## Source canvas

The current source workflow contains:

- 356 nodes
- 91 links
- 82 enabled/non-disabled nodes
- 274 disabled/catalog nodes
- 8 SaveImage terminal lanes
- 13 note boundaries

## Extraction principle

Each SaveImage terminal lane becomes a separate module candidate. Each note-only boundary becomes a future module requirement. Each disabled catalog LoRA node remains registry/catalog data and must not be copied into runtime templates unless selected through a compatibility-checked profile.

## Extracted lane candidates

| Source Save Prefix | Module |
|---|---|
| Main_Flow/SDXL_RealVisXL_LoRA | SDXL/RealVisXL base lane |
| Main_Flow/Flux_Family_ZImage | Z-Image base lane |
| Main_Flow/SDXL_RealVisXL_LoRA_Upscaled | Upscale/export lane |
| Main_Flow/SDXL_Inpaint_Detail | SDXL inpaint/detail lane |
| Main_Flow/Flux_to_SDXL_Refine | Image bridge / SDXL refine lane |
| Main_Flow/True_Flux_Schnell_Reference_Smoke | Flux smoke test lane |
| Main_Flow/IPAdapter_Face_Reference | IPAdapter reference lane |
| Main_Flow/ControlNet_Canny_Edge | ControlNet Canny lane |

## Note boundary conversions

| Note boundary | Target module |
|---|---|
| Reference/IPAdapter/ControlNet staging | Reference + control modules |
| Video/audio handoff boundary | Video/GIF + audio modules |
| True Flux image-reference boundary | Flux reference-conditioning validation module |
| Inpaint/upscale/QA/release promotion | Inpaint, upscale, QA, promotion modules |
| QA boundary | Evidence and promotion gate module |
| LoRA library note | Model registry + engine-compatible profile selector |

## Required extraction method

1. Select one SaveImage lane.
2. Compute upstream nodes.
3. Copy only required upstream nodes into a draft workflow template.
4. Replace hardcoded operator prompts with structured patch points.
5. Replace raw output prefix with a patch point.
6. Replace raw model/LoRA selection with profile-based resolver.
7. Validate schema.
8. Validate object_info.
9. Run a local runtime proof if possible.
10. Write evidence manifest.
11. Promote only the module, not the whole source canvas.

## Runtime proof requirement

A module is not proven just because its source lane exists. It is proven only when:

- its extracted template validates
- object_info confirms all node classes
- models resolve
- a runtime output exists
- a QA evidence record exists
- promotion gate passes
