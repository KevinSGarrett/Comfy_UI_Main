# Gold / Independent-Anchor Mask Dependency Gate Protocol

## Purpose

Human-anchor or manually corrected gold masks are a scoped dependency only for
the optional `independent_real_accuracy` profile or a row that explicitly
requires an independent human-labelled claim. They are not a dependency for
`core_autonomous_runtime` and must never silently redefine end-to-end core
completion.

Any human-anchor masks that are used must remain strict, source-specific,
independently reviewed, and fail-closed for the exact claim they support.
Separately, an active, unexpired, unrevoked, exact-output certificate issued by
`maskfactory_autonomous` may satisfy core mask authority when its release,
capability, access mode, execution stack, source/output hashes, owner,
transforms, QA, scope, signature, and revocation manifests all pass. Candidate,
draft, unbound, or self-reported outputs never gain authority from this rule.

## Required Blocker Code

Use this blocker when an optional independent-accuracy task explicitly depends
on trusted human-anchor masks that are not available or validated:

```text
Blocked_Independent_Anchor_Dependency_Missing
```

Legacy `Blocked_Gold_Mask_Dependency_Missing` records migrate to
`Blocked_Independent_Anchor_Dependency_Missing` only when the affected row
explicitly requires the optional independent claim. They must otherwise be
re-evaluated under the core autonomous certificate path. The blocker applies
only to that optional task, row, artifact, metric, or claim.

## Independent-Accuracy Work That Must Fail Closed

The following work must not make an **independently human-verified** claim until
the required anchors and intake/gate evidence exist:

- real-image accuracy, mIoU, boundary, false-accept, calibration, or confidence
  claims whose selected methodology requires independent human labels;
- human-versus-autonomous agreement claims;
- a claim that an artifact is human gold or manually certified; and
- a row whose written acceptance contract explicitly selects
  `independent_real_accuracy`.

Core body, hand, finger, hair, clothing, contact, geometry, promotion, and
Wave71+ gates must fail closed when their required **mask authority** is absent,
but that authority may come from an eligible exact-output
`maskfactory_autonomous` certificate. They must not hard-code human issuance.

## Work That May Continue

The following work may continue without human-anchor masks. Where it consumes
masks for core use, it must use valid autonomous authority or remain draft:

- Workflow structure and project organization.
- Tracker and item progression for non-mask-dependent rows.
- Evidence, logging, manifest, and report scaffolding.
- UI, pipeline, and orchestration wiring.
- Prompt and workflow templates.
- Dataset organization, intake manifests, and validation scaffolds.
- Automation, cron, session cleanup, and hydration/session-state maintenance.
- ComfyUI workflow wiring and certified core execution through the adopted
  MaskFactory bridge.
- Non-body-mask asset handling and registry work.
- autonomous prediction, deterministic/VLM QA, bounded repair, abstention,
  package publication, serving, and downstream integration;
- body/hand/contact/whole-body core authority when an exact autonomous
  operational certificate passes; and
- Wave71+ activation when its own exact core authority and activation evidence
  pass without a false human-accuracy claim.

## Required Behavior

If an optional task needs independent anchors, mark only that task or row as
`Blocked_Independent_Anchor_Dependency_Missing`.

Do not rerun geometry authority, promotion, or Wave71 activation gates merely
because manual masks, candidate masks, SAM outputs, promptable segmentation
experiments, or an unscoped confidence score exist. Rerun only when a new exact
authority/evidence hypothesis is available.

Do not consume guarded in-progress folders, candidate batches, rejected V2/V3 outputs, or source-test images as gold-standard evidence.

Continue unrelated work and eligible core autonomous mask work without making
unsupported independent human-accuracy claims.

Human-anchor masks become eligible for optional independent-accuracy intake
only after all of the following are true:

1. The independent-anchor artifact is explicitly submitted for that optional
   profile; core operation never waits for this signal.
2. The masks are routed through the canonical intake manifest or equivalent source-of-truth mapping.
3. Strict QA, protected-neighbor review, geometry/promotion gates, and required evidence pass for the exact mask label and source image or reference-matrix slot.

## Facial, Neck, And Hair Dataset Exception

The paired CelebAMask-HQ shard-0 and LaPa datasets registered in
`Plan/10_REGISTRIES/facial_neck_hair_gold_standard_dataset_registry.json` are
available for source-paired facial parsing, supported neck, hair, and landmark
benchmarking under
`Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md`.

This availability supports independent evaluation only for the exact
facial/neck/hair classes represented by those datasets. It does not itself
promote or certify a masking route. Missing manual body/body-part anchors block
only corresponding optional independent-accuracy claims; they do not block an
eligible autonomous exact-output certificate, core body/hand/contact authority,
or dependent Wave71+ work whose own core gates pass.

## Status Taxonomy

Use these statuses where helpful:

```text
Allowed_NonMask_Work_Can_Continue
Allowed_Autonomous_Core_Mask_Work_Can_Continue
Manual_Gold_Mask_Work_In_Progress
Blocked_Independent_Anchor_Dependency_Missing
Gold_Mask_Ready_For_Intake_Validation
Gold_Mask_Intake_Validated_Not_Promoted
Gold_Mask_Gate_Passed_Promotable
```

`Gold_Mask_Gate_Passed_Promotable` means eligible for the exact optional
human-anchor scope only. It does not promote a model route or downstream
artifact by itself.
