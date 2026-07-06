# Wave 08 — Multi-Character Identity Separation

## Problem

Multi-character scenes often fail through identity bleed: face swaps, hair merging, body-shape transfer, outfit mixing, hands assigned to the wrong person, or character-specific LoRAs affecting all subjects.

## Required Separation Objects

Every character instance must have:

- `scene_instance_id`
- `character_id`
- `character_version`
- `person_mask_id`
- `face_mask_id`
- `hair_mask_id`
- `body_mask_id`
- `outfit_mask_id`
- `depth_order`
- `pose_control_id`
- `reference_pack_id`
- `model_selection_plan_id`
- `qa_result_id`

## Pass-Level Rules

- Base generation may include all characters, but QA must confirm count and separation.
- Identity correction must be region-masked per character.
- Hair/outfit/body-detail passes must be region-masked per character.
- Contact/deformation passes must include source mask, target mask, and contact-zone mask.
- Global LoRA activation is allowed only for universal realism/style passes, not per-character identity traits.

## Failure Conditions

A multi-character output fails if:

- wrong number of characters
- two faces merge
- body silhouettes swap
- hair colors/styles swap
- outfit elements bleed between characters
- skin details transfer to the wrong person
- person masks overlap incorrectly
- hand/contact ownership is unclear
- character-specific LoRAs were applied globally without proof

## Corrective Actions

- rerun base with better layout/depth control
- split into per-character detail passes
- regenerate masks
- lower identity LoRA weight
- move character-specific traits to a masked inpaint pass
- use stronger pose/depth separation
- reject the output if character identity cannot be recovered
