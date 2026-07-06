# Wave 05 — Video/GIF Module Interface

## Purpose

Wave 05 does not implement final video generation. It defines the modular handoff between still-image modules and future video/GIF modules.

## Required interface from image system to video/GIF system

The image system must output:

- approved base image
- approved refined image
- character identity manifest
- camera/frame plan
- environment manifest
- pose/keyframe plan
- mask manifest
- contact/action graph when needed
- QA evidence
- seed/model/version metadata

## Video/GIF module input contract

```json
{
  "shot_id": "shot_001",
  "output_type": "gif_loop",
  "fps": 12,
  "duration_seconds": 3,
  "keyframes": [],
  "camera_frame_plan": {},
  "character_state_manifest": {},
  "mask_manifest": {},
  "approved_reference_image": "path/to/image.png"
}
```

## Module boundary

Still image modules must not directly claim temporal consistency. Video/GIF modules must run separate temporal QA:

- identity drift
- body/limb drift
- camera jump
- flicker
- contact-zone drift
- mask instability
- frame-level artifact checks

## Wave dependency

Full implementation is deferred to Waves 26–29.
