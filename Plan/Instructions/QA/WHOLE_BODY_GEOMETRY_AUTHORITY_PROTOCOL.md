# Whole-Body Geometry Authority Protocol

## Purpose

The Mask Factory must not treat face geometry as the whole system. Body, hands, fingers, hair, body skin, clothing contact, support contact, soft-body maps, and temporal masks need their own source-derived geometry authority.

This protocol extends `MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md` from face-first geometry into full human-body masking.

## Non-Negotiable Rule

No Wave70 body, hand, skin, hair, clothing/contact, support-surface, soft-body, video, audio-linked, or temporal mask can be accepted, candidate-passed, locally passed, generalized, certification-ready, target-runtime-ready, or used as canonical protected geometry unless whole-body geometry authority evidence exists for the exact source image or reference-matrix slot.

Required row evidence tokens:

```text
whole_body_geometry_authority_pass
pose_hand_dense_landmark_or_segmentation_pass
semantic_human_part_parsing_pass
contact_occlusion_ownership_pass
body_region_geometry_pass
body_reference_matrix_pass
```

If the model route cannot resolve the body part, visibility, side, owner, occluder, or protected-neighbor boundary, the row must block instead of guessing.

## Required Model Families

Allowed source-derived routes include:

- MediaPipe Pose Landmarker style body landmarks and optional segmentation masks for torso, limbs, joints, and full-person silhouette.
- MediaPipe Hand Landmarker style hand/finger landmarks for palms, fingers, fingertips, fingernails, grips, and hand contact.
- Human parsing or body-part segmentation models for skin, hair, clothing, torso, arms, legs, feet, and body-part regions.
- Promptable SAM/SAM2-style segmentation refinement using positive target prompts, negative protected-neighbor prompts, and visibility/occlusion constraints.
- Multi-person instance segmentation and tracking for owner separation, occlusion order, and contact boundaries.
- Temporal propagation and drift detection for video masks.

OpenCV, Canny, Haar, broad boxes, and hand-tuned one-image coordinates are diagnostic only. They cannot satisfy this protocol by themselves.

## Required Autonomous Stack

Every body-aware mask route must run locally when possible and write exact blockers when a dependency or model is unavailable.

Required layers:

1. Dependency and model availability probe for pose, hand, human parsing, promptable segmentation, and instance/contact routes.
2. Person-instance and owner separation for single-person and multi-person images.
3. Pose landmark authority for shoulders, elbows, wrists, torso, hips, knees, ankles, and body orientation.
4. Hand landmark authority for hands, palms, knuckles, fingers, fingertips, fingernails, grasp shape, and hand side.
5. Human part parsing for skin, hair, torso, arms, legs, feet, clothing, support objects, and background.
6. Promptable segmentation refinement for each target region with protected-neighbor negative prompts.
7. Visibility, occlusion, and side/owner confidence for each region.
8. Contact and occlusion ownership resolver for hand-on-body, hand-on-object, limb-over-limb, body-on-support, and multi-character contact masks.
9. Canonical polygon and segmentation-map export for every target and protected neighbor.
10. Reference matrix validation across body sizes, poses, camera angles, clothing states, occlusions, support surfaces, skin tones, and source resolutions.

## Body-Part Requirements

The authority must be able to implement or block these target families independently:

- Full visible body skin and local skin zones.
- Neck, shoulders, chest/upper torso, abdomen/stomach, belly button/umbilicus, waist, hips, and back.
- Left/right upper arms, forearms, elbows, wrists, full arms.
- Hands, palms, knuckles, fingers, fingertips, fingernails, held objects, and hand contact.
- Thighs, knees, calves, ankles, feet, toes, and toenails.
- Hair, hairline, scalp, body hair, facial hair, skin marks, tattoos, scars, freckles, moles, tanlines, and pressure marks.
- Clothing, seams, collars, cuffs, shoes, socks, gloves, accessories, and clothing/body boundaries.
- Support-surface contact with bed, chair, couch, floor, wall, table, fabric, and props.
- Contact and occlusion boundaries for hand interactions, limb-over-limb, body-on-support, multi-character separation, and owner assignment.

## Fail-Closed Rules

Fail or block when:

