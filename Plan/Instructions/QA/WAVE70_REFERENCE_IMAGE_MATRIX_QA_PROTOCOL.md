# Wave70 Reference Image Matrix QA Protocol

## Purpose

Wave70 is an ultimate mask system, so one portrait cannot prove universal mask behavior. A single image may be used to debug contract creation, workflow routing, and low-denoise generation, but it is only a single-anchor smoke proof.

Final local-generalization, universal-readiness, or certification-ready status requires a representative reference image matrix.

## Non-Negotiable Rule

Do not treat a Wave70 mask as universal, locally generalized, or certification-ready from one source image. A single-image pass must be recorded as single-anchor evidence only.

Required independent gates for generalized Wave70 mask completion:

1. `semantic_mask_alignment_pass`
2. `protected_neighbor_check_pass`
3. `generated_output_safe_pass`
4. `reference_image_matrix_pass`
5. `high_resolution_detail_review_pass` when the target is a small face, hand, jewelry, clothing-edge, contact, or fine-detail region
6. `target_runtime_evidence_pass` before final certification

Generated-output stability on one image never proves cross-subject, cross-angle, cross-expression, or cross-resolution reliability.

## Allowed Use Of A Single Anchor Image

A single anchor image may be used only for:

- Contract/schema validation.
- Initial mask generator plumbing.
- Preview overlay debugging.
- Low-denoise generated-output smoke testing.
- Discovering whether a target region is visible on that source.

A single anchor image may not be used for:

- Universal mask completion.
- Certification-ready status.
- Claims that a mask works across faces, bodies, expressions, camera angles, occlusion, lighting, or image quality levels.
- Replacing a visibility matrix for masks like teeth, tongue, ears, hands, contact patches, profile-only anatomy, or covered clothing/body regions.

## Minimum Face Reference Matrix

Face and face-detail masks must be tested against a minimum matrix before any generalized pass:

| slot_id | required coverage |
| --- | --- |
| `face_front_neutral_highres` | Frontal neutral face, both eyes visible, full nose/mouth/chin visible, source suitable for zoomed detail review |
| `face_front_smile_teeth` | Frontal smile or parted lips with visible teeth for mouth/teeth gates |
| `face_front_open_mouth_inner` | Open-mouth or visible inner-mouth case for tongue/inner-mouth gates |
| `face_three_quarter_left` | Left three-quarter head angle with both protected neighbors reviewable where possible |
| `face_three_quarter_right` | Right three-quarter head angle with both protected neighbors reviewable where possible |
| `face_profile_or_near_profile` | Profile or near-profile case to test partial visibility and side-specific boundaries |
| `face_eye_expression_variant` | Squint, downcast gaze, blink-adjacent, heavy eyelid, makeup, or lash-dominant case for eye-region masks |
| `face_occlusion_or_hair_variant` | Hair, glasses, hand, jewelry, shadow, or accessory near a face target, used to prove protected-neighbor behavior |

The matrix should vary identity, skin tone, hair type, face shape, lighting, and camera crop. Reusing the same generated portrait with small prompt changes does not count as cross-subject coverage unless the manifest proves materially different subject geometry and visibility.

## Resolution Requirements

Minimum source and review requirements:

- General local smoke proof: source may be 768 px or larger on the short edge if the target is clearly visible.
- Face-detail matrix proof: source should be at least 1024 px on the short edge, and the face region should be large enough for reliable zoomed overlay review.
- Fine-detail masks such as pupils/iris/sclera, eyelids, eyelashes, eyebrows, teeth, lips, nostrils, jewelry, fingernails, clothing seams, or contact edges require a zoom crop where the target boundary is inspectable without guessing.
- If a target occupies only a tiny or ambiguous region, record `Blocked_Source_Resolution_Too_Low` or `Blocked_Local_Source_Region_Not_Visible` rather than drawing a shortcut mask.

## Matrix Pass Rules

For each `mask_type_id`, record per-slot results:

