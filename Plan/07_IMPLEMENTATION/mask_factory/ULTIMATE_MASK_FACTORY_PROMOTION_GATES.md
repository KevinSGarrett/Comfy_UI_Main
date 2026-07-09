# Wave70 Ultimate Mask Factory Promotion Gates

These gates are mandatory for autonomous Mask Factory development. They are written for AI execution, not human convenience.

## Non-Negotiable Done Definition

A mask type is not complete until all of the following are true:

0. `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md` passes for the exact source image or reference-matrix slot and the row is backed by explicit `model_backed_geometry_authority_pass == true` evidence. Haar/Canny/rectangle-only geometry, one-image hand-tuned coordinates, or a stable low-denoise output cannot satisfy this gate.
1. `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` passes for body, hands, fingers, hair, body skin, clothing/contact, support-surface, soft-body, video, audio-linked, and body region rows and the row is backed by explicit `whole_body_geometry_authority_pass == true` evidence. Prior hand/contact/body generated-output stability cannot satisfy this gate.
2. `Plan/Instructions/QA/Scripts/Test-Wave70MaskPromotionGate.ps1` passes for the current Tracker/Items state and the exact mask row is backed by explicit `wave70_mask_promotion_gate_pass == true` evidence. Without this hard-gate evidence, no mask row may be called accepted, candidate-passed, locally passed, done, complete, certification-ready, or target-runtime-ready.
3. `Plan/Instructions/QA/Scripts/Test-Wave70MaskGeometryGate.ps1` passes for the current Tracker/Items state and the exact mask row is backed by explicit `wave70_mask_geometry_gate_pass == true` evidence. Bad green allowed / amber protected geometry, conflicting overlays, debug-only rectangles, or unproven coordinate transforms block all later gates.
4. The mask type has a stable mask_type_id in ULTIMATE_MASK_COVERAGE_MATRIX.csv.
5. The mask request compiles into a contract JSON with owner_character_id, target_region, scale, protected_regions, allowed_routes, and evidence_paths.
6. A mask artifact is generated as a PNG, alpha map, segmentation map, deformation map, temporal map, or audio-event map appropriate to the mask role.
7. A preview overlay exists and shows target coverage plus protected-neighbor boundaries.
8. Semantic mask-alignment QA passes: the overlay must be anatomically honest for the named mask type, not merely safe at low denoise.
9. Protected-neighbor checks pass. The edit cannot alter protected eyes, mouth, hands, identity anchors, clothing seams, jewelry, other characters, support objects, background, or body region areas unless explicitly routed.
10. Canonical protected-boundary registry proof passes. A mask cannot use another failed, unreviewed, or single-anchor editable mask as the source of truth for protected-neighbor boundaries.
11. Protected-overlap matrix proof passes against the canonical boundaries for the source image and matrix slot.
12. Reference-image matrix proof passes before any generalized, universal, or certification-ready claim. One source image is only a single-anchor smoke proof.
13. High-resolution detail review passes for small anatomy, fine edges, contact patches, seams, jewelry, hands/fingers, and face-detail masks.
14. Quality score is at least 85 and any domain-specific stricter threshold passes.
15. Workflow patch/routing evidence proves the mask was attached to the intended ComfyUI node, input, pass, and output prefix.
16. A generated output artifact exists. Mask-only proof is not final proof.
17. Whole-artifact visual QA passes for images. Localized target-region review alone is insufficient.
18. Generated-output stability does not override failed or uncertain semantic mask alignment. A stable image may be `generated_output_safe_pass` while the mask remains `mask_alignment_needs_revision` or `mask_alignment_fail`.
19. Single-anchor generated-output stability does not override missing reference-matrix coverage. A row may be locally useful while still blocked from universal readiness.
20. For video/GIF masks, frame-grid plus playback QA passes and temporal drift is checked across the full clip.
21. For audio-linked masks, full-duration playback, AV sync, event timing, clipping/noise, and mix-balance checks pass.
22. For soft-body/deformation masks, gravity, collision, rebound/ripple, anchor protection, and shape identity continuity pass.
24. Target-runtime evidence exists before final certification. Local proof is useful but is not target-runtime certification.

## Hard Promotion Validator Rule

Follow `Plan/Instructions/QA/MASK_PROMOTION_HARD_GATE_PROTOCOL.md` before any mask promotion. The validator is intentionally fail-closed: if the source/overlay/boundary evidence, protected-neighbor proof, user-dispute status, reference matrix, or target-runtime proof is missing or ambiguous, the mask remains blocked or needs-revision.

