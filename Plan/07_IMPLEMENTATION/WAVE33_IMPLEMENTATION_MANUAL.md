# Wave 33 Implementation Manual

## Preview-first workflow
1. Compile proxy_preview_plan.
2. Compile animatic_plan when output is video/GIF/sequence.
3. Compile realism_budget.
4. Compile compute_budget.
5. Render only low-cost previews.
6. Run preview QA.
7. If preview fails, rerun preview or revise plan.
8. If preview passes, run final_render_preflight.
9. Only then unlock EC2/final rendering.

## Operational rule
EC2 stays off by default. The final render gate is the only path to expensive rendering.
