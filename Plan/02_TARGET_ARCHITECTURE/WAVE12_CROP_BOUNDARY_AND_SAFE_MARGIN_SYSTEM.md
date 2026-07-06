# Wave 12 Crop Boundary and Safe Margin System

Crop errors are one of the most common ways a technically good image becomes unusable. Wave 12 adds explicit crop boundary logic.

## Required crop checks

- Is the head fully inside frame when the shot is not a close-up?
- Are the hands visible when the action requires hands?
- Are the feet visible for full-body shots?
- Is the primary face cut by the edge?
- Is the subject touching the frame edge when safe margin is required?
- Is the crop intentional and declared by the camera plan?

## Safe margin model

Safe margins are stored as normalized ratios. A full-body shot receives a larger margin than a face close-up.

## Repair actions

When a crop check fails, the repair plan may choose:

- Wider shot rerun.
- Lower zoom.
- Outpaint/expand canvas.
- Pose map with more padding.
- Switch from full-body to 3/4-body only if the request allows it.
