# Wave 17 — Audio / Visual Body Change Boundary

## Purpose
Body-shape correction is visual, but it may affect animation, motion, and scene continuity. Audio should not drive body-shape changes unless a video/action plan explicitly connects audio events to body motion.

## Rules
- Voice identity is not changed by body-shape correction.
- Audio event timing does not override body masks.
- If body correction changes a video keyframe, downstream audio/visual sync QA must ensure movement still matches the shot timing.
- Audio lanes do not promote a visually failed body-correction output.

## Boundary
Wave 17 body correction produces image evidence. Audio/video promotion remains a separate runtime proof step.
