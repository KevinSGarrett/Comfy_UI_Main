# Wave70 Mask Alignment QA Protocol

## Purpose

Wave70 mask QA must prove that a mask is anatomically honest for its named `mask_type_id`. A low-denoise generated output can prove that a run was visually safe, but it does not prove that the mask itself was correct.

## Non-Negotiable Rule

Do not mark any Wave70 mask item complete, locally generalized, universal, or certification-ready unless the mask first passes model-backed geometry authority from `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md`, whole-body geometry authority from `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` where applicable, then geometry correctness from `Plan/Instructions/QA/MASK_GEOMETRY_HARD_GATE_PROTOCOL.md`, then semantic alignment, protected-neighbor review, canonical protected-boundary review, generated-output stability, and the required reference-image matrix from `Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md`.

Additionally, no Wave70 mask may be called accepted, candidate-passed, locally passed, done, or complete unless `Plan/Instructions/QA/Scripts/Test-Wave70MaskGeometryGate.ps1` and `Plan/Instructions/QA/Scripts/Test-Wave70MaskPromotionGate.ps1` pass and the row cites explicit `model_backed_geometry_authority_pass == true`, `whole_body_geometry_authority_pass == true`, `wave70_mask_geometry_gate_pass == true`, and `wave70_mask_promotion_gate_pass == true` evidence. Until then, existing worked masks must remain `Blocked_Model_Geometry_Dependency_Missing`, `Blocked_Model_Geometry_Low_Confidence`, `Blocked_Model_Geometry_Disagreement`, `Blocked_Body_Geometry_Dependency_Missing`, `Blocked_Body_Geometry_Low_Confidence`, `Blocked_Hand_Finger_Geometry_Not_Trusted`, `Blocked_Contact_Occlusion_Ownership_Unresolved`, `Blocked_Body_Geometry_Low_Confidence`, `Blocked_Wave70_Mask_Promotion_Gate_Not_Passed`, `Blocked_Wave70_Mask_Geometry_Gate_Not_Passed`, `needs_revision`, `fail`, `unreviewed`, or a visibility/resolution blocker.

A single source image may still be used for local smoke testing, but it can only prove a single-anchor result. It cannot prove universal face, body, expression, angle, occlusion, resolution, or future-mask reliability.

For a single-anchor local smoke pass, all three local gates must pass:

1. `mask_geometry_gate_pass`
2. `mask_alignment_semantic_pass`
3. `protected_neighbor_pass`
4. `canonical_protected_boundary_registry_pass`
5. `generated_output_safe_pass`

Generated-output stability never overrides failed or uncertain mask alignment.

Reference-image matrix safety never inherits from a single-anchor pass. Matrix evidence must be reviewed per source image and per target visibility case.

## User Visual Dispute Fail-Closed Rule

If the user supplies a screenshot, panel, overlay crop, or direct visual objection showing that a mask pass claim is wrong, the disputed mask must immediately become fail-closed until a new source-overlay review resolves the specific objection.

The user-supplied visual dispute overrides:

- Existing `semantic_mask_alignment_candidate_pass: true` fields.
- Prior strict-visual-acceptance labels.
- Generated-output stability reports.
- Protected-overlap matrices that were built from coarse, shifted, unreviewed, or non-canonical boundaries.
- Tracker, Items, or ledger rows that only cite the disputed pass evidence.

A disputed candidate must not be used for generated-output proof, target-runtime proof, reference-matrix promotion, or certification until the new review explicitly proves the mask is anatomically centered on the named target, covers the full visible target when required, and avoids protected neighbors. If a local runtime proof was already produced from a disputed mask, keep it only as `generated_output_safe` evidence; it must not promote mask alignment.

For user-disputed masks, the QA record must name the visible failure in plain language. Examples: shifted right of nose, covers cheek instead of nose sidewall, misses nostril/ala, touches inner eye/canthus, touches philtrum/upper lip/mouth, or relies on a tiny protected-overlap thumbnail that cannot prove boundary clearance.

## Gate A - Semantic Mask Alignment

Before Gate A, the geometry panel itself must pass. If green allowed and amber protected overlays are broad debug rectangles, visibly shifted, contradictory, or unproven in source/crop/panel coordinates, record `qa_failed_geometry_boundary_panel_unreliable` and block promotion before semantic alignment is considered.

