# Wave 25 Implementation Manual

## Build objective
Create a deterministic multi-character interaction layer that sits above the existing orchestrator, contact graph, deformation passes, and mask factory.

## Minimum implementation path
1. compile a multi-character interaction contract
2. validate instance ids and region ownership
3. build cross-character masks
4. validate occlusion and depth order
5. route to local refine/inpaint passes
6. score merge-prevention and preservation evidence
