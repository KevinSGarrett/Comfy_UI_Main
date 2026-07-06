# Wave 13 — Mask Bleed and Overlap QA

## Checks

- Person masks must not overlap unless explicitly marked as contact or occlusion.
- Body-part masks must stay inside the owning person mask.
- Fabric masks must not consume unrelated background or another character.
- Contact masks may overlap participants but must be labeled as contact masks.
- Nano cleanup masks must stay below configured area limits.

## Failure result

Any unlabeled cross-person bleed blocks promotion.
