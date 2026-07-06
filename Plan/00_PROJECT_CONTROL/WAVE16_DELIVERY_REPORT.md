# Wave 16 Delivery Report

## Delivered

Wave 16 adds image refine and engine bridging on top of Wave 15.

## Main Flow inventory

- Nodes: 356
- Links: 91
- SaveImage lanes: 8
- KSampler nodes: 7
- Low-denoise KSampler anchors: 2
- Mask input slots: 2
- ControlNet nodes: 2
- IPAdapter nodes: 2
- Disabled LoRA catalog nodes: 274

## Key design decisions

- Cross-engine bridge must be image-based.
- SDXL/RealVisXL is the default refine target.
- Pony is masked specialty only.
- Flux/Flux2 refinement is held until local image-conditioning proof.
- SD1.5 is tiny repair only.
- Denoise above policy is not allowed to claim base preservation.

## Validation

See `11_RELEASES/WAVE16_VALIDATION_REPORT.json`.
