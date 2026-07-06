# Wave 04 — Module Extraction Plan

## Purpose

This plan tells the AI project manager how the current Main Flow should be split into future production modules.

## Required future module map

| Module | Extract from current flow | Future wave dependency | Purpose |
|---|---|---|---|
| `image_base_flux_or_sdxl` | current base-labeled lane and active stack | Wave 05/06/15 | Primary image generation. |
| `z_image_base` | Z-Image lane | Wave 05/15 | Fast or alternate base generation. |
| `image_bridge_refine` | bridge/refine lane | Wave 06/16 | Cross-engine low-denoise refine. |
| `image_upscale_polish` | RealESRGAN upscale lane | Wave 15/16/34 | Final resolution/polish stage. |
| `masked_inpaint_detail` | SDXL inpaint/detail lane | Wave 13/14/16/18/20 | Local masked body/skin/detail corrections. |
| `identity_reference_ipadapter` | IPAdapter staged lane | Wave 08/14/20/24 | Character identity and face reference control. |
| `controlnet_canny_edge` | ControlNet Canny lane | Wave 10/11/12 | Edge/camera/framing control. |
| `lora_catalog_registry` | disabled LoRA library region | Wave 02/03/06 | Registry-based model selection. |
| `qa_evidence_export` | IG-09 notes | Wave 03/14/34 | Evidence generation. |
| `promotion_gate` | IG-10 notes | Wave 03/14/34 | Block unsafe/unproven outputs. |

## Extraction rules

1. Each module must have one clear purpose.
2. Each module must be valid as a ComfyUI API workflow template.
3. Each module must declare required input artifacts.
4. Each module must declare required model assets.
5. Each module must declare required custom nodes.
6. Each module must declare output artifacts.
7. Each module must declare QA gates.
8. No module may contain the full disabled catalog library.
9. No module may rely on hidden manual file swaps.
10. Every fixed test image must become a runtime input parameter.

## Recommended final graph structure

The final system should not be one giant graph.

Use:

- **Small reusable workflow API templates** for the orchestrator.
- **Subgraphs** for repeated internal ComfyUI node groups.
- **App Mode** for simplified user/operator controls.
- **External pass planner** for autonomous first/second/third pass selection.
- **Registry files** for model metadata and compatibility.
- **QA manifests** for every promoted output.

## Why this matters

The current flow proves that several components can exist on a canvas together, but future production requires exact routing. Hyper-realism depends on pass isolation:

- base composition
- camera/framing
- pose
- identity
- body shape
- skin/detail
- hands/face
- contact/deformation
- upscale
- image-to-video/GIF
- audio/AV sync

Those should not all be one monolithic graph.
