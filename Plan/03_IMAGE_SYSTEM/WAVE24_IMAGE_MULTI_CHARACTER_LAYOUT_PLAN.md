# Wave 24 Image Multi-Character Layout Plan

## Build order
1. Resolve target character count.
2. Assign instance ids.
3. Bind identities and reference packs.
4. Bind frame placement and depth order.
5. Bind masks and skeleton maps.
6. Run base/refine pass.
7. Run per-instance QA before any regional repair.

## Primary rule
Never run a body, face, hand, skin, clothing, contact, or deformation repair pass on a multi-character image without target instance ownership.
