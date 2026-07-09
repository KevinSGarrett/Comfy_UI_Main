# Wave70 Ultimate Mask Factory Scope

Wave70 is the required Mask Factory coverage layer for hyperrealistic image, video, GIF, and audio generation.

## Authoritative Files

Read these files before starting or certifying any Mask Factory work:

1. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\mask_factory\ULTIMATE_MASK_FACTORY_TAXONOMY.md`
2. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\mask_factory\ULTIMATE_MASK_COVERAGE_MATRIX.csv`
3. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\mask_factory\ULTIMATE_MASK_FACTORY_PROMOTION_GATES.md`
4. `C:\Comfy_UI_Main\Plan\Items\wave70_ultimate_mask_factory_itemized_list.csv`
5. `C:\Comfy_UI_Main\Plan\Tracker\wave70_ultimate_mask_factory_tracker.csv`

## Scope

Wave70 covers body-part, protected-neighbor, contact, support-surface, clothing, accessory, temporal, audio-linked, body regions, and soft-body/deformation masks.

The existing W69 Mask Factory evidence proves only one narrow local face-skin no-mouth micro mask. It does not certify full face, body, hands, feet, clothing, support objects, multi-character contact, video temporal, audio-linked, body regions, or soft-body deformation coverage.

## Execution Rule

Each mask type must be implemented and proven from its source-cited Item and Tracker row. Do not mark a row complete because it exists in the taxonomy.

Required evidence for each row:

- mask contract JSON;
- owner and target-region assignment;
- generated mask, alpha map, segmentation map, deformation map, temporal map, or audio-event map;
- preview overlay;
- protected-neighbor validation;
- quality score;
- workflow patch or routing manifest;
- generated output artifact;
- strict whole-artifact visual QA;
- temporal QA for video/GIF rows;
- full-duration audio and AV-sync QA for audio-linked rows;
- target-runtime evidence before final certification.

## Whole-Artifact Rule

Localized work cannot pass localized-only review. If a task edits feet, hands can still block promotion. If a task edits a mouth mask, identity, eyes, clothing ownership, support-surface contact, background, audio sync, or temporal continuity can still block promotion.

## Soft-Body Rule

Soft-body, morphing, gravity, collision, jiggle, ripple, rebound, compression, and mesh-control masks are not ordinary edit masks. They require deformation maps, protected anchors, pose-aware checks, contact/collision checks, and temporal continuity evidence.


Adult anatomical mask classes are technical planning rows only unless explicit technical age, consent, safety, and explicit route evidence exists. They must not be routed from normal mask requests.

## Anti-Loop Rule

Do not rerun Wave65, indexes, hydration, or broad validators just because Wave70 exists. Rerun coverage tools only when source files, mask artifacts, routing, generated outputs, or QA evidence changed.
