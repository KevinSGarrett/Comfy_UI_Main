# Wave 15 — Base Image to Video Keyframe Handoff

Wave 15 is image-base focused, but every base image must be structured so it can become a video keyframe source later.

## Handoff requirements

- Base image evidence manifest
- Character identity bindings
- Environment/room binding
- Camera/framing plan
- Pose/blocking plan
- Control-map/mask availability
- Seed/model metadata
- QA status

## Video lane relationship

The base image lane does not prove WAN/Hunyuan/LTXV video runtime. It produces candidate keyframes and evidence that later video workflows can consume.

## Rule

```text
No video workflow should start from an unscored base image.
```
