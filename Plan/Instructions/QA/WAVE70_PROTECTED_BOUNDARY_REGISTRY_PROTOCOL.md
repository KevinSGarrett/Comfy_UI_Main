# Wave70 Protected Boundary Registry Protocol

## Purpose

Wave70 masks must not protect or exclude regions by trusting another generated mask that may itself be wrong. Protected boundaries must come from a canonical source-derived boundary registry for the specific source image and matrix slot.

This prevents failures such as a bad `mf70_nose` mask crossing into the mouth and then causing `mf70_mouth_lips` to inherit the bad nose region as a protected boundary.

## Non-Negotiable Rule

Do not use a previous editable mask as the authoritative protected boundary for another mask unless that previous mask has passed semantic alignment, protected-neighbor QA, reference-matrix validation where required, and is explicitly promoted as a canonical boundary layer.

For normal Wave70 work, every mask must be checked against independent canonical boundaries:

- source image dimensions and crop
- model-backed landmarks, semantic parsing, promptable segmentation refinement, or manually reviewed gold traces
- taxonomy `protected_regions`
- zoomed source/overlay review
- reference-image matrix slot metadata

The green allowed / amber protected geometry panel must also pass `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md`, `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` where applicable, and `Plan/Instructions/QA/MASK_GEOMETRY_HARD_GATE_PROTOCOL.md`. Protected-boundary evidence is not valid if the allowed/protected regions are only broad debug rectangles, visibly misaligned, based on Haar/Canny alone, or not proven in the same full-image/crop/panel coordinate space.

## Boundary Source Priority

Use this order when creating or validating protected boundaries:

1. Model-backed source-derived landmarks, semantic parsing, promptable segmentation refinement, and visibility/occlusion confidence for the current image.
2. Whole-body source-derived pose, hand, human parsing, person-instance, contact/occlusion, and body regions safety geometry where applicable.
3. Manually reviewed gold/canonical boundary polygons for the current image and matrix slot.
4. Taxonomy-defined protected-region labels mapped onto model-backed source geometry.
5. Previously generated masks only if they are explicitly marked `canonical_boundary_layer_pass` and still pass model-backed and whole-body authority on the current source.

If no reliable boundary source exists, record a blocker instead of guessing:

- `Blocked_Wave70_Mask_Geometry_Gate_Not_Passed`
- `Blocked_Model_Geometry_Dependency_Missing`
- `Blocked_Model_Geometry_Low_Confidence`
- `Blocked_Model_Geometry_Disagreement`
- `Blocked_Body_Geometry_Dependency_Missing`
- `Blocked_Body_Geometry_Low_Confidence`
- `Blocked_Hand_Finger_Geometry_Not_Trusted`
- `Blocked_Contact_Occlusion_Ownership_Unresolved`
- `Blocked_Body_Geometry_Low_Confidence`
- `Blocked_Canonical_Boundary_Not_Available`
- `Blocked_Source_Resolution_Too_Low`
- `Blocked_Local_Source_Region_Not_Visible`

## Required Boundary Registry

Each generalized or repair-focused mask package must include or link a boundary registry manifest:

```json
{
  "boundary_registry": {
    "source_image_id": "",
    "matrix_slot_id": "",
    "canonical_boundary_layer_pass": false,
    "boundary_layers": [
      {
        "region_id": "nose | mouth_lips | eyes | eyelids | cheeks | jaw_chin | hairline",
        "source": "model_landmark | pose_landmark | hand_landmark | human_part_parsing | contact_occlusion_authority | body_regions_geometry_authority | semantic_parsing | promptable_segmentation | manual_reviewed_gold_trace | promoted_canonical_mask",
        "path": "",
        "sha256": "",
        "model_backed_geometry_authority_pass": false,
        "whole_body_geometry_authority_pass": false,
        "review_status": "pass | needs_revision | fail | blocked"
      }
    ],
    "protected_overlap_matrix_path": "",
    "protected_overlap_matrix_pass": false
  }
}
```

## Overlap Rules

For every mask, compute or manually record an overlap matrix against canonical protected neighbors.

Fail or require revision when:

- `mf70_nose` overlaps mouth, upper lip, philtrum beyond allowed boundary, inner eye/canthus, lower eyelid, or broad cheeks.
- `mf70_mouth_lips` overlaps nose, philtrum beyond allowed boundary, chin, broad cheeks, teeth/tongue/inner mouth when those are protected.
- Eye-region masks overlap eyelids, eyelashes, iris/sclera, brow, or under-eye skin outside the named target.
- Cheek masks overlap nose, mouth, lower eyelids, hairline, or jawline beyond the named cheek-skin region.
- Jaw/chin masks overlap lips, mouth corners, broad neck, clothing, hair, or cheeks beyond the contour region.
- Hairline masks overlap forehead, brows, eye region, or background beyond the named hairline edge.
- Hand/finger masks overlap wrist, object, other hand, contacted body part, or background beyond the declared target.
- Torso/chest/abdomen/umbilicus masks overlap clothing, arms, hands, body regions regions, support surface, or background beyond the declared target.
- Feet/toe masks overlap floor, shoes/socks, ankles, or contact shadows outside the declared target.
- Contact masks lack owner/occluder/shared-contact boundaries or inherit boundaries from a bad earlier hand/body mask.

Low denoise and stable generated output do not waive overlap failures.

## Future-Mask Rule

All future face, body, clothing, hand, contact, video, audio, and deformation masks must define:

- target region boundary
- protected-neighbor boundaries
- allowed overlap tolerance, if any
- canonical boundary source
- overlap pass/fail result

This must be done before a mask can be marked locally passed, generalized, or certification-ready.
