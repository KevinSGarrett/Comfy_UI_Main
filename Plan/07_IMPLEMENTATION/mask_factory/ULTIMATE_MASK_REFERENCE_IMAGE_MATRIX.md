# Ultimate Mask Reference Image Matrix

Purpose: define the implementation-facing image-variation requirements for the Mask Factory. This complements `Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md`.

## Design Decision

The active MOD-17 portrait can be used as an anchor image for local smoke tests, but it is not a representative dataset. It does not prove masks across subject identity, face shape, skin tone, expression, mouth visibility, profile geometry, occlusion, body pose, clothing edges, hands, contact patches, video motion, or audio-event timing.

Mask Factory development must separate:

- `single_anchor_smoke`: one source image proves plumbing and a narrow local overlay.
- `reference_matrix_validation`: multiple source images prove that the mask strategy generalizes.
- `target_runtime_certification`: the final runtime environment proves the route outside local smoke testing.

## Required Manifest

Every generalized mask proof must produce a matrix manifest with:

- `mask_type_id`
- `matrix_version`
- `source_image_ids`
- `source_image_paths`
- `source_image_sha256`
- `slot_id`
- `subject_id`
- `angle`
- `expression_or_pose`
- `occlusion_notes`
- `target_visibility`
- `source_resolution`
- `target_crop_path`
- `target_crop_sha256`
- `overlay_path`
- `overlay_sha256`
- `generated_output_path` when runtime proof is run
- `generated_output_sha256` when runtime proof is run
- `semantic_mask_alignment_result`
- `protected_neighbor_result`
- `generated_output_safe_result`
- `reviewer_notes`

## Required Local Asset Policy

Do not silently reuse one source image for all masks unless the row is explicitly marked as `single_anchor_smoke`.

For face-detail masks, prepare or select a local reference matrix before claiming generalized readiness. The matrix may contain generated, licensed, or project-approved local images, but it must not be a near-duplicate set of the same face/crop. If generated images are used, the manifest must record prompts/seeds or source provenance well enough to identify duplicate subjects.

## Mask Generator Requirement

Mask generators should accept a source image path and write outputs under a source-image-specific directory. Hardcoded coordinates from one portrait are allowed only for short-lived smoke scripts and must not be promoted to a generalized generator.

Required generator behavior before generalized pass:

- Detect or consume landmark/segmentation geometry per source image.
- Scale boundaries relative to detected anatomy, not fixed absolute coordinates.
- Emit source crop and zoom overlay evidence for each matrix slot.
- Record target-not-visible and resolution-too-low blockers instead of drawing shortcut masks.
- Keep protected-neighbor exclusions explicit for each mask type.

## Promotion Boundary

A row can move from single-anchor smoke to matrix validation only after the generator/request strategy is source-adaptive. A row can move from matrix validation to certification-ready only after the required matrix slots pass and target-runtime evidence exists.
