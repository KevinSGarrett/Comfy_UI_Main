# Wave 11 Control Map Workflow Build Instructions

## Build Modules

Create separate modules/subgraphs for:

- DWPose/OpenPose extraction;
- depth extraction;
- normal extraction;
- Canny extraction;
- lineart extraction;
- ControlNet apply;
- per-character mask application;
- control-map QA output.

## Do Not Overload One Canvas

The Main Flow should not become a massive all-control-at-once graph. Use modular workflows/subgraphs:

- `modules/control/dwpose_extract.json`
- `modules/control/openpose_extract.json`
- `modules/control/depth_extract.json`
- `modules/control/normal_extract.json`
- `modules/control/canny_extract.json`
- `modules/control/lineart_extract.json`
- `modules/control/sdxl_controlnet_apply.json`
- `modules/control/flux_control_apply.json`
- `modules/control/video_pose_sequence_apply.json`

## Strength Strategy

Start soft. Increase only when QA proves the output needs stronger control.
