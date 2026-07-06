# Wave 11 DWPose/OpenPose Install and Proof Checklist

## Install

- Install ComfyUI Manager if not already installed.
- Install the ControlNet auxiliary/preprocessor custom nodes needed by the selected workflow.
- Restart ComfyUI.
- Capture `/object_info`.

## Validate

Check object_info for the configured node names in:

- `10_REGISTRIES/wave11_pose_preprocessor_registry.json`

## Proof

Create test outputs for:

- one DWPose map;
- one OpenPose map;
- one depth map;
- one normal map;
- one Canny map;
- one lineart map.

Each proof needs:

- source image path;
- map path;
- hash;
- dimensions;
- node name used;
- settings;
- QA status.

## Promotion

Do not mark the pose/control-map system promoted until proof output exists.
