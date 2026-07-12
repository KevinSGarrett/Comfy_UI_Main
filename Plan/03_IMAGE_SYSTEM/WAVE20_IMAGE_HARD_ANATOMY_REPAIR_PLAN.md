# Wave 20 Image Hard-Anatomy Repair Plan

## Required inputs
- approved source image
- character id / identity lock
- region mask
- crop box
- crop context margin
- repair prompt and negative prompt
- target QA goals

## Required outputs
- before crop
- repaired crop
- composited full image
- local anatomy score report
- global preservation score report

## Required machine gates

- `anatomy_scorecard`
- `hands_feet_check`
- `face_teeth_eye_check`
- `hard_reject_on_deformation`

Every compiler output must contain these gates. Missing regional evidence compiles
to an explicit blocked disposition with hard rejection enabled and promotion
disabled. Whole-image plausibility does not certify zoomed fingers, toes, teeth,
eyes, joints, limbs, or contact anatomy.