Follow `Plan/Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md` when manual gold-standard masks are still being created or have not yet passed intake. Rows that depend on those masks must stay `Blocked_Gold_Mask_Dependency_Missing`. This blocks only mask-dependent promotion, authority, certification, and Wave71+ activation claims; it does not block unrelated workflow structure, orchestration, evidence/logging, automation, dataset organization, validation scaffolding, or non-mask asset work.

Follow `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md` before geometry or semantic mask alignment. Fine anatomy must be derived from source-specific landmark, parsing, promptable segmentation, visibility/occlusion, and consensus evidence. Canny/Haar/rectangle panels are diagnostic only.

Follow `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` before any body, hand, finger, hair, body skin, clothing/contact, support, soft-body, video, audio-linked, or body region mask alignment. Pose landmarks, hand landmarks, human part parsing, contact/occlusion ownership, body region geometry geometry, and canonical body polygons must drive these masks. Existing hand/contact/body masks must be redone or blocked through this route before they can pass.

Follow `Plan/Instructions/QA/MASK_GEOMETRY_HARD_GATE_PROTOCOL.md` before semantic mask alignment. The green allowed and amber protected regions must be source-derived, coordinate-consistent, readable, non-conflicting, and target-specific. Broad hardcoded boxes and one-image coordinates are debug aids only; they cannot certify mask geometry.

Existing Wave70 face/body-part masks are not truly passed just because prior rows or QA JSONs say `pass`, `candidate_pass`, or `generated_output_safe`. They must stay `Blocked_Wave70_Mask_Promotion_Gate_Not_Passed` until the hard gate passes. This applies to face identity, expression, forehead, cheeks, jaw/chin, skin, eyes, left eye, right eye, pupils/iris/sclera, eyelids, eyelashes, under-eye, eyebrows, nose, mouth/lips, teeth, tongue/inner-mouth, ears, neck, hairline, hair, hands, clothing, contact, and every later body/object/video/audio mask family.

An edge-only or contour-only mask must be labeled as edge/contour. It cannot pass as a full anatomical region. For example, a thin mouth contour cannot pass as `mf70_mouth_lips`, and an off-center nose-side mask cannot pass as `mf70_nose`.

## Semantic Mask-Alignment Rule

Follow `Plan/Instructions/QA/WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md` for every Wave70 mask before marking a row as locally passed. The overlay must match the taxonomy label and avoid protected neighbors. Broad shortcut polygons, shifted regions, partial labels that change the mask meaning, and clothing/background bleed are blocking mask-alignment defects even when the generated image looks stable.

For face-detail masks, the overlay must also pass zoomed source/overlay review. Generic ovals, V-shapes, triangles, broad shortcut polygons, half-target masks, and masks that touch protected neighbors must be marked `mask_alignment_needs_revision` or `mask_alignment_fail`, not pass-with-notes.

## Protected Boundary Registry Rule

Follow `Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md` for every Wave70 mask before marking a row as locally passed. Protected boundaries must come from source-derived landmarks, segmentation, or manually reviewed canonical polygons for the current source image/matrix slot. A previous generated editable mask is not authoritative unless it has been explicitly promoted as a canonical boundary layer.

If `mf70_nose` crosses into the mouth, the mouth mask must not inherit that bad nose area as a protected boundary. In short: a bad nose mask must not become mouth boundary truth. Instead, both masks fail or revise against the canonical nose/mouth boundary registry. The protected-overlap matrix decides the violation; stable generated output does not.

## Reference Image Matrix Rule

Follow `Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md` and `Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_REFERENCE_IMAGE_MATRIX.md` before any Wave70 row is treated as generalized or certification-ready. The current local portrait may be reused only for single-anchor smoke testing. It cannot prove reliable masking across subjects, face/body geometry, expressions, camera angles, occlusion, visibility, or source resolution.

One source image is only a single-anchor smoke proof.

Mask scripts that rely on hardcoded coordinates from one image are smoke scripts only. Generalized generators must adapt to each source image through landmarks, segmentation, or another source-specific geometry route and must record visibility/resolution blockers instead of inventing hidden anatomy or drawing shortcut masks.

## Anti-Loop Rule

Do not refresh Wave65, indexes, hydration, or generic validators just because Wave70 exists. Only rerun Wave65 if Plan source files are added or renamed after this Wave70 package, and only once for that changed source set.

## Whole-Artifact Review Rule

Every generated image, video, GIF, or audio artifact must be reviewed as a whole artifact. A task focused on feet cannot pass if hands are broken. A task focused on mouth timing cannot pass if face identity, eyes, hands, clothing ownership, background, or audio sync fails elsewhere in the artifact.

## Cost-Control Rule

Prefer local ComfyUI validation for mask contracts, previews, overlays, low-resolution image proof, and iterative QA. EC2 is allowed only for bounded target-runtime proof when AWS/Git/model/readiness/cost-control gates pass.
