# Temporal QA and Keyframe System

## Required temporal QA

- identity consistency
- face consistency
- body silhouette consistency
- hand/finger consistency
- contact-zone consistency
- no frame-to-frame flicker
- no sudden body morph unless planned
- no character merge/split
- no object drift
- no background instability
- no camera jump unless planned
- no lip-sync target mismatch when audio exists

## Repair strategy

If a frame fails:
1. Identify failed region.
2. Use prior/next passing frames for reference.
3. Build a localized repair mask.
4. Run frame repair pass.
5. Reinsert repaired frame.
6. Re-run temporal QA.

## Output formats

- GIF: quick review, short loops, lower color fidelity.
- MP4/WebM: production video preview, smoother playback, better color/quality.
- PNG frame sequence: highest control and repairability.
