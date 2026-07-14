# ComfyUI Delivery Recovery And Portfolio Control

Updated: 2026-07-13

## Purpose

This protocol restores delivery control across image, video, and audio. It prevents readiness, evidence, infrastructure, or ledger activity from being reported as product advancement when no executable capability, generated media, measured quality improvement, or exact productive blocker was produced.

The authoritative portfolio is:

```text
C:\Comfy_UI_Main\Plan\10_REGISTRIES\comfyui_delivery_portfolio_registry.json
```

The deterministic delivery snapshot is:

```text
C:\Comfy_UI_Main\tools\New-ComfyUIDeliveryProgressSnapshot.ps1
```

## Production Architecture Decision

Separate versioned ComfyUI API workflows are the production architecture. The July 2 monolithic Main Flow snapshot with 356 nodes remains a UI/reference and compatibility surface only. It must not be described as the current production graph until its image, video, audio, input, output, and runtime contracts are synchronized with the proven API workflows and the synchronized graph passes runtime QA.

New production work should extend a bounded lane workflow. Do not delay video or audio implementation merely because those modalities are intentionally separate from the Main Flow.

## Delivery Truth

One of the following is required for `DELIVERY_ADVANCING`:

1. A new executable workflow capability that passes its applicable static and runtime checks.
2. A new genuine image, video, or audio artifact with source settings and direct modality QA.
3. A measured quality improvement on a fixed benchmark with before/after evidence.
4. A production target-runtime proof that has not already been completed for the same unchanged unit.
5. One exact external blocker, followed in the same window by movement to another productive lane.

These do not independently count as delivery:

- plans, runbooks, handoff packets, or readiness summaries;
- dry runs, object listings, dependency probes, upload plans, or repeated gate reruns;
- hydration, manifest, Tracker, Items, Jira, index, audit, proof-log, or Git maintenance;
- worker-wrapper health checks;
- EC2 stopped-state and cost-safety checks;
- synthetic audio fixtures or offline routers without a genuine engine execution;
- candidate masks, untrusted geometry, or mask promotion blocked by missing gold truth.

A readiness or dry-run proof may be credited once as an enabling event. Repeating it without a changed executable input, dependency, or blocker resolution is `REPEATED_READINESS_ACTIVITY`, not new progress.

## Portfolio Rules

Every declared lane must be classified as `required_production`, `required_fallback`, `required_support`, `experimental`, `deferred`, or `retired`. No lane may remain indefinitely as an unclassified planned candidate.

The active delivery portfolios are image, video, and audio. During autonomous operation:

- no active modality may go more than 12 hours without a genuine artifact, measured quality improvement, new executable capability, or newly confirmed external blocker;
- a blocked modality must yield to another productive modality instead of consuming the whole window;
- image work must not prevent bounded video and audio progress;
- video must promote one primary engine beyond the existing AnimateDiff fallback;
- audio must select and prove at least one genuine engine or source before router/mixer scaffolding can be called production audio;
- masking dependencies block only mask-dependent authority and certification gates.

Two consecutive two-hour supervisor windows without delivery truth are `DELIVERY_STAGNATION`. A modality beyond the 12-hour limit is `PORTFOLIO_STARVATION`. Both require one concise correction toward the highest-value executable outcome in the portfolio registry, not toward generic bookkeeping.

## Status Vocabulary

- `workflow_graph_complete`: a runnable API workflow and its input/output contracts exist.
- `local_runtime_proven`: the unchanged workflow executed locally and produced a genuine artifact.
- `ec2_runtime_proven`: the unchanged workflow executed on the approved target runtime and pullback/hash evidence exists.
- `technical_qa_passed`: deterministic output checks passed for the stated scope.
- `direct_review_passed`: image, video, or audio was directly reviewed for the stated scope.
- `bounded_scope_complete`: only the named sample/configuration is complete.
- `production_lane_certified`: the declared production scope has multisample runtime and direct QA evidence.

Never shorten `bounded_scope_complete` to “lane complete.” Never use package, queue, or readiness completion as runtime or quality completion.

## Recovery Execution Order

The registry's `recovery_priority` is the default order, subject to live safety and runtime ownership:

1. Preserve and finish any already-running bounded target-runtime unit; do not duplicate it.
2. Produce an image end-to-end benchmark through base, control, repair, and upscale.
3. Promote one primary video candidate with a genuine image-to-video artifact and temporal QA.
4. Select one genuine audio source/engine, create a short reviewed mix, and mux it to a short video.
5. Continue unresolved required image lanes and explicitly defer or retire optional candidates.

The automation fleet supervises this order. It does not execute live AWS, Git, Jira, mask promotion, or certification mutations.

## Duplicate-Work And Runtime Guard

`C:\Comfy_UI_Main` is the execution authority. `C:\Comfy_UI` is archived legacy source, not an active runtime root. The EC2 project copy is runtime/cache state, not planning authority. Reuse hash-proven S3 objects and completed EC2 proofs. Never recreate a completed unit unless workflow, model, input, seed/scope, or acceptance requirement materially changed and the registry records why.

An active EC2 runtime marker owned by another thread must be observed, not replaced or commandeered.

## Automation Contract

The two-hour anti-loop supervisor owns delivery steering. The six-hour auditor checks both sequence and delivery. Fleet health cannot pass solely because schedules and audit files are healthy; it must also report the latest delivery classification. Specialist safety jobs remain independent and must explicitly state that safety success is not delivery progress.

Required audit fields:

```text
delivery_classification
candidate_media_latest_write_at
candidate_media_artifact_count
verified_new_delivery_latest_execution_at
verified_new_delivery_count
verified_new_delivery
new_executable_capability_count
quality_metric_delta
repeated_readiness_or_gate_count
bookkeeping_effort_ratio
image_last_delivery_at
video_last_delivery_at
audio_last_delivery_at
starved_modalities
next_concrete_outcome
```

Candidate media write times are observational only and cannot produce `DELIVERY_ADVANCING`. Verified new delivery requires a recent evidence-native execution timestamp, a passing execution or direct-QA state, an existing media path, an exact SHA-256 match, and hash deduplication. Checkout, restoration, recovery, inventory, and readiness evidence cannot qualify as new delivery. Human/Codex final authority still verifies whether a hash-bound record qualifies for certification.

Automations must treat schema versions before `1.1`, or any snapshot lacking `verified_new_delivery`, as observational-only and may not emit `DELIVERY_ADVANCING` from those records.
