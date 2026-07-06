# Wave 23 Failure Modes and Rerun Actions

## Failure modes
- mask bleed
- cut/chop seam
- merged anatomy
- over-deformation
- under-deformation
- texture wipeout
- finger duplication
- shadow mismatch
- pose drift
- identity drift

## Default rerun actions
- reduce denoise,
- shrink or enlarge mask depending on failure scope,
- switch to a lower-risk refinement lane,
- split one large pass into two smaller passes,
- reject and reroute to upstream pose/layout/body-correction wave if the problem is not local.
