# Wave 17 — Silhouette Locking and Edge Cleanup Plan

## Why edge cleanup is separate
Large body corrections can create seams, ripples, or mismatched edges. Edge cleanup should be a later, lower-denoise pass, not mixed into the main body-shape change.

## Edge cleanup targets
- outer silhouette,
- waist/hip transition,
- thigh/background edge,
- clothing boundary,
- skin/fabric transition.

## QA checks
- no visible mask seam,
- no warped background,
- no floating fabric,
- no broken limb boundary,
- no crop cutoff,
- no merged body edges.

## Promotion rule
If silhouette cleanup fixes one region but damages another, the candidate fails and the orchestrator must rerun from the previous approved stage.
