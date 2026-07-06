# Wave 26 GIF Export Plan

## GIF-specific planning fields
- loop_type
- loop_frame_count_target
- frame_hold_strategy
- seam_management_strategy
- contact resolution strategy
- output dimensions
- palette/compression tolerance

## Export sequence
1. Build loop plan.
2. Generate keyframes.
3. Generate/interpolate in-between frames.
4. Run frame QA.
5. Repair failed frames.
6. Assemble loop.
7. Run seam QA.
8. Promote or rerun.
