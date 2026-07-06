# Wave 11 App Mode Control Map Controls

## Operator Controls

Expose only clean controls:

- Pose control enabled
- Pose source image
- Pose type: DWPose / OpenPose
- Pose strength
- Depth control enabled
- Depth source image
- Depth strength
- Edge control enabled
- Edge type: Canny / Lineart
- Edge strength
- Normal control enabled
- Per-character skeleton mode
- Multi-character blocking mode
- Runtime proof mode
- QA strictness

## Do Not Expose

- raw node IDs;
- random disconnected LoRA catalog nodes;
- model binary paths;
- internal S3 paths;
- experimental rejected/superseded assets;
- unsupported mixed-engine control routes.
