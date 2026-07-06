# Wave 33 EC2 Render Block Implementation

## Block conditions
- missing preview plan
- missing preview output
- missing preview QA
- preview QA below threshold
- missing realism budget
- missing compute budget
- budget exceeds allowed tier
- unresolved state diff
- no selected take/variant
- missing final output destination

## Allowed condition
Only `final_render_preflight.promotion_decision = unlock_final_render` may unlock final rendering.