- `eligible`: the named target is visible enough to judge.
- `blocked_not_visible`: the target is not visible on that slot.
- `blocked_resolution_too_low`: the target is visible but not reviewable at sufficient detail.
- `mask_alignment_pass`: semantic target coverage passes.
- `protected_neighbor_pass`: protected-neighbor boundaries pass.
- `generated_output_safe_pass`: generated output is stable when runtime proof is run.
- `fail`: mask is shifted, too broad, too narrow, shortcut-shaped, or includes protected neighbors.

A generalized matrix pass requires:

- No eligible slot has semantic alignment failure.
- No eligible slot has protected-neighbor failure.
- At least four eligible slots pass for conditionally visible targets such as teeth, tongue, ears, hands, contact patches, or occluded regions.
- At least six eligible slots pass for common face-detail targets such as nose, eyes, eyelids, eyelashes, under-eye, eyebrows, lips, cheeks, jaw/chin, and forehead.
- At least one frontal and one angled slot pass for face-detail masks.
- At least one expression/visibility variant passes for expression, eye, mouth, teeth, tongue, and makeup masks.
- Fine-detail masks include zoom-crop evidence for every eligible pass.

If the matrix exposes a failure after a single-anchor pass, downgrade the row to matrix revision/fail status and repair the generator or request strategy before continuing.

## Future Body, Clothing, Object, Video, And Audio Masks

The same rule applies beyond faces:

- Body masks require front, side/three-quarter, cropped, partially occluded, clothing-edge, contact/support, and varied pose cases.
- Hands/fingers/fingernails require open palm, curled fingers, held object/contact, partial occlusion, left/right hand, and different scales.
- Hair masks require varied hair type, color, flyaways, hairline, background contrast, and occlusion cases.
- Clothing/accessory masks require seam, fold, transparency/edge, jewelry overlap, and skin-boundary cases.
- Multi-character/contact masks require owner separation, contact patch isolation, overlap, shadow, and support-object cases.
- Video/GIF masks require frame-grid and playback matrix coverage across motion, expression, occlusion, and temporal drift.
- Audio-linked masks require event-type and full-duration playback coverage, not only a single timestamp.

## Required Evidence Shape

Each generalized mask QA record must include or link a matrix manifest:

```json
{
  "reference_image_matrix": {
    "result": "pass | needs_revision | fail | blocked",
    "single_anchor_only": false,
    "matrix_manifest_path": "path/to/manifest.json",
    "slots_required": [],
    "slots_passed": [],
    "slots_blocked": [],
    "slots_failed": [],
    "minimum_resolution_pass": true,
    "high_resolution_detail_review_pass": true,
    "cross_subject_generalization_pass": true,
    "completion_allowed": false
  }
}
```

For face masks, the manifest should include `minimum_face_slots` matching the required slot IDs above.

Use `Plan/Instructions/QA/Templates/WAVE70_REFERENCE_IMAGE_MATRIX_MANIFEST_TEMPLATE.json` as the default manifest shape unless a stricter mask-specific schema is created.

For current single-anchor Wave70 evidence, append:

```json
{
  "reference_image_matrix": {
    "result": "required_not_run",
    "single_anchor_only": true,
    "completion_allowed": false
  }
}
```

## Status Vocabulary

Use these statuses when matrix coverage changes the meaning of prior local proof:

- `Single_Anchor_Mask_Alignment_Pass_Matrix_Required_Target_Runtime_Pending`
- `Matrix_Mask_Alignment_Pass_Target_Runtime_Pending`
- `Matrix_Mask_Alignment_Needs_Revision_Target_Runtime_Pending`
- `Matrix_Mask_Alignment_Fail_Target_Runtime_Pending`
- `Blocked_Source_Resolution_Too_Low`
- `Blocked_Local_Source_Region_Not_Visible`

Existing `Mask_Alignment_Pass_Generated_Output_Safe_Target_Runtime_Pending` rows from a single source must be reclassified or explicitly annotated as single-anchor only before they are used for future planning.
