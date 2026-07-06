# Wave 07 Image Scene Plan and Pass Compiler

## Purpose

This document defines how the Scene Director should plan image-generation jobs before any ComfyUI workflow is run.

## Image planning sequence

1. Determine output type: single image or image series.
2. Determine subject count.
3. Determine camera/framing.
4. Determine environment/lighting/materials.
5. Determine character/body/wardrobe/identity requirements.
6. Determine interaction/contact requirements.
7. Determine whether base generation, refinement, inpaint, detail, ControlNet, IPAdapter, or upscale passes are required.
8. Determine models and engines.
9. Determine QA goals.
10. Compile ordered pass plan.

## Base image planning

A base image pass is required when:

- the user asks for a new image
- the camera/framing is wrong
- the pose is wrong
- the subject count is wrong
- the environment is wrong
- a body-shape change is too large for a safe regional pass

The Director should not attempt to fix major composition problems through microdetail passes.

## Regional pass planning

A regional pass is appropriate when:

- the base image is compositionally correct
- the correction is localized
- a usable mask can be made
- the engine supports masked/inpaint/detail behavior
- QA can compare before/after crops

Regional pass examples:

- skin texture detail
- fabric seam detail
- hands/face detail
- small body-shape correction
- contact/pressure mark correction
- object/furniture touch-up

## Detail intensity planning

The Director must separate detail intent from model selection.

Good detail controls:

- detail target region
- detail type
- intensity
- denoise range
- mask scale
- protect regions
- QA crop requirement

Bad detail controls:

- globally enable many LoRAs
- add every realism LoRA
- use high denoise on a small region without protection
- change base model family mid-pass without image bridge

## Hyperreal image pass order

Recommended order:

```text
1. scene graph and camera plan
2. base generation
3. file/camera/subject-count QA
4. identity/reference pass if needed
5. pose/body/silhouette correction if needed
6. regional contact/deformation if needed
7. skin/material/fabric microdetail
8. hand/face/hard-anatomy detail
9. upscale
10. final QA/promotion gate
```

## Full-body framing rule

If the plan requires full-body framing, the Director must set:

- shot type = full_body
- crop rule = head_to_feet_visible
- safe margin
- visible floor contact
- no foreground occlusion of feet/hands
- QA goal = qa_camera_framing

A failed full-body crop should usually rerun the base/camera plan, not attempt to inpaint missing feet.

## Multi-character rule

If more than one character exists:

- create one character instance per person
- assign depth order
- create person-instance masks
- define occlusion relationships
- define contact graph only after instance separation
- add character-count QA
- add no-merged-people QA

## Soft-body/contact image rule

Contact detail requires:

- source mask
- target mask
- contact-zone mask
- falloff
- shadow/occlusion plan
- deformation goal
- no-bleed QA
- before/after crop evidence

Text alone is not enough. The Scene Director must create the structural requirements for a regional pass.
