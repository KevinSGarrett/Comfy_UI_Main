# GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL

## Purpose

Manual gold-standard mask creation is a scoped dependency gate, not a global project freeze.

Gold masks must remain strict, source-specific, manually reviewed or explicitly approved, and fail-closed when missing. At the same time, unrelated project work may continue when it does not consume candidate masks as truth and does not claim mask promotion, body geometry authority, or certification readiness.

## Required Blocker Code

Use this blocker when a task depends on trusted manual gold masks that are not yet available or not yet validated:

```text
Blocked_Gold_Mask_Dependency_Missing
```

The blocker applies only to the task, row, artifact, or gate that actually depends on gold masks.

## Work That Must Fail Closed

The following work must not pass, promote, certify, or activate until required gold masks and intake/gate evidence exist:

- Canonical body-part mask promotion.
- Mask-based body, hand, finger, hair, clothing, contact, or body-region geometry authority.
- Body/hand/contact validation that relies on trusted masks.
- Final Mask Factory QA that requires approved gold-standard masks.
- Any claim that a body mask, body geometry route, reference matrix, or generated output is gold-standard, universal, certification-ready, or target-runtime-ready.
- Any Wave71+ activation that relies on mask or geometry proof from gold masks.

## Work That May Continue

The following work may continue while manual gold masks are being created, as long as it does not promote or certify mask truth:

- Workflow structure and project organization.
- Tracker and item progression for non-mask-dependent rows.
- Evidence, logging, manifest, and report scaffolding.
- UI, pipeline, and orchestration wiring.
- Prompt and workflow templates.
- Dataset organization, intake manifests, and validation scaffolds.
- Automation, cron, session cleanup, and hydration/session-state maintenance.
- ComfyUI workflow wiring that does not require final mask truth.
- Non-body-mask asset handling and registry work.

## Required Behavior

If a task needs gold masks, mark only that task or row as `Blocked_Gold_Mask_Dependency_Missing`.

Do not rerun geometry authority, promotion, or Wave71 activation gates merely because manual masks, candidate masks, SAM outputs, or promptable segmentation experiments exist.

Do not consume guarded in-progress folders, candidate batches, rejected V2/V3 outputs, or source-test images as gold-standard evidence.

Continue unrelated non-mask work when it can be completed without making mask truth claims.

Manual masks become eligible for gold-standard intake only after all of the following are true:

1. The user explicitly signals that the manual masks are ready for intake.
2. The masks are routed through the canonical intake manifest or equivalent source-of-truth mapping.
3. Strict QA, protected-neighbor review, geometry/promotion gates, and required evidence pass for the exact mask label and source image or reference-matrix slot.

## Facial, Neck, And Hair Dataset Exception

The paired CelebAMask-HQ shard-0 and LaPa datasets registered in
`Plan/10_REGISTRIES/facial_neck_hair_gold_standard_dataset_registry.json` are
available for source-paired facial parsing, supported neck, hair, and landmark
benchmarking under
`Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md`.

This availability removes the missing-gold dependency only for the exact
facial/neck/hair classes represented by those datasets. It does not itself
promote or certify any masking route. Manual body and body-part masks remain in
progress, and the existing blocker continues to apply to body, hand, finger,
contact, whole-body geometry, body-mask promotion, and dependent Wave71+ gates.

## Status Taxonomy

Use these statuses where helpful:

```text
Allowed_NonMask_Work_Can_Continue
Manual_Gold_Mask_Work_In_Progress
Blocked_Gold_Mask_Dependency_Missing
Gold_Mask_Ready_For_Intake_Validation
Gold_Mask_Intake_Validated_Not_Promoted
Gold_Mask_Gate_Passed_Promotable
```
