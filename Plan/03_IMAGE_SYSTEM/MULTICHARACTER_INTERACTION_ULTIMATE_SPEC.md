# Ultimate Multi-Character Interaction System

## Problem this solves

Multi-character scenes fail when the model treats all bodies as one prompt soup. The system must represent every character as an instance with identity, pose, mask, depth order, camera visibility, and contact edges.

## Required per-character structure

```json
{
  "character_id": "character_A",
  "identity_refs": [],
  "body_refs": [],
  "outfit_refs": [],
  "voice_profile": null,
  "pose_skeleton": "path/to/pose_A.png",
  "person_mask": "path/to/person_A_mask.png",
  "depth_order": 1,
  "frame_requirement": "full_body|half_body|close_up|background"
}
```

## Multi-character generation order

1. Scene and frame layout preview.
2. Per-character pose skeletons.
3. Depth/order/occlusion plan.
4. Base generation with low global LoRA use.
5. Person-instance QA.
6. Per-character identity correction.
7. Interaction/contact passes.
8. Detail passes.
9. Final upscale and QA.

## Merge prevention

QA must fail if:

- requested number of people is not present,
- two characters share one torso/head/limb mass,
- hands or limbs cannot be assigned to a character,
- person masks overlap incorrectly,
- per-character identity refs bleed into the wrong person,
- a character-specific LoRA is applied globally without a validated regional mechanism.
