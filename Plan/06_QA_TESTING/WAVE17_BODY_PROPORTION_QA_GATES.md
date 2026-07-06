# Wave 17 — Body Proportion QA Gates

## Required gates
A body-corrected output must pass:

1. character identity preservation,
2. pose preservation,
3. character count integrity,
4. no merged bodies,
5. target region improvement,
6. body ratio plausibility,
7. left/right paired-region balance,
8. mask-edge blend,
9. skin texture continuity,
10. clothing/fabric continuity,
11. crop and frame preservation,
12. source-base preservation.

## Automatic fail flags
- face identity changed,
- pose or skeleton changed unexpectedly,
- character count changed,
- body merged with another body,
- extra limb/body fragment created,
- crop boundary cuts corrected region,
- protected region changed,
- full-image redraw used,
- same-engine compatibility violated,
- mask owner mismatch.

## QA output
The QA output must be a body_shape_evidence report with scores, fail flags, weighted score, decision, and artifact references.
