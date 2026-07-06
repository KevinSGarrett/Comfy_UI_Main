# Wave 12 Current Status

Status: **Static architecture and validation harness added.**

Runtime status: **Evidence required later.**

The current Main Flow already has image-generation output lanes and staged reference/control branches. Wave 12 adds the downstream frame-integrity gate that reviews generated outputs from those lanes.

## What is now covered

- Correct character count.
- Full/half/1/3/1/4 body visibility definitions.
- Crop boundary enforcement.
- No merged bodies.
- No unassigned body fragments.
- No duplicated characters.
- Multi-character separation.
- Video keyframe/sample-frame extension.

## What remains runtime-proof-bound

- Actual detector output for generated images.
- Actual skeleton/pose maps for generated images.
- Actual segmentation masks for generated images.
- Video sampled-frame integrity reports.
- Promotion decisions from actual output evidence.
