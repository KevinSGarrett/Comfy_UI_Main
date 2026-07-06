# Wave 24 Video Multi-Instance Temporal Continuity

Each character instance must retain the same id across frames.

## Required temporal evidence
- per-frame instance id map
- per-frame mask ownership
- skeleton continuity
- depth order continuity
- contact graph event continuity

A frame fails if a character swaps identity, skeleton, depth order, or mask ownership without a declared scene event.
