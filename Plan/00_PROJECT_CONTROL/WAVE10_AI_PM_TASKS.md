# Wave 10 AI Project Manager Tasks

## Objective

Implement the Camera, Lens, Zoom, Angle, Framing, and Depth layer as a reusable project contract.

## Required AI Behavior

1. Never treat camera wording as prompt-only.
2. Convert every camera request into a structured `camera_plan`.
3. Validate shot size, lens, angle, depth, subject slots, and crop policy before runtime.
4. For full-body requests, preserve head, hands, feet, outfit edges, and scale anchors.
5. For close-ups, preserve identity anchors and focus targets.
6. For multi-character shots, assign subject slots, screen positions, depth order, identity priority, and occlusion rules.
7. For video, separate still-camera framing from camera motion continuity.
8. For audio/AV, map camera distance and room perspective to audio perspective only after audio runtime lanes are proven.

## Non-Negotiable Gates

- Missing camera plan = blocked.
- Missing shot size = blocked.
- Multi-character without subject slots = blocked.
- Full body without crop/margin policy = blocked.
- Video camera motion without video runtime proof = blocked.
- Promotion without framing QA evidence = blocked.

## Outputs To Maintain

- camera plan JSON
- camera validation report
- framing/composition score
- workflow patch manifest
- visual QA evidence
- promotion decision
