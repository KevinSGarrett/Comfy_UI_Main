# Wave 18 Skin/Material Realism QA Gates

## Mandatory pass gates
1. Region ownership confirmed.
2. Compatible engine family confirmed.
3. Denoise within profile limits.
4. Before/after evidence generated.
5. Identity, pose, body, crop, and seam continuity preserved.
6. Surface target visibly improved.

## Acceptance checks
- pores look like pores, not random noise
- blemishes are plausible and not plastic or painted-on
- cellulite follows body curvature
- sweat/oil specular highlights obey scene lighting
- pressure marks align with contact geometry
- fabric state remains consistent with environment and contact

## Machine-readable decision
The evidence record must contain `surface_texture_check`, `lighting_consistency`,
`material_state_continuity`, and `visual_score_threshold`. Promotion requires all three
qualitative gates to be inspectable passes, a bounded visual score at or above threshold,
passing macro and full-frame reviews, and a linked visual-QA record with
`certification_allowed: true`. Missing, blocked, not-applicable, or uninspectable required
evidence fails closed.
