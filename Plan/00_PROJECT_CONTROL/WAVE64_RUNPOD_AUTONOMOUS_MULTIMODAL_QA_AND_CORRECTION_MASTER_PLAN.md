# Wave64 RunPod Autonomous Multimodal QA and Bounded-Correction Master Plan

Updated: 2026-07-21 America/Chicago
Program ID: `W64-AQA`

## Decision

The project will use a fail-closed, evidence-producing QA controller rather than
one unrestricted "master LLM." The current production-capable tier is sized for
the live single RTX 6000 Ada 48 GB RunPod and runs generation and review in
separate GPU phases. Larger reviewers are optional future services, not current
runtime authority.

This package is additive to the existing Wave64 autonomous model-intelligence,
image, video, audio, speech, and MaskFactory programs. It does not promote their
planning artifacts, discovery catalogs, backup files, or model names into
runtime authority.

## Current authority and runtime truth

- `C:/Comfy_UI_Main` and its Git history are the sole ComfyUI project authority.
- The live runtime is RunPod pod `1q4ji0gg1fkhvt`, one RTX 6000 Ada 48 GB,
  attached to network volume `o9qv2ld91c` at `/workspace`.
- The 20 GB container overlay is disposable and must not hold model libraries,
  accepted artifacts, Ollama blobs, or durable evidence.
- ComfyUI and Ollama were healthy during the 2026-07-21 reconciliation.
- The installed strict product reviewer is `qwen2.5vl:32b`. Installed smaller
  VLMs are smoke or triage helpers only.
- EC2 is forbidden for current generation or review. Existing S3 objects with
  EC2-era names are historical evidence, not permission to restart EC2.
- Sibling clones, recovery checkouts, transfer copies, WSL images, and backup
  directories are read-only evidence or recovery sources until exact bytes are
  deliberately reconciled into the authoritative repository.
- MaskFactory is an external mask producer and quality-evidence source. Its
  repositories and data stores are not silently writable from this program.
- Static-control implementation is not proof that every modality or reviewer
  is installed, calibrated, or production-certified.

## Autonomy authority model

The controller separates five authorities:

1. **Specification authority** creates the immutable job quality contract.
2. **Measurement authority** emits deterministic media and mask measurements.
3. **Reviewer authority** emits schema-constrained observations and confidence.
4. **Policy authority** applies hard gates, retry limits, and promotion rules.
5. **Integration authority** accepts project-state changes, evidence, Git, and
   external mutations.

An LLM or VLM may diagnose, rank, explain, or propose a bounded patch. It may
not certify itself, lower thresholds, invent runtime evidence, mutate trackers,
approve credentials, promote artifacts, commit, push, or authorize cloud cost.

## Current model tiers

### Tier P0: deterministic preflight and measurement

Always runs first. It validates hashes, dimensions, codecs, alpha/channel
semantics, frame and sample counts, clipping, loudness, silence, image
statistics, mask topology, temporal sampling, lineage, required references,
and receipt completeness. A hard failure cannot be overridden by a VLM score.

### Tier P1: inexpensive triage and crop selection

Installed small models such as `qwen3-vl:4b-instruct-q4_K_M`,
`qwen3-vl:8b-instruct-q4_K_M`, `qwen2.5vl:7b`, and `llava:13b` may reject
obvious failures, select crops/frames, or exercise connectivity. They are never
sufficient for product approval.

### Tier P2: strict product review

`qwen2.5vl:32b` is the current visual product reviewer only when its exact
digest, runtime, prompt/rubric version, artifact hashes, calibration state, and
phase-safe VRAM receipt are present. Its PASS is necessary but not sufficient:
all deterministic hard gates and lineage checks must also pass.

### Tier P3: independent specialist or juror

No independent product juror, semantic audio judge, or golden-mask ensemble is
currently certified by this package. Each remains `BLOCKED_UNQUALIFIED` until
the exact checkpoint, license, hash, runtime envelope, calibration corpus,
failure rate, structured-output reliability, and cost ceiling are evidenced.

### Tier P4: optional multi-GPU arbitration

Qwen3.5 122B/397B, InternVL 241B, Qwen3-Omni, Qwen3-Coder-Next, or comparable
models may be evaluated only as separate capacity-qualified endpoints. The
122B, 241B, and 397B classes are explicitly forbidden from being claimed as
runnable on the current single 48 GB pod. Absence or cost rejection of P4 never
weakens P0-P2 gates; it produces abstention, hold, or human exception review.

## Phase-safe GPU protocol

The single GPU is scheduled through an exclusive phase lease:

1. Reconcile foreign jobs and ComfyUI queue ownership; never kill an unknown job.
2. Run generation with Ollama reviewers unloaded.
3. Wait for a terminal generation receipt and an idle ComfyUI queue.
4. Unload ComfyUI models through the approved helper and record free VRAM.
5. Start the selected reviewer with `OLLAMA_MODELS=/workspace/ollama`.
6. Run bounded review requests and record reviewer digest and VRAM evidence.
7. Unload the reviewer (`keep_alive=0`) before another generation phase.
8. Reconcile the lease and queue before continuing.

