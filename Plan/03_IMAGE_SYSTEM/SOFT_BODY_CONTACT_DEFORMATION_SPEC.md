# Soft-Body Contact and Deformation Specification

## Purpose

Create believable contact, pressure, indentation, compression, pull/push, and collision visuals through controlled masked passes.

## Important boundary

ComfyUI image generation does not provide true physics simulation by itself. The system can create believable visual evidence using pose, depth, masks, contact-zone inpaint, and QA. For physically accurate animation, external reference video or 3D simulation remains superior.

## Contact lane inputs

- approved base/refined image
- source entity/body-part mask
- target entity/body-part mask
- contact-zone mask
- falloff mask
- pose/hand keypoints
- depth/normal map
- contact prompt
- negative prompt
- chosen engine/model/LoRA

## Contact pass order

```text
lock pose
lock depth/volume
detect source hand/object
detect target body/object area
build contact-zone mask
build falloff and shadow masks
run inpaint/detail pass
QA contact crop
rerun or reject
```

## Required visual evidence

- hand/finger/object is readable
- target body/object is readable
- contact point exists
- pressure/indentation/compression is visible when requested
- contact shadow/occlusion is plausible
- no merged fingers
- no impossible penetration
- no duplicate limbs
- no hard mask edge
