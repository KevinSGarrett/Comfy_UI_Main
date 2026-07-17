# App Mode + Orchestrator Design

## App Mode role

App Mode should be the clean UI for non-node operation. It should expose task-level controls, not internal node details.

## Recommended App Mode controls

- Scene request text
- Output mode: still, GIF, video, full AV
- Character count
- Character reference uploads
- Pose/camera reference uploads
- Body-shape target selector
- Detail target selector
- Contact/soft-body target selector
- Engine mode: Auto, Flux-first, SDXL, Pony specialty, video-auto
- QA review profile request: draft, normal, strict, release (display/proposal only; never live promotion authority)
- Final output preview
- QA report preview

## Orchestrator role

The additive Rows321-348 MaskFactory bridge supersedes any interpretation of
the QA review-profile control as a live strictness or promotion-policy dial.
Core runtime uses a pinned `maskfactory_promotion_gate_policy_v2` with structured
versioned criteria, comparators, thresholds, evidence/analyzer manifests, and
revocation manifests. App values cannot mutate that policy, and optional
independent-accuracy evidence cannot alter the core decision.

## MaskFactory page/read-model binding

Rows321-348 require the App to consume the generated
`wave64_maskfactory_bridge_app_read_model_mapping_v2` registry. The binding is:

| Page | MaskFactory bridge read models |
|---|---|
| Home / Readiness | `maskfactory_bridge_readiness_projection_v2`, health/capability snapshot, bridge release certificate |
| Projects / Revisions | release snapshot, adoption receipt, invalidation event |
| Scene Builder / Pose & Masks | bridge request, normalized result, authority decision |
| Runs / DAG | event, request, result, authority decision |
| Queue / Workers | health/capability snapshot, bridge event |
| Recovery | invalidation event, bridge event, normalized result |
| QA | normalized result, authority decision, promotion policy, operational certificate |

The Home projection separates planning/fixture state from genuine runtime
evidence and shows Row218, Rows321-347, Row348, and each completion profile.
These read models are read-only and cannot call MaskFactory directly, mutate
producer truth, change authority, infer runtime readiness from fixtures, bypass
a blocker, or commit promotion.

The orchestrator:
- reads the App Mode inputs
- builds a pass plan
- edits API workflow JSON values
- submits workflows to ComfyUI
- waits for outputs
- runs QA
- reruns failed modules
- writes manifests
- returns final outputs and QA report

## Required ComfyUI API operations

- Get node metadata with object_info.
- Upload input images/masks.
- Submit workflows to prompt queue.
- Poll or subscribe for progress.
- Read history and locate outputs.
- Save outputs, masks, control maps, and crops.
- Write run manifest.

## Required orchestrator services

- pass_plan_builder
- workflow_template_patcher
- comfyui_client
- output_collector
- mask_factory_client
- qa_evaluator
- rerun_decision_engine
- manifest_writer
- promotion_gate

## MaskFactory bridge page behavior freeze

The generated page/read-model registry is the source of truth for field paths;
the following defines product behavior.

### Home / Readiness

Show the active release/adoption pin, trusted signer state, signed journal head,
Row218, Rows321-347, Row348, all seven page projections, genuine runtime evidence,
and exact core blockers. Show `independent_real_accuracy` and
`scale_daz_maturity` separately as optional profiles. The page never calculates
readiness from a green badge, fixture, aggregate percentage, or conversation.

### Projects / Revisions

Show immutable producer release ID/hash, supersession/revocation state, Main
adoption decision, trusted-key registry reference, allowed capabilities, journal
checkpoint/head, and invalidation impact. A revision switch is a schema-bound
controller command that revalidates and atomically changes a pin; the browser
never selects a raw directory or mutable worktree.

### Scene Builder / Pose & Masks

Show exact still/frame/span scope; target character; declared character, prop,
and environment roster; target/protected input regions; provider indices;
requested intents; executable transform summary; output-mask lineage; authority
and claim class; and intended-use blockers. The page must visually distinguish
input constraints from generated outputs and must never flatten multi-character
ownership into a single anonymous mask.

### Runs / DAG

Show project/run/job/pass/attempt/hypothesis, lifecycle state, selected route and
selection reason, eligible alternatives, input/output dependencies, exact media
scope, factual QA, authority decision, cache state, and blockers. Quality repair
creates a child attempt with a new hypothesis while the accepted parent remains
immutable.

### Queue / Workers

Show route health/freshness, authenticated capability eligibility, runtime kind
and immutable provenance, queue/runtime durations, peak RAM/VRAM, resource/deadline
conformance, idempotency state, and circuit state. `outcome_unknown` is visibly
distinct and offers only the schema-bound reconcile command, not blind retry.

### Recovery

Show trusted checkpoint/head, stream sequence and hash continuity, invalidation
tombstones, fork/quarantine state, outcome-unknown reconciliation, safe resume
frontier, and affected versus unaffected DAG branches. A journal gap, fork,
reorder, reseal, or signing-key substitution disables resume and promotion.

### QA

Show factual QA observations separately from exact-use eligibility. Display the
signed policy hash and complete criterion vector, claim class, certificate scope,
signer trust, decision-time issue/expiry/revocation evaluation, media scope,
runtime evidence, and blocker provenance. `operationally_certified_artifact` must
never be labelled independent accuracy or training gold.

Across every page, LLM/VLM output is explicitly labelled proposal or observation.
Conversation and compaction summaries are not durable project truth. All writes
go through the controller tool gateway and return an admitted event/receipt; no
page, App Mode launcher, browser extension, or model can directly call production
MaskFactory, alter producer truth, mutate pinned policy, promote an artifact, or
mark runtime readiness.
