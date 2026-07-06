# Wave 26 Reference Video QA Gates

## Required gates
1. Source video decodes.
2. Source metadata is recorded.
3. Frame extraction or sampling succeeds.
4. Frame manifest is complete.
5. Pose/depth/mask/contact timeline outputs are synchronized.
6. Keyframe candidates map to reference timestamps.
7. Identity continuity is protected from the source-to-target transfer.
8. Flicker, frame corruption, and frame-jump issues are detected.
9. Frame repair plan exists for failed segments.

## Hard fails
- unable to decode source video
- extracted frames are blank or corrupt
- inconsistent orientation not resolved
- timeline states not aligned to frame indices
- source contains cuts but is treated as a single continuous shot
- generated target drifts from reference timing without declared reason
