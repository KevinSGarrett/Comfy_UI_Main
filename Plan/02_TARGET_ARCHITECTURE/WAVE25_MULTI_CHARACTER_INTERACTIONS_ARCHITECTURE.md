# Wave 25 Multi-Character Interactions Architecture

Wave 25 coordinates interactions between multiple character instances, props, and environment objects.

## Core model
Every interaction is represented as an event containing:
- source character instance
- target character instance or object
- source body region
- target body/object region
- contact type
- choreography phase
- occlusion role
- depth order
- required masks
- expected visual effect
- QA requirements

## Relationship to earlier waves
- Wave 24 identifies each character and owns masks/skeletons/regions.
- Wave 22 defines physical contact edges.
- Wave 23 defines local deformation/indentation repair.
- Wave 25 governs multi-character choreography, overlap, occlusion, and merge prevention.
