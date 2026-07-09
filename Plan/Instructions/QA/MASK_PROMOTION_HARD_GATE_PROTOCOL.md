# Mask Promotion Hard Gate Protocol

## Purpose

Mask QA has repeatedly allowed low-denoise generated-output stability to masquerade as mask correctness. This protocol makes mask acceptance fail-closed across face, body, skin, hair, hands, clothing, contact, video, audio, and deformation masks.

## Non-Negotiable Rule

No mask is accepted, complete, locally passed, candidate-passed, generalized, universal, certification-ready, or target-runtime-ready unless a blocking promotion validator passes for that exact `mask_type_id`, source image or matrix slot, and evidence set.

The validator result must be explicit evidence. Prose, screenshots, generated-output stability, previous pass notes, tracker status text, or manual confidence language are not enough.

Required model-backed geometry authority before promotion:

```text
model_backed_geometry_authority_pass == true
W70_MODEL_BACKED_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE
whole_body_geometry_authority_pass == true
W70_WHOLE_BODY_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE
```

Required validator gate:

```text
wave70_mask_promotion_gate_pass == true
W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE
```

Required geometry gate before promotion:

```text
wave70_mask_geometry_gate_pass == true
W70_MASK_GEOMETRY_ROW_GATE_PASS_TRUE
```

For future non-Wave70 mask families, use the same rule with the corresponding family-specific promotion gate. Until such a validator exists, the row must stay blocked or needs-revision.

## Current Wave70 Lockdown

All existing Wave70 human/body/face mask work is treated as not truly passed until it has new hard-gate evidence. This includes, but is not limited to:

- face identity
- expression region
- forehead
- cheeks
- jaw/chin
- skin tone / skin continuity
- eyes full
- left eye
- right eye
- pupils / iris / sclera
- eyelids
- eyelashes
- under-eye
- eyebrows
- nose
- mouth/lips
- teeth
- tongue / inner mouth when visible
- ears, neck, hairline, hair, hands, fingers, nails, clothing, contact, and body-part masks as they are activated

Existing generated-output QA may remain useful as output-geometry evidence only. It must not promote or rehabilitate mask alignment.

## Blocking Validator Requirements

A mask promotion validator must fail unless all applicable checks are true:

1. The row is for the exact `mask_type_id` being promoted.
2. The source image or matrix slot is named and hashable.
3. The mask-only artifact exists and is hashable.
4. `Plan/Instructions/QA/MODEL_BACKED_GEOMETRY_AUTHORITY_PROTOCOL.md` passes for the exact source/crop/mask/panel or writes an exact blocker. Haar/Canny/rectangle-only proof fails here.
5. `Plan/Instructions/QA/WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` passes for body, hand, hair, body skin, clothing/contact, support, soft-body, video, audio-linked, and body region rows, or writes an exact blocker. Prior hand/contact/body generated outputs fail here unless whole-body authority exists.
6. `Plan/Instructions/QA/MASK_GEOMETRY_HARD_GATE_PROTOCOL.md` passes for the exact source/crop/mask/panel. Rectangle-only debug boxes, conflicting green/amber regions, or unproven coordinate transforms fail here.
7. A readable source crop, mask-only crop, source+mask overlay crop, and protected-boundary overlay/panel exist.
8. The panel is large enough for direct review; tiny thumbnails are not sufficient.
9. The semantic target definition is explicit: full region, edge-only, subpart-only, contour-only, temporal span, deformation field, or contact region.
10. The mask matches that exact target definition.
11. Full-region labels cover the full visible target, not only an edge, half, side, or convenient subpart.
12. Edge/contour-only masks are labeled as edge/contour masks; they cannot pass as full body-part masks.
13. Protected neighbors are named and checked against source-derived canonical boundaries.
14. Protected overlap matrix evidence exists and passes.
15. User visual disputes and later fail-closed corrections are checked and are not unresolved.
16. Generated-output stability is separated from semantic mask alignment.
17. Reference-image matrix evidence is present before any generalized/universal/certification-ready claim.
18. Target-runtime proof is present before final certification.

If any check is unknown, ambiguous, too small to inspect, not visible, stale, or contradicted by user-supplied visual evidence, the result is blocked, needs-revision, or fail.

## Source-Alignment Fail-Closed Validator

The hard-gate status validator only proves that no unsupported pass-like row is currently promoted. It does not prove a mask is anatomically aligned.

Before any Wave70 mask can move toward row-level promotion, run source-alignment validation against the actual source image and active mask asset:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave70_source_alignment_fail_closed.py --project-root C:\Comfy_UI_Main --stamp <timestamp>
```

The validator must produce:

- a structured QA evidence JSON under `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/`
- mirrored tracker evidence under `Plan/Tracker/Evidence/`
- per-mask panels with source crop, mask-only crop, source+mask crop, and allowed/protected-region overlay
- target definition, allowed source region, protected-neighbor hits, out-of-target ratio, and final fail-closed decision

Current governing fail-closed evidence:

```text
Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_SOURCE_ALIGNMENT_FAIL_CLOSED_VALIDATION_20260707T223600-0500.json
Plan/Tracker/Evidence/W70_SOURCE_ALIGNMENT_FAIL_CLOSED_VALIDATION_20260707T223600-0500.json
runtime_artifacts/mask_factory/wave70_source_alignment_fail_closed_20260707T223600-0500/
```

This evidence reports `mask_count = 18`, `failing_mask_count = 18`, and `result = fail_closed_current_masks_not_promotable`. It supersedes earlier generated-output, candidate, or pass-with-notes wording for the current masks. Generated-output stability remains useful only as output-geometry evidence.

## Geometry Hard Gate Validator

Before any Wave70 mask row is promoted, run the geometry gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Plan/Instructions/QA/Scripts/Test-Wave70MaskGeometryGate.ps1 -ProjectRoot C:\Comfy_UI_Main -OutJson Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_<timestamp>.json
```

The geometry gate is separate from semantic mask alignment. It fails when the green allowed and amber protected regions are only debug rectangles, visibly misaligned, internally conflicting, too broad for the target, or not proven to share the same source/crop/panel coordinate transform. A mask can be output-safe and still geometry-failed.

## Status Rule

The following status is mandatory for existing mask work until the hard gate passes:

```text
Blocked_Wave70_Mask_Promotion_Gate_Not_Passed
```

Use this additional blocker when geometry is the direct cause:

```text
Blocked_Wave70_Mask_Geometry_Gate_Not_Passed
```

Do not use any of these status meanings unless the hard gate evidence exists and passes:

- `Mask_Alignment_Candidate_Pass_*`
- `Mask_Alignment_Pass_*`
- `Single_Anchor_Mask_Alignment_Pass_*`
- `Matrix_Mask_Alignment_Pass_*`
- `Local_Generated_Output_Proof_Pass_*`
- `Complete`
- `Certification_Ready`

## Validator

Run this validator before any Wave70 mask row is promoted:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Plan/Instructions/QA/Scripts/Test-Wave70MaskPromotionGate.ps1 -ProjectRoot C:\Comfy_UI_Main -OutJson Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_<timestamp>.json
```

The validator is intentionally conservative. If it cannot prove the promotion is valid from structured evidence, it fails.
