# Wave 25 Interaction Orchestrator and Rerun Loop

## Default routing
1. validate instance layout
2. validate interaction contract
3. validate masks and region ownership
4. validate occlusion/depth order
5. patch local refine/inpaint workflow
6. score output evidence
7. promote, rerun, split into smaller passes, or block

## Rerun strategies
- split one complex interaction into smaller contact events
- reduce denoise
- isolate source and target masks
- repair occlusion before deformation
- reroute to Wave 24 if the instance layout is wrong
- reroute to Wave 23 if the deformation intent is wrong
