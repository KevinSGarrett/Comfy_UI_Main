# ComfyUI Wiring Repair List

## Current active lanes to preserve as source templates

- SDXL/RealVisXL base lane
- Flux/Z-Image lane
- RealESRGAN upscale lane
- SDXL inpaint/detail lane
- Flux-to-SDXL light refine lane
- Flux Schnell smoke/reference lane
- SDXL IPAdapter face-reference lane
- SDXL ControlNet Canny lane

## Current branches to convert from notes to executable modules

1. True Flux image-reference conditioning.
2. Additional reference-slot routes beyond face reference.
3. DWPose/OpenPose/depth/normal/tile ControlNet lanes.
4. Mask Factory.
5. Pass Planner.
6. Multi-character instance workflow.
7. Video/GIF lanes.
8. Audio/AV sync lanes.
9. Visual-truth QA.

## Wiring priorities

### Priority 1

- Replace static LoadImage/LoadImageMask in inpaint lane with previous-pass output + generated mask input.
- Add mask preview outputs.
- Add output handoff path to next pass.

### Priority 2

- Create control-map preprocessing module.
- Feed actual control maps into ControlNet, not arbitrary RGB placeholders.
- Add pose/depth output saves.

### Priority 3

- Move LoRA library nodes out of active graph and into model registry.
- Activate LoRAs only through selected pass templates.

### Priority 4

- Add per-character reference and mask input slots.
- Add multi-character scene graph input binding.

### Priority 5

- Add QA sheet exporter and promotion gate.
