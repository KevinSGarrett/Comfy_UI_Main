# Workflow Module Decision

## Decision

Use a modular workflow architecture controlled by an external orchestrator.

## Why not one giant flow

One giant flow causes:
- unreadable routing
- accidental global LoRA effects
- slow troubleshooting
- hard-to-test branches
- disabled nodes mistaken for active nodes
- poor multi-character isolation
- poor pass sequencing
- impossible QA evidence tracking

## Recommended module families

1. Input/reference upload module
2. Character Bible builder
3. Scene graph builder
4. Engine router
5. Base image generator
6. Control-map factory
7. Mask factory
8. Full-image refine
9. Body-shape correction
10. Surface detail inpaint
11. Face detail
12. Hand detail
13. Contact/deformation
14. Multi-character layout
15. Multi-character interaction
16. Upscale/finalize
17. GIF/video keyframe generator
18. Video model router
19. Frame repair
20. Audio planner/generator
21. AV sync/mix
22. QA and promotion

## ComfyUI subgraph usage

Use ComfyUI subgraphs for stable reusable node clusters. Use separate API workflow JSON files for execution modules that the orchestrator calls directly.

## App Mode usage

Use App Mode as a high-level operator interface. Do not expose the full graph. Expose only stable controls:
- prompt / scene request
- character count
- references
- engine preset
- detail targets
- output type
- QA strictness
- run/finalize button

The external orchestrator remains the decision-making brain.
