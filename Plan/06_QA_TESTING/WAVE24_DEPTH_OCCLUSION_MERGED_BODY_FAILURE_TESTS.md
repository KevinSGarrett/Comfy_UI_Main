# Wave 24 Depth, Occlusion, and Merged-Body Failure Tests

## Failure modes
- merged torso or limbs
- duplicate arms/hands assigned to wrong instance
- face identity swap
- foreground/background reversal
- occlusion mask missing
- contact boundary not owned by both source and target
- region mask covers two people

Each failure maps to a rerun action in the Wave 24 rerun policy.
