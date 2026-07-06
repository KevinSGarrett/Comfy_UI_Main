# Video Generation Review Protocol

## Purpose

This protocol governs autonomous QA for generated or processed video artifacts.

## Required review areas

Codex must review:

- temporal consistency
- flicker
- identity drift
- face drift
- body drift
- object permanence
- limb motion
- pose continuity
- camera motion
- physics plausibility
- contact consistency
- body / cloth / hair motion
- frame-to-frame anatomy changes
- compression artifacts
- audio/video sync if audio exists
- loop seams if looped video
- prompt compliance across time

## Review method

1. Confirm video file integrity and playback.
2. Inspect start, middle, and end frames.
3. Inspect scene-change and action-heavy segments.
4. Inspect any frames around contact or rapid movement.
5. If looped, inspect the seam from final frame back to first frame.
6. If audio exists, verify sync and perceived coherence.
7. Record defects and severity.

## Sampling guidance

At minimum, review:

- first 10% of runtime
- middle 10% of runtime
- final 10% of runtime
- any segments with visible complexity or high motion

For high-risk outputs, increase sample density or review full playback.

## Scoring categories

- identity stability
- motion quality
- physical plausibility
- continuity and permanence
- rendering cleanliness
- prompt adherence
- audio/video coherence when applicable

Use 0–5 scoring per category.

## Blocking defects

- severe flicker
- character identity collapsing over time
- disappearing / reappearing major objects
- gross anatomy shifts between frames
- impossible motion that breaks intended realism
- severe lip-sync or timing mismatch when sync matters
- unusable compression or encoding corruption

## Output record

Each video artifact must receive:

- a QA record
- scorecard result
- defect log
- segment notes
- final pass/fail decision