Before Gate A, the model-backed geometry authority must also pass. If the target/protected regions were derived only from Haar detection, Canny edges, broad boxes, hand-drawn one-image coordinates, or symmetry guesses, record `qa_failed_model_backed_geometry_authority_missing` and block promotion before semantic alignment is considered.

For body, hand, contact, support, soft-body, video, audio-linked, and body region rows, the whole-body geometry authority must also pass. If a prior hand/contact/body mask was only generated from a broad local mask, output-safe low-denoise proof, or untrusted protected boundary, record `qa_failed_whole_body_geometry_authority_missing` and redo or block the mask.

The preview overlay must match the named anatomical or scene target in the taxonomy.

Pass only when:

- The mask covers the named body part, region, event region, temporal span, or deformation field.
- The mask shape is anatomically plausible for that target.
- The mask is not a shortcut polygon that merely avoids breakage.
- The mask would still be meaningful at a stronger denoise or more sensitive edit.
- The mask scale is appropriate for the declared `minor`, `major`, temporal, audio, or deformation role.
- Full-region labels cover the full visible target, not only one side, half, or a convenient subpart.
- The reviewer can explain the anatomical boundary in words without relying on "the output stayed stable."

Fail or require revision when:

- The mask is shifted away from the named target.
- The mask includes a large unrelated body region, clothing region, background region, or object.
- The mask only covers a subset that changes the meaning of the label, such as iris/pupil only for `pupils_iris_sclera`.
- The mask is broad enough that a stable low-denoise proof hides an alignment problem.
- The mask is a generic oval, V-shape, triangle, or coarse polygon for a detailed anatomical feature.
- The mask misses a meaningful visible portion of a full-region label, such as half of a full nose.

## Gate B - Protected Neighbors

The mask must avoid protected regions listed in the taxonomy and contract unless the route explicitly allows them.

Protected-neighbor boundaries must be checked against `Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md`. Do not use a failed, unreviewed, or single-anchor editable mask as the boundary source for another mask. A bad nose mask cannot define the mouth boundary; both must be checked against canonical source-derived boundaries.

Fail or require revision when:

- Eye masks include protected eyelids, lashes, sclera, iris, or brows beyond the requested target.
- Face masks intrude into hairline, ears, neck, clothing, or background when those regions are protected.
- Skin masks bleed into clothing, jewelry, support objects, or background.
- Audio/video/deformation masks include owners, anchors, contact partners, or time spans outside the requested target.
- Nose masks touch or overlap inner eye/canthus, lower eyelid, philtrum, upper lip, mouth, broad cheeks, or unrelated skin outside the allowed target.
- Jaw/chin masks intrude into lips, mouth corners, broad neck, clothing, or hair rather than tracing the actual jaw/chin contour.
- Hand/finger masks merge palm, wrist, object, other hand, or contacted body part outside the declared target.
- Belly button/umbilicus masks are inferred from abdomen geometry without visible source evidence.
- Feet/toe masks merge floor, shoes/socks, ankles, or support shadows outside the declared target.
- Contact masks fail to identify owner, occluder, protected neighbor, and shared contact boundary.
- Body region masks lack explicit technical safety, source/context, and explicit route evidence.

## Required Strict Review Method

Every Wave70 face-detail overlay review must inspect the source, overlay, and generated output at normal view and zoomed view. The QA note must explicitly answer:

- What named anatomical target is being claimed?
- Does the mask cover the full visible target for that label?
- What protected neighbors are closest, and are any touched?
- Is the shape anatomically plausible, or is it a shortcut oval/polygon/stroke?
- Would the mask still be valid at higher denoise or in a more sensitive edit?

If the reviewer cannot answer these directly, use `Generated_Output_Safe_Mask_Alignment_Unreviewed_Target_Runtime_Pending` or a revision/fail status. Do not infer alignment from visual stability.

For generalized or certification-directed work, also follow `Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md`. The reviewer must state whether the evidence is `single_anchor_only` or `reference_image_matrix_pass`.

## Face-Detail Hard-Fail Examples

These examples must not pass semantic mask alignment:

