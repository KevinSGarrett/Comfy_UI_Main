# Wave 11 AI Project Manager Tasks — Pose, Action, Blocking, Control Maps

## Goal

Build the control-map planning layer that turns Scene Director intent into runtime-ready pose/action/blocking instructions.

Wave 11 covers:

- DWPose / OpenPose skeleton planning.
- Depth maps for spatial ordering and camera distance.
- Normal maps for surface orientation and shape continuity.
- Canny maps for hard edges and silhouettes.
- Lineart maps for cleaner contour retention.
- Per-character skeleton and mask ownership.
- Multi-character blocking, occlusion, and depth separation.
- Local validation before EC2.
- Runtime proof gates before promotion.

## Current Main Flow Truth

The current Main Flow already contains a wired Canny ControlNet branch and a staged IPAdapter/reference branch. DWPose, OpenPose, depth, normal, and lineart are not yet runtime-proven in the current Main Flow; they are part of the target architecture and must be added as workflow modules/subgraphs with object_info evidence and generated control-map evidence.

## Required Implementation Order

1. Inventory current Main Flow control nodes.
2. Define control-map contracts.
3. Define per-character skeleton contracts.
4. Define control-map router rules by engine.
5. Add validation scripts.
6. Add examples and schemas.
7. Add App Mode control-map controls.
8. Block promotion until runtime evidence exists.

## Non-negotiable Rule

Do not mark DWPose/OpenPose/depth/normal/lineart as production-working until local ComfyUI object_info confirms nodes and a generated output/evidence manifest exists.
