# Wave 17 — Stomach, Waist, Hips, and Thighs Correction Plan

## Stomach correction
Use abdomen_stomach + outer_silhouette masks. Protect face, hands, background, and clothing areas that should not move. Keep denoise low enough to avoid identity/pose drift.

## Waist correction
Use paired waist_left and waist_right masks. Always compare left/right balance after correction. Do not overpinch the waist or break clothing/fabric edges.

## Hip correction
Use hips_pelvis and outer_silhouette masks. Preserve pelvis/knee alignment and frame/crop boundaries.

## Thigh correction
Use thigh_left and thigh_right masks as a pair. Preserve stance, feet, knees, and fabric continuity.

## Combined correction
For larger changes, split passes:
1. coarse silhouette/shape correction,
2. clothing/fabric blend,
3. skin texture restore,
4. edge cleanup,
5. QA.

Do not try to fix every region with one prompt and one giant unprotected mask.
