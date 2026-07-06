# Wave 06 Image Engine Routing Strategy

## Image generation routing priorities
The image system must route by pass purpose, not by whichever model filename seems interesting.

## Base image route
Preferred future route:

1. Flux2 dev local — if proven
2. Flux1 dev — existing fallback/candidate
3. SDXL/RealVisXL — if SDXL LoRA ecosystem is needed immediately
4. Z-Image — preview/proxy only unless QA proves otherwise

## Fast preview route
Use for cheap iteration:

1. Flux2 klein — planned
2. Z-Image — existing experimental
3. Flux1 schnell FP8 — existing smoke/proxy

Preview outputs are not final. They are direction/proxy artifacts.

## SDXL/RealVisXL route
Use when the pass needs:

- SDXL LoRA library support
- low-denoise img2img refine
- skin/fabric/cellulite/pores/blemish/detail passes
- inpaint/detail workflows
- ControlNet SDXL Canny/depth/pose branches
- IPAdapter SDXL identity/reference workflows

## Pony route
Use only when a Pony-compatible checkpoint/asset is selected intentionally and QA proves it helps. Pony should be a specialty bridge, not a hidden global base.

## Flux2 route
Flux2 becomes the planned next-generation image backbone, but with strict proof requirements. It should be tested on:

- one-character base realism
- multi-character layout
- identity/reference consistency
- camera/framing instructions
- environment consistency
- body-shape prompt adherence
- local edit/inpaint/reference editing
- image-to-SDXL bridge quality

## Inpaint/detail route
Routing should consider mask size:

| Mask size | Likely engine |
|---|---|
| Macro/full scene | Flux2 or SDXL base rerun |
| Major body shape | SDXL/RealVisXL or Flux2 edit |
| Minor region | SDXL/RealVisXL inpaint/detail |
| Micro texture | SDXL/RealVisXL detail |
| Nano/pixel repair | crop/detail/upscale/QA module |

## Router output
Every image route decision must produce:

```json
{
  "selected_engine": "...",
  "selected_checkpoint": "...",
  "reason": "...",
  "blocked_engines": ["..."],
  "required_assets": ["..."],
  "workflow_template": "...",
  "expected_output": "...",
  "qa_gates": ["..."]
}
```
