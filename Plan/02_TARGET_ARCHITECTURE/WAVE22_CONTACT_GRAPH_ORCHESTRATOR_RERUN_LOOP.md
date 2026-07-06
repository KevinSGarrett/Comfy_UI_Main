# Wave 22 Contact Graph Orchestrator and Rerun Loop

## Orchestration loop
1. Load approved base/refine output.
2. Load contact graph contract.
3. Validate every edge.
4. Bind masks and soft-body profiles.
5. Patch the relevant inpaint/refine/control workflow.
6. Run pass.
7. Collect evidence.
8. Score edge-level and global preservation QA.
9. Promote, rerun, fallback, or block.

## Rerun reasons
- source region drift
- target region drift
- wrong occlusion
- no visible contact
- excessive deformation
- no support shadow
- floating contact
- clipping/merging
- audio force mismatch
