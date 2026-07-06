# Wave 12 No-Merged-Bodies Tests

The no-merged-bodies test suite is designed for the common multi-character failure where two bodies melt together, share limbs, or become one ambiguous skeleton.

## Required evidence

- Person instance IDs.
- Skeleton IDs.
- Face/body assignments.
- Segmentation masks when available.
- Occlusion plan.
- Body-fragment count.

## Pass criteria

- Every expected character has a valid body assignment.
- Skeletons do not merge into one body chain.
- No unassigned limbs or body islands appear.
- Contact boundaries are visually distinct or intentionally occluded.

## Failure criteria

- Shared torso.
- Shared face/body assignment.
- Extra limbs not assigned to any character.
- Two expected characters detected as one person instance.
- One expected character split into two people without reason.
