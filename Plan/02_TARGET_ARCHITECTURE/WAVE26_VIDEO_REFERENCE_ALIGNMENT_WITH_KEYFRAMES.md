# Wave 26 Video Reference Alignment with Keyframes

A reference video can drive a generated shot without forcing one-to-one copying.

## Alignment modes
- frame_to_frame: target output follows source frame count closely
- keyframe_only: source video provides anchor frames only
- motion_phase: source video provides phase labels such as setup, approach, contact, hold, release
- pose_only: source video provides pose/skeleton timing
- depth_mask_only: source video provides occlusion/mask order
- camera_only: source video provides camera movement intent

## Required mapping
Every generated keyframe should map to one of:
- source frame id
- source timestamp
- source motion phase
- interpolated position between source frames

## Safety boundary
Reference video alignment must not override identity ownership, character count, body-region ownership, mask ownership, or QA promotion gates.
