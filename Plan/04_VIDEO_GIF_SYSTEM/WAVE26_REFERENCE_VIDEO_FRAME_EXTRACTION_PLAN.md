# Wave 26 Reference Video Frame Extraction Plan

## Extraction outputs
- `reference_video_manifest.json`
- `frame_manifest.jsonl`
- sampled frame images
- keyframe candidate list
- extraction QA report

## Frame extraction profiles
- `all_frames_short_clip`: extract every frame for short clips.
- `sample_every_n`: sample at fixed intervals.
- `motion_peak_sampling`: sample around movement peaks.
- `contact_phase_sampling`: sample before, during, and after contact.
- `shot_boundary_sampling`: sample around detected cuts.

## QA checks
- file decodes
- duration is non-zero
- fps is known or estimated
- frame count is known or calculated
- frames are not blank
- dimensions are stable
- orientation is normalized
