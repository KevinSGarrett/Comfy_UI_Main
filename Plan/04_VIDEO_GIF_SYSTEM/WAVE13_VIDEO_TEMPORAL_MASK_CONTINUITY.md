# Wave 13 — Video Temporal Mask Continuity

## Video mask problem

A mask that works on one frame can flicker, drift, merge with another character, or lose contact consistency across frames.

## Video mask requirements

- stable person-instance IDs across frames,
- temporal smoothing of mask edges,
- continuity checks for face/hair/hand/body regions,
- contact masks that remain consistent during motion,
- frame-to-frame mask drift scoring,
- keyframe mask anchors.

## Promotion rule

Video output cannot promote if character-instance masks or contact masks drift beyond the configured tolerance.
