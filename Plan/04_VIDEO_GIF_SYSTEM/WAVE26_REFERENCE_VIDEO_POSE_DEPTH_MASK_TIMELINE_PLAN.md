# Wave 26 Reference Video Pose / Depth / Mask Timeline Plan

## Timeline layers
A reference video can produce multiple timelines:

- pose timeline: per-frame skeleton or body layout
- depth timeline: per-frame front/back/occlusion state
- mask timeline: per-frame editable/protected/contact regions
- contact timeline: per-frame source/target interaction state
- camera timeline: estimated framing/crop/camera shift
- surface-state timeline: continuity of skin/fabric/wetness/lighting states

## Required sync
All timelines must map to the same timestamp/frame index base.

## Failure handling
If pose extraction succeeds but mask extraction fails, the video is only allowed to drive pose. If mask extraction succeeds but identity QA fails, the video can still serve as motion reference but cannot promote identity-sensitive output without additional reference locks.
