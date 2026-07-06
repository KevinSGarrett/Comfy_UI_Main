# Wave 12 Video/GIF Frame Integrity Continuity Interface

Video needs frame-integrity checks across time, not just on one still image.

## Required video checks

- Keyframe character count.
- Sampled-frame character count.
- Persistent character IDs.
- No sudden crop changes unless camera movement says so.
- No body merging during motion/contact.
- No sudden disappearance of feet/hands in full-body shots.
- No identity swaps caused by skeleton crossing.

## Sampling strategy

The system should check:

- First frame.
- Last frame.
- Scene cuts.
- Motion peaks.
- Contact-heavy frames.
- Any frame where detector confidence drops.

## Promotion rule

A video cannot be promoted when a small number of sampled frames look good but critical motion frames show character merging, body disappearance, or broken crop boundaries.
