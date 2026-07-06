# Wave 16 — Base Preservation and Drift Prevention

The base image is the contract. Refinement is allowed only if it improves the target issue without breaking the contract.

## Preservation targets

The refine system must preserve:

- character count;
- character identity;
- body shape and pose unless intentionally edited;
- full/half/third/quarter body visibility contract;
- crop boundaries and camera angle;
- room/environment layout;
- lighting direction;
- outfit continuity;
- prop locations;
- reference identity;
- base composition.

## Drift classes

The system records drift classes before deciding whether to rerun, fallback, or stop.

| Drift class | Example failure | Normal action |
|---|---|---|
| Identity drift | face or body identity changed | fail and rerun lower denoise |
| Pose drift | hands/body/blocking changed | fail and tighten pose/control |
| Frame drift | crop/body visibility changed | fail and rerun with frame lock |
| Mask bleed | unrelated pixels changed | fail and tighten mask |
| Style drift | specialty pass changed realism style | fail or cleanup with SDXL |
| Engine mismatch | wrong LoRA/checkpoint family | block before execution |
| Over-denoise | pass acts like regenerate | block/reclassify |

## Diff evidence

Refine QA should compare:

- base image vs refined image;
- masked region vs unmasked region;
- pose/skeleton before vs after;
- character instance count before vs after;
- crop/body visibility before vs after;
- color/lighting continuity;
- artifact rate.

## Masked pass rule

A masked pass may change:

- the owned mask region;
- a small feather/blend edge;
- approved shadow/contact boundary.

A masked pass must not change:

- unrelated characters;
- background layout;
- identity outside the mask;
- camera/crop;
- unowned fabric/skin/props.

## Stop condition

If the same high-severity drift repeats twice, the system stops instead of endlessly rerunning. The failure is returned to the Scene Director and Orchestrator for a new plan.
