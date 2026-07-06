# Wave 26 Reference Video to Timeline Extraction

## Goal
Convert a real reference video into timeline data that the orchestrator can use.

## Extracted timeline layers
- frame index / timestamp
- camera movement estimate
- per-character pose estimate
- per-character visibility estimate
- depth / occlusion order
- region masks
- contact state
- deformation state
- object / prop state
- surface-state continuity hints
- audio-event alignment hooks when audio exists

## Sampling modes
- exact_all_frames: use for short clips or QA proof
- fixed_interval: sample every N frames
- scene_cut_aware: sample around detected cuts or major motion changes
- motion_peak: sample at highest motion/interaction intensity
- contact_event: sample before/during/after physical interaction

## Output
A reference-video timeline contract that can be converted into:
- still keyframes
- GIF loop plans
- full video shot plans
- frame repair manifests
