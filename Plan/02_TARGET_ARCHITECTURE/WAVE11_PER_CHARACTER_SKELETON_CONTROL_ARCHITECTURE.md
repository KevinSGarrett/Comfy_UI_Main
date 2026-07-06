# Wave 11 Per-Character Skeleton Control Architecture

## Problem

Multi-character generation often fails because skeletons, limbs, hands, faces, and masks bleed between characters. A single global pose map is not enough for complex scenes.

## Solution

Every character gets:

- `character_id`
- `character_version`
- `skeleton_id`
- source pose/reference image
- generated pose map
- optional keypoint JSON
- regional mask
- blocking slot
- depth layer
- occlusion role
- required body regions
- QA requirements

## Skeleton Ownership Rules

1. One character cannot reuse another character's skeleton unless explicitly cloned.
2. If two characters interact, each needs separate skeleton ownership and mask ownership.
3. Hands must be checked against the correct body/contact region.
4. Occluded body parts must be marked as intentionally occluded, not missing.
5. Skeletons must match camera framing; full-body requests require visible full-body skeleton evidence.
6. Face/hand keypoints must be required only when they matter to the action.

## Output

The per-character skeleton contract feeds:

- Scene Director plan
- camera plan
- mask plan
- ControlNet route
- inpaint/detail pass
- video pose-sequence plan
- QA/promotion report
