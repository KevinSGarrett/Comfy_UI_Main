# Wave 07 Video/GIF Scene Director Interface

## Purpose

The Scene Director must convert video/GIF requests into keyframe, timeline, motion, camera, mask, engine, and temporal QA plans.

## Video/GIF planning fields

Required:

- target duration
- aspect ratio
- output format
- frame count or FPS target
- keyframe count
- camera motion
- subject motion
- pose timeline
- depth/occlusion timeline
- masks over time
- engine route
- temporal QA goals
- frame repair rules

## Keyframe-first rule

For hyperreal video/GIF, the Director should plan keyframes before full video generation.

Recommended phases:

```text
1. neutral/start
2. pre-motion
3. peak action or peak contact
4. release/recovery
5. settle/final
```

This is especially important for motion, soft-body approximation, object contact, and multi-character scenes.

## Temporal mask rule

If the video includes regional motion or contact, the Director must plan masks across time.

Examples:

- person instance mask over frames
- hand/object/contact masks
- fabric/body contact masks
- face/identity protection masks
- background protect masks

## Video engine routing

The Director can propose video engines, but Wave06 router validates them.

Planned candidates:

- Wan2.2
- HunyuanVideo 1.5
- LTX-2
- Flux/SDXL/Flux2 keyframes as inputs

## Temporal QA goals

Required checks may include:

- identity stability
- body/limb continuity
- no flicker above threshold
- no sudden background jumps
- camera motion matches plan
- contact events match timeline
- frame repair evidence exists
- final export manifest exists

## Relationship to audio

If audio is included, the video plan must expose timing markers for the audio director:

- contact event timestamps
- movement rhythm
- room/environment context
- speaker positions
- camera distance
- impact/pressure intensity