- `mf70_nose`: covers only half of the visible nose, misses a sidewall/ala/nostril region, or touches inner eye, philtrum, upper lip, or mouth.
- `mf70_pupils_iris_sclera`: covers generic eye ovals or only iris/pupil cores without correct visible sclera isolation.
- `mf70_eyelids`: covers upper-orbital or brow-adjacent polygons instead of actual upper/lower eyelid bands.
- `mf70_eyelashes`: uses shortcut strokes that do not trace visible lash lines or that cross eyelid/eye-aperture protected regions.
- `mf70_cheeks_skin`: uses cheekbone polygons that miss cheek surfaces or sit too close to eyes, nose, mouth, hairline, or jawline.
- `mf70_skin_tone_continuity`: includes clothing, background, or artificial neck/chest triangles.

## Gate C - Generated-Output Safety

After the mask alignment and protected-neighbor gates pass or are explicitly recorded as revision-needed, generated-output QA may be used to classify the runtime result.

Generated-output QA must answer:

- Did the output preserve whole-image identity and composition?
- Did the target region avoid visible seams, artifacts, or unnatural texture?
- Did protected regions remain unchanged?
- Did unrelated whole-frame defects appear?

## Required Status Vocabulary

Use these statuses for Wave70 mask rows and evidence:

- `Mask_Alignment_Pass_Generated_Output_Safe_Target_Runtime_Pending`
- `Single_Anchor_Mask_Alignment_Pass_Matrix_Required_Target_Runtime_Pending`
- `Matrix_Mask_Alignment_Pass_Target_Runtime_Pending`
- `Matrix_Mask_Alignment_Needs_Revision_Target_Runtime_Pending`
- `Matrix_Mask_Alignment_Fail_Target_Runtime_Pending`
- `Mask_Alignment_Needs_Revision_Generated_Output_Safe_Target_Runtime_Pending`
- `Mask_Alignment_Fail_Generated_Output_Safe_Target_Runtime_Pending`
- `User_Disputed_Mask_Alignment_Fail_Generated_Output_Safe_Target_Runtime_Pending`
- `Generated_Output_Safe_Mask_Alignment_Unreviewed_Target_Runtime_Pending`
- `Blocked_Wave70_Mask_Promotion_Gate_Not_Passed`
- `Blocked_Wave70_Mask_Geometry_Gate_Not_Passed`
- `Blocked_Source_Resolution_Too_Low`
- `Blocked_Local_Source_Region_Not_Visible`

Do not use `Local_Generated_Output_Proof_Pass_Target_Runtime_Pending` for new Wave70 mask rows. Do not use candidate/pass statuses at all unless the hard promotion gate passes. If semantic alignment, protected-neighbor review, generated-output stability, and the hard gate all pass on only one source image, use `Single_Anchor_Mask_Alignment_Pass_Matrix_Required_Target_Runtime_Pending`. Use `Matrix_Mask_Alignment_Pass_Target_Runtime_Pending` only when the reference-image matrix also passes.

## Required Evidence Fields

Each Wave70 mask QA JSON must include or be accompanied by:

```json
{
  "semantic_mask_alignment": {
    "result": "pass | pass_with_notes | needs_revision | fail | blocked",
    "named_target_match": true,
    "protected_neighbor_pass": true,
    "generated_output_safe_pass": true,
    "completion_allowed": false,
    "findings": []
  },
  "boundary_registry": {
    "canonical_boundary_layer_pass": false,
    "protected_overlap_matrix_pass": false
  }
}
```

Generalized evidence must also include or link:

```json
{
  "reference_image_matrix": {
    "result": "pass | needs_revision | fail | blocked | required_not_run",
    "single_anchor_only": true,
    "minimum_resolution_pass": false,
    "cross_subject_generalization_pass": false,
    "completion_allowed": false
  }
}
```

For pre-existing Wave70 evidence, append a retroactive `semantic_mask_alignment_reaudit` block instead of rewriting old generated-output findings.

## Retroactive Audit Rule

Previously generated outputs may keep their visual QA result if they were stable, but tracker and item rows must be downgraded or flagged when the overlay does not semantically match the named mask type.

The correct interpretation is:

- Generated-output stable means the run did not visibly damage the artifact.
- Mask-alignment pass means the overlay correctly represents the named target.
- Single-anchor mask-alignment pass means the overlay correctly represents the named target only for that one source image.
- Matrix mask-alignment pass means the mask strategy survived representative subject, angle, expression, visibility, occlusion, and resolution cases.
- Final mask completion requires semantic alignment, protected-neighbor review, canonical protected-boundary registry pass, protected-overlap matrix pass, generated-output stability, reference-image matrix pass when claiming generalization, and target-runtime proof before certification.
