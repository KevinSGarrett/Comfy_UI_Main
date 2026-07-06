# Wave 13 — Mask Factory Build Instructions

## Build stages

### Stage A — Contract

Create the mask factory contract from structured scene data.

### Stage B — Detection/segmentation

Use the chosen detector/segmentation module to create initial masks.

### Stage C — Normalization

Rename masks according to the registry and assign owners.

### Stage D — QA

Validate coverage, edges, overlap, and ownership.

### Stage E — Routing

Route masks into inpaint/detail/control workflows.

### Stage F — Evidence

Store mask paths, checksums, dimensions, before/after crops, and score reports.

## Do not

- Do not route unassigned masks.
- Do not use a wrong character's mask for another character.
- Do not use nano masks for large edits.
- Do not promote masks without output evidence.
