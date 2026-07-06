# Wave 16 — Base Corruption Detection Tests

The system must detect when a refine pass has silently become a rebuild.

## Corruption tests

1. Character count comparison
2. Character bounding box comparison
3. Body visibility comparison
4. Pose/skeleton comparison
5. Face/identity comparison
6. Mask ownership diff
7. Background/environment diff
8. Color/lighting continuity
9. Texture/artifact inspection
10. Output semantic summary comparison

## Fail conditions

A refine pass fails if it:

- changes the number of characters;
- changes crop/body visibility without approval;
- changes identity;
- changes pose or blocking without approval;
- changes large unmasked areas;
- swaps clothing or environment unexpectedly;
- introduces new body fragments;
- over-sharpens or waxes details;
- violates denoise policy.

## Evidence format

Every corruption report must include:

- before image path/hash;
- after image path/hash;
- pass id;
- bridge id;
- denoise;
- masks used;
- detected changes;
- pass/fail decision.
