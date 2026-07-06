# Wave 28 Micro-Motion and Secondary-Motion Architecture

Wave 28 adds a motion-detail layer above Wave 26 keyframe planning and Wave 27 temporal QA.

## Core mission
Make generated motion feel alive without creating drift.

## Motion classes
- primary action: the main body/scene motion
- micro-motion: small intentional changes like gaze, blink, grip, breath
- secondary motion: delayed/follow-through response like hair sway, fabric flutter, bounce/ripple/rebound
- stabilization motion: tiny camera or body-settle changes used to avoid frozen stillness

## Inputs
- Wave 26 keyframe timeline
- Wave 27 per-frame manifest
- Wave 21 soft-body profiles
- Wave 22 contact graph
- Wave 23 deformation passes
- Wave 24/25 multi-character ownership and interaction rules

## Outputs
- micro-motion manifest
- secondary-motion pass plan
- per-frame motion deltas
- QA scores
- repair or rerun decision
