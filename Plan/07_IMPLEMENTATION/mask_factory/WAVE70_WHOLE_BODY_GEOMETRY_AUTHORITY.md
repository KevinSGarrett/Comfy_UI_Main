# Wave70 Whole-Body Geometry Authority

## Purpose

Wave70 must produce accurate masks for the full human body, not only the face. The current failures with face and hand/contact masks show that generated-output stability and broad geometry panels are not enough. Body masking requires a dedicated source-derived authority for pose, hands, human parsing, hair/skin/clothing, contact ownership, soft-body anchors, temporal propagation, and body regions.

This plan turns `WHOLE_BODY_GEOMETRY_AUTHORITY_PROTOCOL.md` into autonomous implementation rows.

## Required Pipeline

```text
source image or video frame
  -> dependency/model probe
  -> person-instance detection and owner assignment
  -> pose landmarks and body orientation
  -> hand/finger landmarks
  -> human part parsing
  -> promptable segmentation refinement
  -> visibility, side, occlusion, and contact ownership scoring
  -> source-visible body-region geometry check where applicable
  -> consensus metrics
  -> canonical body-part polygons and segmentation maps
  -> geometry hard gate
  -> mask generation
  -> semantic mask QA
  -> generated-output QA
```

## Implementation Requirements

### 1. Dependency And Model Probe

Autonomously probe for local support:

- image/video I/O
- MediaPipe-compatible pose route
- MediaPipe-compatible hand route
- human parsing/body-part segmentation route
- person instance segmentation route
- promptable SAM/SAM2-style refinement route
- temporal propagation route for video
- blocker writer for missing models/dependencies

### 2. Person Instance And Owner Authority

Implement or block person/owner detection. Every body part must belong to a named person instance. Multi-character, contact, and occlusion masks must identify foreground/background owner and shared contact regions.

### 3. Pose Landmark Authority

Implement or block pose landmarks for:

- shoulders, elbows, wrists
- torso/chest/abdomen/hips
- knees, ankles, feet orientation
- body side mapping
- skeleton anchors used to protect identity, joints, and deformation maps

### 4. Hand And Finger Authority

Implement or block hand landmarking for:

- left/right hands
- palms and knuckles
- fingers, fingertips, fingernails
- hand grip geometry
- hand-on-body and hand-on-object contact boundaries

Existing hand/contact masks must be treated as untrusted until this authority passes. Prior low-denoise stable outputs are output-geometry evidence only.

### 5. Human Part Parsing Authority

Implement or block semantic body parsing for:

- skin and body skin zones
- hair, scalp, body hair, facial hair
- clothing and accessories
- torso, arms, hands, legs, feet
- support surfaces and background where possible

Parsing output must be compared against pose/hand landmarks and promptable refinement.

### 6. Torso, Chest, Abdomen, Umbilicus, Waist, Hips

Implement or block source-derived geometry for chest/upper torso, abdomen/stomach, belly button/umbilicus, waist, hips, and back. These regions must avoid clothing, arms/hands, support surfaces, and protected neighboring body regions unless explicitly requested by the mask contract.

### 7. Limb And Joint Authority

Implement or block left/right upper arms, forearms, elbows, wrists, thighs, knees, calves, ankles, full arms, and full legs. Side labels must distinguish subject-left/right and viewer-left/right.

### 8. Feet And Toes Authority

Implement or block feet, toes, toenails, socks/shoes, floor/support-surface contact, and frame-edge risk. Toe-level masks need high-resolution crops and stricter thresholds.

### 9. Hair, Body Hair, Skin Marks, And Body Skin

Implement or block hair, hairline, scalp, body hair, body skin, tattoos, scars, freckles, moles, tanlines, and pressure marks. Hair/body-hair cannot be inferred from Canny texture alone.

### 10. Contact And Occlusion Ownership

Implement or block hand-on-body, hand-on-object, limb-over-limb, body-on-support, shared contact, pressure/compression patches, and multi-character separation. A bad hand mask cannot become protected-boundary truth for a later body/contact mask.

### 11. Body Region Geometry


These targets are ordinary body-region masks. If pose, parsing, promptable refinement, visibility, owner/contact, or protected-neighbor evidence is missing or contradictory, the row blocks instead of guessing.




### 13. Soft-Body And Deformation Anchors


Soft-body evidence must preserve skeletal anchors, owner/contact separation, protected neighboring body parts, clothing/support boundaries, and temporal continuity where video is involved.


### 14. Video Temporal Authority

Implement or block temporal tracking, per-frame mask propagation, drift detection, occlusion enter/exit states, and contact persistence. Video masks must pass both frame-grid and playback review.

### 15. Body Reference Matrix

Build or register a body-reference matrix covering:

- different poses
- camera angles
- body sizes
- skin tones
- hair and body-hair cases
- clothing states
- hand/finger configurations
- feet/toe visibility
- contact/support surfaces
- occlusion and multi-person cases
- body-region regression cases

One portrait or one hand proof is single-anchor smoke evidence only.

### 16. Redo Existing Body/Hand/Contact Masks

All prior hand, hand-interaction, contact, support, body, and soft-body masks remain untrusted until regenerated or explicitly blocked through this authority. Generated-output stability may remain as output-geometry evidence but cannot pass mask alignment.

## Required Artifacts

- dependency/model probe JSON
- person-instance/owner JSON
- pose landmark JSON
- hand landmark JSON
- human part parsing JSON or blocker
- SAM/SAM2 refinement JSON or blocker
- visibility/occlusion JSON
- contact/ownership JSON
- body-region geometry check JSON when applicable
- canonical body-part polygon JSON
- coordinate transform manifest
- consensus metrics JSON
- source+geometry panel
- protected-neighbor panel
- body reference-matrix manifest
- tracker evidence mirror

## Done Definition

This authority is not complete until all rows in `WAVE70_WHOLE_BODY_GEOMETRY_AUTHORITY_MATRIX.csv` are implemented with strict evidence or blocked with exact local-first blockers, and every affected mask row remains fail-closed until whole-body authority, geometry hard gate, and promotion hard gate all pass.
