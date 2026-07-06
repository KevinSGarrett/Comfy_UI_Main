# Wave 26 GIF / Video Keyframe Planner Architecture

Wave 26 introduces a planning layer that sits between approved still-image states and runtime video/GIF generation.

## Core mission
Transform a static scene into a temporal plan containing:
- ordered keyframes
- pose state per keyframe
- depth state per keyframe
- mask state per keyframe
- camera/framing state per keyframe
- interaction/contact state per keyframe
- continuity expectations
- export target (GIF or video)

## Inputs
- Wave 07 structured scene plan
- Wave 08 identity registry
- Wave 09 environment/world plan
- Wave 10 camera/framing plan
- Wave 11 pose/control-map plan
- Wave 13 mask factory outputs
- Wave 22–25 interaction/contact/deformation plans
- approved still base or approved scene state

## Outputs
- keyframe plan
- timeline plan
- GIF loop plan and end-state closure rules
- video shot plan
- temporal QA checklist
