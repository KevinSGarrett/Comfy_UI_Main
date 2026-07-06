# Wave 12 Delivery Report — Frame Composition Integrity

Wave 12 adds the frame-integrity layer required to prevent common hyper-realism failures: wrong character count, accidental extra bodies, cropped full-body shots, missing feet/hands, merged bodies, duplicated limbs, and ambiguous multi-character separation.

## Delivered capability

The pack now defines:

- Character count contracts.
- Body visibility profiles.
- Crop-boundary rules.
- Safe-margin rules.
- Multi-character separation and no-merged-body rules.
- Detector/skeleton/segmentation evidence fields.
- Runtime promotion lifecycle for image and video frame integrity.
- App Mode controls for operators to choose body visibility and crop rules cleanly.
- Local scripts for contract compilation, validation, scoring, and Main Flow inventory.

## Static validation result

Static validation can pass locally without ComfyUI or EC2. Runtime promotion still requires actual generated image/video evidence.

This is intentional: Wave 12 defines the integrity gate; it does not pretend that generated outputs have already passed visual frame QA before those outputs exist.
