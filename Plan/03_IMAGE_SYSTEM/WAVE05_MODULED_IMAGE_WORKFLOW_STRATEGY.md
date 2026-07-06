# Wave 05 — Modular Image Workflow Strategy

## Goal

Replace the giant image canvas with a modular image pipeline that can be run, tested, and repaired one module at a time.

## Recommended image module order

```text
01 scene request
02 camera/frame plan
03 engine selection
04 base generation
05 base QA
06 identity/reference correction if needed
07 pose/depth/camera correction if needed
08 mask factory
09 body/shape correction if needed
10 skin/material detail if needed
11 hard anatomy detail if needed
12 contact/deformation detail if needed
13 upscale
14 final crop/creative QA
15 promotion
```

## Why base generation must stay separate

The base module must solve:

- character count
- rough identity
- pose
- camera angle
- frame composition
- environment
- lighting
- broad body shape
- no obvious impossible anatomy

It must not try to solve every pore, finger, fabric fold, soft-body deformation, audio cue, and video motion at the same time.

## Why detail modules must be masked

Detail modules can easily damage identity, body shape, pose, and framing if run globally. They must use:

- person-instance masks
- body-part masks
- crop bounds
- low-denoise settings
- before/after QA
- mask bleed checks

## Current source-lane conversion

The current source workflow exposes these extractable lanes:

- SDXL/RealVisXL base lane
- Z-Image base lane
- SDXL inpaint detail lane
- Z-Image to SDXL refine lane
- upscale/export lane
- IPAdapter face reference lane
- ControlNet Canny lane
- Flux smoke test lane

Each lane becomes its own module contract. Later waves will replace note-only boundaries with real modules for pose/depth/OpenPose, video/GIF, audio, AV sync, and advanced contact/deformation.
