# Wave 24 Depth Order and Frame Placement System

## Placement fields
- normalized frame box: x, y, width, height
- visible body coverage class
- crop safety margins
- primary/secondary/background role
- intended gaze/camera relationship

## Depth fields
- depth_layer index
- in_front_of list
- behind list
- occlusion boundary masks
- contact/support relationship when applicable

## Rule
Depth order must match masks, contact graph edges, and visual occlusion. A character cannot be both in front of and behind the same target without an explicit split-region occlusion plan.
