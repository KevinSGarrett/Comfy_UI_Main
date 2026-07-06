# Wave 21 Soft-Body Orchestrator and Rerun Loop

The orchestrator uses soft-body profiles to decide whether a pass should run, rerun, fallback, or stop.

## Default flow
1. read approved image and masks
2. read profile contract
3. check contact/support context
4. select pass profile
5. patch low-denoise refine workflow
6. run pass
7. score evidence
8. promote, rerun, fallback, or stop

## Rerun examples
- deformation too weak -> slightly raise denoise or profile intensity
- deformation too strong -> lower denoise and tighten mask
- compression misaligned -> return to Wave 19 contact repair
- identity/body drift -> stop and restore approved source
