# Wave 16 — Refine QA Gates

Every refine pass must pass these gates before promotion.

## Gate 1 — Source evidence

- approved base image exists;
- base image hash recorded;
- base image QA already passed.

## Gate 2 — Engine compatibility

- source engine family known;
- target engine family known;
- target checkpoint allowed;
- LoRA/profile family compatible;
- forbidden cross-engine object use absent.

## Gate 3 — Denoise policy

- denoise in allowed band;
- high-denoise pass not mislabeled as refinement.

## Gate 4 — Mask contract

For regional passes:

- mask exists;
- owner is known;
- target region is known;
- feather/expand policy defined;
- unmasked regions protected.

## Gate 5 — Preservation QA

- identity preserved;
- pose preserved;
- frame/crop/body visibility preserved;
- environment preserved;
- character count preserved.

## Gate 6 — Artifact QA

- no harsh mask edge;
- no waxy texture;
- no new limbs/body fragments;
- no new background artifacts;
- no over-sharpening or halos.

## Gate 7 — Rerun/fallback record

If the pass is not first try, rerun reason and changed settings must be recorded.

## Gate 8 — Promotion decision

Promotion is allowed only when all required gates pass.
