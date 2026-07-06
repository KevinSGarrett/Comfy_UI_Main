# Wave 24 Multi-Character Instance Layout Architecture

## Objective
Create a deterministic ownership layer for scenes containing more than one visible character.

## Required instance fields
Each character instance must declare:

- character_instance_id
- character_identity_id
- person_instance_mask_id
- skeleton_id
- region_ownership_map_id
- frame_bbox
- depth_layer
- occlusion_role
- contact_graph_edges
- protected_identity_regions
- QA evidence references

## Why this sits above other waves
Without instance layout, later waves can edit the wrong person, merge bodies, confuse contact direction, or use one character's identity/mask on another. Wave 24 becomes the ownership gate for multi-character generation and repair.
