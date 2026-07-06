# Wave 26 Reference Video Input Pipeline

## Pipeline
1. Receive reference video file.
2. Create source_video_manifest.
3. Decode metadata.
4. Normalize orientation and fps assumptions.
5. Extract frames or sampled frames.
6. Run frame QA.
7. Generate pose/depth/mask/contact timelines.
8. Convert timeline to GIF or video shot plan.

## Source handling modes
- full_reference_video: real video controls the full target sequence
- reference_segment: only a time range from the video is used
- motion_reference_only: video controls motion but not identity or appearance
- pose_reference_only: video controls pose/skeleton timing
- contact_reference_only: video controls contact and occlusion phases
- loop_reference: source clip is intended to become a GIF loop