Concurrent ComfyUI generation and the 32B strict reviewer are forbidden unless
a later, measured runtime envelope explicitly proves that exact combination.

## Complete autonomous control loop

The target controller owns the whole closed loop, not only visual scoring:

1. Compile the creative request into an immutable quality contract.
2. Retrieve only installed, compatible, licensed, and qualified models,
   workflows, LoRAs, controls, masks, voices, and specialist tools.
3. Produce a versioned generation plan and estimate GPU, storage, time, and cost.
4. Validate the ComfyUI graph, nodes, model references, parameter ranges,
   output paths, and runtime envelope before submission.
5. Generate candidates with exact workflow, seed, prompt, model, and lineage.
6. Run deterministic image, video, audio/AV, mask, and workflow measurements.
7. Run triage, strict review, independent review, and senior arbitration as
   qualified roles and the job policy require.
8. Merge findings into a typed, evidence-localized defect report.
9. Select the smallest authorized correction: prompt, parameter, graph patch,
   regional mask/inpaint, frame span, audio span, route, or regeneration.
10. Validate the patch in a candidate workflow; never mutate the accepted graph.
11. Rerun failed gates, protected invariants, and regression tests.
12. Keep measured improvement or revert; enforce attempt/no-progress ceilings.
13. Promote only a hash-bound accepted candidate with a complete receipt.
14. Feed eligible evidence into calibration, drift detection, model/workflow
    report cards, and future routing without self-promotion.

The loop handles failures, restarts, and blocked roles autonomously. Human input
is reserved for missing licensed assets, new paid capacity, subjective intent
changes, policy exceptions, and genuinely unresolved adjudication.

## Target self-hosted service topology

The best architecture is a pool of isolated services with one deterministic
policy authority. Services load on demand and need not be resident together.

### Controller and fast planner

A qualified Qwen3.6-35B-A3B-class service is the target request compiler,
triage reviewer, correction planner, and route explainer. On the current pod it
requires a measured quantized exclusive-phase deployment. Until then, installed
small models provide bounded triage and deterministic code owns decisions.

### Primary visual reviewer

The current `qwen2.5vl:32b` strict lane remains active while a
Qwen3.5-122B-A10B service is evaluated as the high-accuracy primary reviewer on
separate capacity. It must demonstrate enough calibrated improvement to justify
its runtime and cost.

### Independent visual juror

An InternVL-family checkpoint supplies genuinely independent review. Select the
smallest checkpoint meeting project calibration floors; InternVL 241B is the
no-compromise target only when a multi-GPU cost/capacity gate passes.
Disagreement is preserved and arbitrated rather than averaged.

### Senior visual arbitration

Qwen3.5-397B-A17B FP8 is an optional on-demand multi-GPU endpoint for borderline
masters, persistent anatomy/identity failures, complex temporal defects, or
reviewer disagreement. It never reviews every candidate and never runs on the
current 48 GB pod.

### Audio and audiovisual authority

Qwen3-Omni-30B-A3B-Thinking is the target semantic audio/AV judge, paired with
Qwen3-ASR, forced alignment, NISQA, DNSMOS, CLAP, speaker embeddings, onset and
event detectors, and deterministic loudness/peak/phase/sync checks. Clip
duration determines the qualified single- or multi-GPU envelope.

### Workflow engineering authority

Qwen3-Coder-Next is the target workflow diagnosis and patch-proposal service.
It receives workflow JSON, node schemas, installed inventories, logs, defect
JSON, resource limits, previous attempts, and approved patch points. It returns
a proposal only. Deterministic services validate nodes, connections, types,
paths, models, ranges, resources, schema, and regression scope before sandbox
generation. It has no shell, credential, promotion, Tracker, or Git authority.

### Golden-mask authority

The target pool combines admitted SAM-family grounding/tracking, SAM2Matting,
MatAnyone2, PDFNet, BiRefNet HR-Matting, MODNet, and Robust Video Matting through
MaskFactory contracts. The controller generates multiple proposals, calculates
disagreement and uncertainty, refines only uncertain regions, validates overlays
and temporal behavior, and packages mask, alpha, target binding, metrics, model
hashes, and rollback lineage.

## Modality pipelines

### Image

Validate decode, dimensions, color/alpha, compression, prompt/reference
lineage, perceptual metrics, identity/landmark evidence when applicable, and
approved crops. Strict review covers anatomy, hands, identity, materials,
lighting, geometry, background, seams, and prompt adherence.

### Video and GIF

Validate container, codec, duration, frame rate, frame count, decode, audio
presence, and sampled-frame hashes. Measure motion, optical-flow consistency,
flicker, temporal identity, scene continuity, object persistence, and boundary
stability. Review representative frames, transitions, worst-metric spans, and
the full clip only within the certified context/VRAM envelope.