- The source image does not show the requested body part clearly.
- Clothing, hair, another limb, another person, a prop, or support surface occludes the target.
- Pose/hand/human parsing/SAM routes disagree beyond threshold.
- The target side is inferred by symmetry instead of visible evidence.
- A hand/finger mask is broad enough to include the wrist, object, other hand, or contacted body part without an explicit route.
- A torso/abdomen/hip/limb mask crosses clothing, limbs, support surfaces, or protected neighbors outside the route contract.
- A previous bad hand/contact/body mask is being reused as protected-boundary truth.

Required blocker statuses:

```text
Blocked_Body_Geometry_Dependency_Missing
Blocked_Body_Geometry_Low_Confidence
Blocked_Body_Geometry_Disagreement
Blocked_Body_Part_Occluded
Blocked_Body_Part_Not_Visible
Blocked_Body_Source_Resolution_Too_Low
Blocked_Hand_Finger_Geometry_Not_Trusted
Blocked_Contact_Occlusion_Ownership_Unresolved
Blocked_Wave70_Mask_Geometry_Gate_Not_Passed
```

## Required Evidence Fields

Every whole-body geometry record must include:

```json
{
  "whole_body_geometry_authority": {
    "result": "pass | needs_revision | fail | blocked",
    "whole_body_geometry_authority_pass": false,
    "pose_hand_dense_landmark_or_segmentation_pass": false,
    "semantic_human_part_parsing_pass": false,
    "contact_occlusion_ownership_pass": false,
    "body_region_geometry_pass": false,
    "body_reference_matrix_pass": false,
    "source_image": "",
    "source_sha256": "",
    "source_dimensions": [0, 0],
    "mask_type_id": "",
    "matrix_slot_id": "",
    "person_instance_id": "",
    "subject_side_mapping": {},
    "models_attempted": [],
    "models_available": [],
    "pose_landmark_record_path": "",
    "hand_landmark_record_path": "",
    "human_part_parsing_record_path": "",
    "sam_refinement_record_path": "",
    "contact_occlusion_record_path": "",
    "visibility_occlusion_record_path": "",
    "canonical_polygon_path": "",
    "coordinate_transform_manifest_path": "",
    "consensus_metrics": {
      "iou_against_gold_or_prior": null,
      "mean_boundary_error_px": null,
      "max_boundary_error_px": null,
      "center_drift_px": null,
      "protected_overlap_ratio": null,
      "owner_overlap_error_ratio": null
    },
    "confidence": {
      "pose_confidence": null,
      "hand_confidence": null,
      "human_parsing_confidence": null,
      "refinement_confidence": null,
      "contact_ownership_confidence": null,
      "visibility_confidence": null,
      "overall_confidence": null
    },
    "blocked_reason": "",
    "findings": []
  }
}
```

## Passing Thresholds

Thresholds must be declared per body-part family before use.

Default body thresholds:

- `overall_confidence >= 0.90`
- `protected_overlap_ratio <= 0.01`
- `owner_overlap_error_ratio <= 0.01` for contact or multi-person masks
- `center_drift_px <= 5` for medium body parts when gold/reference exists
- `mean_boundary_error_px <= 6` for medium body parts when gold/reference exists
- `max_boundary_error_px <= 14` unless the target is coarse, partially visible, or support-surface-scale
- no unresolved user visual dispute
- no hidden/occluded anatomy invented from symmetry

Fine-detail masks such as fingers, fingertips, fingernails, toes, toenails, belly button, jewelry, contact patches, and occlusion boundaries require stricter target-specific thresholds.

## Autonomy Requirements

All body geometry work must be autonomous:

- Probe local dependencies and model files.
- Use local CPU/GPU if available.
- Record exact missing dependency/model blockers.
- Download nothing unless the project has an explicit approved local model acquisition route.
- Do not ask the user to trace or label future images.
- Use existing user traces as calibration/test evidence, not as a recurring manual dependency.
- Do not start EC2 unless an explicit bounded target-runtime activation gate allows it.

## Source References

- MediaPipe Pose Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
- MediaPipe Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- MediaPipe Face Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- SAM2: https://ai.meta.com/research/sam2/

## Relationship To Other Gates

This protocol feeds:

- `MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md`
- `MASK_GEOMETRY_HARD_GATE_PROTOCOL.md`
- `WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md`
- `WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md`
- `WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md`
- `MASK_PROMOTION_HARD_GATE_PROTOCOL.md`

Generated-output stability cannot override missing whole-body geometry authority.
