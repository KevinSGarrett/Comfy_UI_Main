# Wave 22 AI PM Tasks

## Objective
Add a physical interaction contact graph so the system can reason about source/target contact, pressure, occlusion, duration, expected visual response, and expected audio force before any contact repair or deformation pass is promoted.

## Tasks
1. Convert user intent into contact graph edges.
2. Bind each edge to source and target ownership.
3. Attach masks from Wave 13 and soft-body/material profiles from Wave 21.
4. Route each edge to image, video, and audio handoff plans.
5. Require evidence for pressure, occlusion, shadow/contact, and deformation.
6. Reject passes that create floating, clipping, merged bodies, or impossible contact.
7. Record audio force metadata for later foley/audio synthesis.