### Audio and audiovisual

The current tier is deterministic unless a semantic audio model has a current
qualification certificate. Validate codec, duration, channels, sample rate,
true peak, clipping, LUFS, DC offset, silence, discontinuities, phase, expected
script/ASR alignment when an ASR certificate exists, and AV event offset.
NISQA, DNSMOS, CLAP, speaker embeddings, forced alignment, and omni-modal judges
remain optional gates that must identify their exact implementation and scope.

### Golden masks

MaskFactory or another admitted producer may supply candidate masks and alpha
mattes. Validate dimensions, target-instance binding, binary/alpha semantics,
foreground completeness, leakage, topology, boundary distance, fine structures,
occlusion consistency, and temporal stability. SAM, matting, or refinement
models remain proposals until exact producer and evaluator certificates exist.
Model consensus is evidence of disagreement, not automatic ground truth.

### Workflow review and correction

Before execution, validate JSON/schema, graph connectivity, input/output types,
installed custom nodes, exact model and LoRA identities, engine compatibility,
paths, sampler/scheduler/CFG/step/denoise limits, mask bindings, output capture,
and predicted VRAM. Bind runtime errors and QA defects to graph nodes and
approved patch points. Patch a candidate graph, run static validation and one
bounded sandbox generation, compare with the accepted graph, then promote or
revert through the same evidence policy used for media artifacts.

## Bounded correction policy

- Preserve the accepted parent and immutable baseline before every repair.
- Repair only the failed region, frame span, audio span, or workflow parameter
  set when lineage permits targeted correction.
- Default ceiling: two repair attempts for one defect category.
- Default global ceiling: four total generation attempts per job.
- Stop after two consecutive no-progress cycles.
- A candidate is retained only when the applicable weighted score improves,
  every hard gate passes, and no protected category materially regresses.
- Otherwise revert to the accepted parent and emit `REJECT`, `BLOCKED`, or
  `HUMAN_EXCEPTION_REQUIRED` with typed reasons.
- Exhaustion never changes thresholds and never becomes PASS.

## Evidence, replay, and promotion

Every decision binds the job contract, source and candidate hashes, workflow
hash, model/component hashes, reviewer digest, prompt/rubric versions,
deterministic measurements, repair history, runtime/pod identity, cost and VRAM
observations, decision, and rollback parent. Raw evidence is append-only.

S3 remains an artifact/evidence store. Promotion requires a content hash and a
manifest; bucket presence alone is not proof of deployment or QA. GitHub branch
presence, a worker statement, a generated file, or a successful process exit is
also not product acceptance.

## Security and cost controls

- Secrets remain in process/credential stores and are never written to Plans,
  receipts, prompts, logs, tests, tracker notes, or worker packets.
- Reviewer and repair services receive only allowlisted tools and paths.
- Model cards, prompts, metadata, archives, and generated text are untrusted.
- New paid endpoints, downloads, or pod resizing require an explicit cost
  decision and a reversible rollout plan.
- Record pod cost, run duration, storage target, and unexpected overlay growth.
- Fail closed on missing hashes, unknown model identity, invalid JSON, stale
  calibration, unavailable reviewer, queue conflict, or budget exhaustion.

## Implementation and activation sequence

1. Land this static package, schema, registry, validator, Items, and Tracker.
2. Validate the currently installed P0-P2 inventory and exact digests.
3. Build calibrated known-good, known-bad, borderline, and refusal fixtures.
4. Shadow the controller without artifact promotion.
5. Prove targeted repair, revert, attempt ceilings, and crash recovery.
6. Qualify image and sampled-video scopes for the current 32B reviewer.
7. Qualify deterministic audio/AV gates; add semantic audio only after evidence.
8. Admit MaskFactory contracts and golden-mask fixtures without cross-repo writes.
9. Qualify the workflow diagnosis/patch service and sandbox regression suite.
10. Evaluate an independent juror only if it adds measured value within budget.
11. Qualify semantic audio/AV roles and duration-specific capacity envelopes.
12. Provision on-demand multi-GPU primary/arbitration endpoints only after an
    explicit capacity and cost decision.

## Pursuing-goal strategy

The active project loop is: reconstruct repository and runtime truth; select the
highest-value dependency-unblocked row; preserve dirty ownership; implement a
bounded increment; run exact validators and runtime proof appropriate to the
claim; record truthful evidence; commit and push exact paths; recompute the
dependency graph; continue on another lane when one blocks. One successful run,
queued request, planned model, or blocked row is never project completion.

## Definition of done

The static package is done when all W64-AQA IDs agree across Plan, Items,
Tracker, requirements, registry, schema, Instructions, and tests. Runtime
completion additionally requires reproducible calibration, failure-injection,
recovery, resource, cost, security, drift, and modality evidence for every role
claimed active. Until then, unqualified roles remain blocked and the project
continues through other actionable rows.
