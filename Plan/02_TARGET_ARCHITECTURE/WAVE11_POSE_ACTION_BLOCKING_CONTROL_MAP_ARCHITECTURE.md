# Wave 11 Architecture — Pose, Action, Blocking, Control Maps

## Purpose

Wave 11 converts action and pose from loose prompt text into structured control-map plans.

The system now separates:

1. **Intent** — what the user wants the subject(s) to be doing.
2. **Blocking** — where each character/object is in the scene.
3. **Skeleton** — per-character body/action keypoints.
4. **Depth** — foreground/background ordering and camera distance.
5. **Surface/edge maps** — normal, Canny, and lineart maps.
6. **Masks** — per-character and per-object ownership.
7. **Runtime route** — engine-compatible ControlNet/IPAdapter/workflow module path.
8. **QA evidence** — generated map files and final output proof.

## Control Map Stack

Recommended order:

1. Character/environment/camera plan.
2. Per-character skeleton plan.
3. Pose map generation.
4. Depth map generation.
5. Optional Canny or lineart map for prop/room/outfit contours.
6. Optional normal map for surface orientation.
7. Mask validation.
8. Workflow module compile.
9. ComfyUI runtime execution.
10. Evidence collection and promotion gate.

## Current Main Flow Boundary

The current Main Flow contains a wired Canny ControlNet branch and staged reference/IPAdapter behavior. It does not yet contain a proven DWPose/OpenPose/depth/normal/lineart module. Wave 11 therefore treats those as required target modules, not as already-working production features.

## Design Rule

Control maps should control structure; LoRAs should not be used as substitutes for skeletons, depth, masks, or runtime proof.
