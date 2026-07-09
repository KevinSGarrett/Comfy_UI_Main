# Mask Geometry Hard Gate Protocol

## Purpose

Wave70 mask QA must prove that geometry overlays are correct before they are used to judge mask alignment. A green allowed box, amber protected box, crop panel, or overlap matrix is not proof if the geometry itself is crude, shifted, conflicting, too broad, or drawn in the wrong coordinate space.

This protocol exists because current panels can make bad masks look valid when the mask sits inside a broad debug rectangle. That failure must block before semantic mask QA, generated-output QA, target-runtime proof, or certification.

## Non-Negotiable Rule

No mask can be accepted, candidate-passed, locally passed, complete, certification-ready, target-runtime-ready, generalized, or universal unless model-backed geometry authority and the geometry gate both pass for the exact `mask_type_id`, source image or matrix slot, crop, mask, and overlay panel.

Required geometry approval token:

```text
model_backed_geometry_authority_pass == true
W70_MODEL_BACKED_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE
whole_body_geometry_authority_pass == true
W70_WHOLE_BODY_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE
wave70_mask_geometry_gate_pass == true
W70_MASK_GEOMETRY_ROW_GATE_PASS_TRUE
```

Without these tokens for the exact row, geometry is untrusted and the row remains blocked, needs-revision, failed, or not-complete.

## Gate Order

The geometry gate runs before all other mask-specific gates:

1. Model-backed geometry authority gate from `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md`.
2. Whole-body geometry authority gate from `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` for body, hands, hair, body skin, clothing/contact, support, soft-body, video, audio-linked, and body region rows.
3. Coordinate geometry gate.
4. Semantic mask-alignment gate.
5. Protected-neighbor and protected-overlap gate.
6. Generated-output geometry gate.
7. Reference-image matrix/generalization gate.
8. Target-runtime/certification gate.

If gate 1 or 2 fails, later gates may still be recorded as observations, but they cannot promote the mask.

## Coordinate-Space Requirements

Every geometry proof must include:

- Full source image dimensions and hash.
- Crop rectangle in full-image coordinates.
- Mask dimensions and hash.
- Display/panel resize scale.
- Coordinate transform from full image to crop to panel.
- Allowed geometry in full-image coordinates.
- Protected geometry in full-image coordinates.
- The same allowed/protected geometry rendered on the source crop.
- A statement that the mask, crop, source, and overlay all use the same coordinate basis.

If any coordinate transform is missing, stale, or visually inconsistent, the geometry gate fails.

## Allowed And Protected Geometry Requirements

Allowed geometry must trace or tightly bound the named target. Protected geometry must trace or tightly bound protected neighbors. Both must be source-derived or manually reviewed for the current source image/matrix slot.

Pass only when:

- The source-derived target and protected geometry came from the model-backed geometry authority, or from a recorded exact blocker when the source is not usable.
- Green allowed geometry covers the actual named target and not a broad convenient band.
- Amber protected geometry corresponds to real protected anatomy/object boundaries.
- Green and amber regions do not conflict unless the overlap is explicitly allowed and documented.
- The panel is large enough to inspect without guessing.
- Geometry remains valid in the source crop, mask-only crop, source+mask crop, and boundary panel.
- Rectangle boxes are only used as debug aids unless they are proven to be valid source-derived bounding boxes for a coarse target.

Fail or block when:

- Green allowed and amber protected regions overlap in a confusing or contradictory way.
- A broad rectangle substitutes for eyes, eyelids, nose, cheeks, jaw, lips, hairline, hands, or other detailed anatomy.
- The geometry crosses protected eyes, eyelids, lashes, iris/sclera, brows, under-eye skin, nose, philtrum, lips, teeth, tongue, inner mouth, cheeks, jaw/chin, neck, hairline, hair, clothing, background, hands, or other protected neighbors outside the contract.
- The crop/full-image/panel coordinate mapping is unproven.
- The panel is too small, too cluttered, or too low-resolution to inspect.
- The only proof is that mask pixels are inside a green box.

## Debug Geometry Rule

Hardcoded rectangles, broad bounding boxes, and hand-tuned one-image coordinates are debug geometry. They can support diagnosis, but they cannot pass geometry QA by themselves.

Haar cascades, Canny edge maps, and rectangle-only overlays are also diagnostic assists. They cannot satisfy `model_backed_geometry_authority_pass`, `whole_body_geometry_authority_pass`, `source_derived_landmark_or_segmentation_pass`, `model_consensus_geometry_pass`, `visibility_occlusion_confidence_pass`, or `no_symmetry_guessing_pass`.

Use this blocker when geometry is only debug-level:

```text
Blocked_Wave70_Mask_Geometry_Gate_Not_Passed
```

Use this finding when the panel itself is unreliable:

```text
qa_failed_geometry_boundary_panel_unreliable
```

## Required Evidence Fields

Each promotable mask geometry evidence record must include or link:

```json
{
  "geometry_gate": {
    "result": "pass | needs_revision | fail | blocked",
    "wave70_mask_geometry_gate_pass": false,
    "approval_token": "",
    "source_dimensions": [0, 0],
    "mask_dimensions": [0, 0],
    "source_sha256": "",
    "mask_sha256": "",
    "crop_rect_full_image_xyxy": [0, 0, 0, 0],
    "panel_scale": 1.0,
    "coordinate_transform_manifest_pass": false,
    "allowed_geometry_source_derived_pass": false,
    "protected_geometry_source_derived_pass": false,
    "green_amber_conflict_pass": false,
    "debug_rectangle_only": true,
    "panel_readable_pass": false,
    "findings": []
  }
}
```

## Relationship To Existing Gates

This protocol is required by:

- `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md`
- `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md`
- `Plan/Instructions/QA/MASK_PROMOTION_HARD_GATE_PROTOCOL.md`
- `Plan/Instructions/QA/WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md`
- `Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md`
- `Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_FACTORY_PROMOTION_GATES.md`

Generated-output stability never overrides a failed geometry gate. A stable image can be output-safe while the mask remains geometry-failed and unpromotable.
