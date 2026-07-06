# Wave 17 — Video Body Proportion Continuity Interface

## Purpose
Image body-correction profiles must be reusable by video workflows, but video requires temporal continuity.

## Video-specific requirements
- same character_id across frames,
- same body target profile across shot,
- temporal masks or keyframe masks,
- pose/skeleton continuity,
- frame-to-frame silhouette stability,
- no body shape popping,
- no clothing/fabric popping,
- no crop boundary drift.

## Recommended video bridge
1. Correct keyframes with Wave 17 image body-correction contracts.
2. Promote only passing keyframes.
3. Use promoted keyframes as video references.
4. Run temporal QA for body shape consistency.
5. Do not promote video if body proportions change randomly across frames.

## Boundary
Wave 17 defines the image-to-video contract. It does not claim video body correction is promoted until the video runtime lane produces frame evidence.
