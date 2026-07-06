# Wave 11 Character Action Mask Control Plan

## Purpose

Character action must be controlled by pose maps and protected by masks.

## Mask Types

- full body character mask;
- face/head mask;
- left/right hand masks;
- clothing/outfit mask;
- prop mask;
- contact region mask;
- occlusion mask;
- background/room mask.

## Rules

- Do not apply a character pose map globally when it should affect only one character.
- Do not let a prop or room Canny map override hands/faces.
- Keep identity-reference influence separate from skeleton control.
- For contact actions, validate finger/hand/body alignment before detail pass.
