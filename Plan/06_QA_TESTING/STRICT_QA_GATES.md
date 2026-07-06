# Strict QA Gates

## Gate 1 — Source and graph validation

- JSON parses.
- Workflow links resolve.
- Required node classes exist in object_info.
- Required models exist.
- Required references/masks exist.
- Disabled/rejected assets are blocked.
- Workflow hash is recorded.

## Gate 2 — Base visual QA

- correct character count
- correct layout
- correct pose/camera
- acceptable anatomy
- identity and body silhouette match
- no merged characters
- no unusable hands/faces

## Gate 3 — Mask QA

- target mask covers intended region
- wrong character not included
- feathering/grow/blur correct
- preview saved
- mask hash recorded

## Gate 4 — Local edit QA

- target change exists
- change is localized
- no mask edge
- no identity drift
- no body/chopped composite
- no detail bleed

## Gate 5 — Contact QA

- contact point exists
- hands/fingers readable
- target body/object readable
- pressure/indentation visible when requested
- occlusion/shadow plausible
- no impossible penetration

## Gate 6 — Multi-character QA

- each character remains separate
- per-character references preserved
- no cross-character style/detail bleed
- interactions happen between correct entities
- occlusion/depth order is plausible

## Gate 7 — Temporal QA

- identity stable
- pose/motion stable
- no flicker
- no body drift
- no hand/contact drift
- no object drift
- repaired frames pass recheck

## Gate 8 — Audio/AV QA

- correct speaker/voice
- speech timing matches scene
- lip-sync/mouth target correct
- foley/SFX tied to visual action
- no clipping
- dialogue intelligible

## Gate 9 — Promotion

- all required gates pass
- all artifacts are hashed
- all manifests are written
- known limitations recorded
- final output promoted only by promotion gate
