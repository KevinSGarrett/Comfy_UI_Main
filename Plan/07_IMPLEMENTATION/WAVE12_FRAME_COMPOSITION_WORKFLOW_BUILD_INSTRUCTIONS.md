# Wave 12 Frame Composition Workflow Build Instructions

## Build modules

Create one lightweight module per integrity function:

- Character count evidence collector.
- Body visibility evidence collector.
- Crop boundary checker.
- Merged body checker.
- Frame integrity scorer.
- Repair-plan emitter.

## ComfyUI integration model

The Main Flow should continue producing image outputs. Frame integrity QA can run as a downstream local script or as a separate ComfyUI utility workflow once detector nodes are available and proven.

## Recommended output folder pattern

```text
Implementation/manifests/frame_composition_evidence/<run_id>/<lane_prefix>.json
Implementation/manifests/frame_composition_scores/<run_id>/<lane_prefix>.json
Implementation/manifests/frame_composition_repairs/<run_id>/<lane_prefix>.json
```
