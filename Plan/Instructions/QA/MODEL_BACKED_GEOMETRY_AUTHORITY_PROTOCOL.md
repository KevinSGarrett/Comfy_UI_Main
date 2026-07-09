# Model-Backed Geometry Authority Protocol

## Purpose

Mask generation must stop guessing anatomy from Haar boxes, Canny edges, broad rectangles, or one-image hand-tuned coordinates. Before a mask is generated or promoted, an autonomous geometry authority must derive source-specific body-part geometry from model-backed evidence and confidence checks.

This protocol defines the required local-first stack for face, body, hand, hair, clothing/contact, video, and future mask families.

## Non-Negotiable Rule

No Wave70 mask can be accepted, candidate-passed, locally passed, generalized, certification-ready, target-runtime-ready, or used as canonical protected geometry unless model-backed geometry authority evidence exists for the exact source image or reference-matrix slot.

Required row evidence tokens:

```text
model_backed_geometry_authority_pass
source_derived_landmark_or_segmentation_pass
model_consensus_geometry_pass
visibility_occlusion_confidence_pass
no_symmetry_guessing_pass
whole_body_geometry_authority_pass
```

If model authority is unavailable, contradictory, low-confidence, occluded, or too low-resolution, the row must block instead of guessing.

## Required Autonomous Stack

The geometry authority must run locally when possible and write exact blockers when dependencies or models are unavailable. It must never require human manual work during normal execution.

Required layers:

1. Dependency and model availability probe.
2. Face landmark authority for face oval, eyes, brows, nose, lips, jaw/chin, and face orientation.
3. Semantic face parsing authority for skin, hair, brows, eyes, nose, upper/lower lips, mouth, neck, and background where model coverage permits.
4. Promptable segmentation refinement authority, such as SAM/SAM2-compatible local adapter, using positive/negative points from landmarks/parsing and protected-neighbor prompts.
5. Visibility and occlusion confidence authority. Occluded regions must be marked `partially_visible`, `occluded`, or `blocked`; they must not be invented from symmetry.
6. Gold reference trace authority. User-provided or reviewed traces can be used as calibration/evaluation evidence and future regression tests.
7. Consensus validator. Landmarks, parsing, refinement, and gold traces must be compared with numeric metrics.
8. Canonical polygon export. Masks must be generated from validated source-derived polygons or segmentation maps, not from debug rectangles.
9. Whole-body geometry authority for body, hands, hair, body skin, clothing/contact, soft-body, video, and body region rows, following `WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md`.
10. Reference-image matrix validation before generalized or certification-ready claims.

## Allowed Model Families

The implementation may use whichever local model route is available and source-cited, but the output contract must remain stable.

Acceptable routes include:

- MediaPipe Face Landmarker or Face Mesh style dense face landmarks.
- MediaPipe Hands and Pose style body/hand landmarks.
- Human parsing/body-part segmentation models trained for skin, hair, clothing, torso, arms, hands, legs, feet, and support/background boundaries.
- Face parsing models trained for semantic face regions.
- Segment Anything / SAM2 style promptable segmentation refinement.
- OpenCV/Canny/Haar only as diagnostic assists, never as the sole authority.

If more than one model route is available, the authority should use model consensus. If routes disagree beyond threshold, block.

## Confidence And Disagreement Rules

Fail or block when:

- Only one eye is confidently detected for a two-eye mask and the missing side is occluded or ambiguous.
- Hair texture overwhelms Canny/edge maps.
- Landmark, parsing, and segmentation disagree beyond threshold.
- A full-region target is inferred from symmetry instead of visible source evidence.
- A detector returns a broad box without fine anatomy boundaries.
- The source crop is too small or low-resolution for the target.
- The generated polygon crosses protected neighbors.
- A body, hand, contact, soft-body, or body regions region lacks whole-body geometry authority evidence.

Required blocker statuses:

```text
Blocked_Model_Geometry_Dependency_Missing
Blocked_Model_Geometry_Low_Confidence
Blocked_Model_Geometry_Disagreement
Blocked_Source_Region_Occluded
Blocked_Source_Resolution_Too_Low
Blocked_Body_Geometry_Dependency_Missing
Blocked_Body_Geometry_Low_Confidence
Blocked_Hand_Finger_Geometry_Not_Trusted
Blocked_Contact_Occlusion_Ownership_Unresolved
Blocked_Body_Geometry_Low_Confidence
Blocked_Wave70_Mask_Geometry_Gate_Not_Passed
```

## Required Evidence Fields

Every model-backed geometry record must include:

```json
{
  "model_backed_geometry_authority": {
    "result": "pass | needs_revision | fail | blocked",
    "model_backed_geometry_authority_pass": false,
    "source_image": "",
    "source_sha256": "",
    "source_dimensions": [0, 0],
    "mask_type_id": "",
    "matrix_slot_id": "",
    "models_attempted": [],
    "models_available": [],
    "model_versions": {},
    "landmark_record_path": "",
    "semantic_parsing_record_path": "",
    "sam_refinement_record_path": "",
    "visibility_occlusion_record_path": "",
    "canonical_polygon_path": "",
    "coordinate_transform_manifest_path": "",
    "gold_trace_comparison_path": "",
    "consensus_metrics": {
      "iou_against_gold_or_prior": null,
      "mean_boundary_error_px": null,
      "max_boundary_error_px": null,
      "center_drift_px": null,
      "protected_overlap_ratio": null
    },
    "confidence": {
      "landmark_confidence": null,
      "parsing_confidence": null,
      "refinement_confidence": null,
      "visibility_confidence": null,
      "overall_confidence": null
    },
    "blocked_reason": "",
    "findings": []
  }
}
```

## Passing Thresholds

Thresholds must be declared per target family before use. Default face-detail thresholds:

- `overall_confidence >= 0.90`
- `protected_overlap_ratio <= 0.01`
- `center_drift_px <= 3` for small face parts when gold/reference exists
- `mean_boundary_error_px <= 4` for small face parts when gold/reference exists
- `max_boundary_error_px <= 10` unless the target is coarse or occluded
- no unresolved user visual dispute
- no hidden/occluded anatomy invented from symmetry

The threshold may be stricter for eyes, eyelids, lashes, pupils/iris/sclera, lips, teeth, fingers, jewelry, contact patches, and other fine-detail masks.

## Autonomy Requirements

All model-backed geometry work must be autonomous:

- Probe local dependencies and model files.
- Use local CPU/GPU if available.
- Record exact missing dependency/model blockers.
- Download nothing unless the project has an explicit approved local model acquisition route.
- Do not ask the user to trace or label future images.
- Use existing user traces as calibration/test evidence, not as a recurring manual dependency.
- Do not start EC2 unless an explicit bounded target-runtime activation gate allows it.

## Whole-Body Extension

Face-specific authority is not sufficient for Wave70 completion. Body, hands, fingers, hair, body skin, clothing contact, support contact, soft-body/deformation maps, and body regions must also pass `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md`.

Existing hand, hand-interaction, contact, support, body, soft-body, and body region masks are untrusted until regenerated or exactly blocked from whole-body canonical geometry. Generated-output stability remains output-geometry evidence only.

## Relationship To Other Gates

This protocol feeds:

- `MASK_GEOMETRY_HARD_GATE_PROTOCOL.md`
- `WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md`
- `WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md`
- `WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md`
- `WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md`
- `MASK_PROMOTION_HARD_GATE_PROTOCOL.md`

Generated-output stability cannot override missing model-backed geometry authority.
