# Wave 27 Per-Frame Manifest System

Every temporal run must emit a per-frame manifest.

## Required frame fields
- frame_index
- time_seconds
- source_route
- engine_name
- shot_id
- keyframe_phase
- visible_characters
- identity_targets
- contact_state
- deformation_state
- camera_state
- QA scores
- repair_status

## Purpose
The manifest makes frame-level QA and repair deterministic and auditable.
