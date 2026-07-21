# Wave64 RunPod Autonomous Multimodal QA and Bounded-Correction Master Plan

Updated: 2026-07-21 America/Chicago
Program ID: `W64-AQA`

## Decision

The project will use a fail-closed, evidence-producing QA controller rather than
one unrestricted "master LLM." Every required Qwen, InternVL, Omni, Coder,
generation, QA, and golden-mask role is targeted to one self-hosted RunPod. The
current RTX 6000 Ada 48 GB pod remains authoritative during migration. The
preferred budget target is one pod with 2x A40 GPUs (96 GB aggregate VRAM,
at least 100 GB RAM and 18 vCPU); the performance fallback is one RTX PRO 6000
Blackwell 96 GB pod with at least 124 GB RAM and 32 vCPU. The controller runs
roles sequentially and may unload, reload, tensor-parallelize, quantize, or
CPU/NVMe-offload models under an exclusive phase lease.

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

### Tier P4: large-model role qualification

Qwen3.5 122B/397B, InternVL 241B, Qwen3-Omni, and Qwen3-Coder-Next are installed
to durable primary-pod storage and evaluated one at a time with checkpoint-
specific quantization and CPU/NVMe offload. No large role is operational merely
because its files exist: the exact quantization must pass memory, latency,
structured-output, calibration, and quality floors. A capacity failure leaves
that role blocked. A secondary 48 GB pod may accept an independently packaged
burst phase after its per-job budget gate passes; the design does not pretend
that aggregate VRAM behaves as one allocation: the 2x A40 target requires an
exact same-host tensor-parallel/NCCL topology certificate.

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
is reserved for missing licensed assets, setting or changing paid burst limits,
subjective intent changes, policy exceptions, and genuinely unresolved adjudication.

## Target self-hosted service topology

The best architecture is a pool of isolated role packages with one deterministic
policy authority on one pod. Packages load on demand and are never assumed to
be resident together. The current pod is replaced only after the candidate
one-pod profile passes storage, runtime, role, rollback, and cost canaries.

### Controller and fast planner

A qualified Qwen3.6-35B-A3B-class service is the target request compiler,
triage reviewer, correction planner, and route explainer. On the current pod it
requires a measured quantized exclusive-phase deployment. Until then, installed
small models provide bounded triage and deterministic code owns decisions.

### Primary visual reviewer

The current `qwen2.5vl:32b` strict lane remains active while a quantized/offloaded
Qwen3.5-122B-A10B package is installed and evaluated as the high-accuracy primary
reviewer on the existing pod. It must demonstrate enough calibrated improvement
to justify its latency, storage, memory, and cost.

### Independent visual juror

InternVL3.5-241B-A28B is the target independent review package. It is tested on
the existing pod through an exact quantized/offloaded envelope and remains
blocked if that envelope cannot meet the declared latency and quality floors.
Disagreement is preserved and arbitrated rather than averaged.

### Senior visual arbitration

Qwen3.5-397B-A17B is the senior target for borderline masters, persistent
anatomy/identity failures, complex temporal defects, or reviewer disagreement.
Its primary-pod package may use a qualified lower precision plus CPU/NVMe
offload, and it never reviews every candidate. If the exact package cannot meet
capacity or quality floors, senior arbitration remains blocked; no smaller model
inherits its authority. The 2x A40 profile may use same-host tensor parallelism;
the single 96 GB Blackwell profile uses contiguous VRAM. Both must independently
prove the exact senior quantization/offload package and acceptable latency.

### Audio and audiovisual authority

Qwen3-Omni-30B-A3B-Thinking is the target semantic audio/AV judge, paired with
Qwen3-ASR, forced alignment, NISQA, DNSMOS, CLAP, speaker embeddings, onset and
event detectors, and deterministic loudness/peak/phase/sync checks. Clip
duration determines the qualified sequential/offload envelope on the primary pod.

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
Every external package first compiles into a read-only consumer contract binding
the exact source, candidate, integration-accepted golden, target overlay,
geometry, and target instance. That contract is candidate-only and cannot grant
MaskFactory write, runtime, golden-reference, or promotion authority.

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
- Model downloads and pod migration require an exact storage/cost receipt and a
  reversible rollout plan. The current pod stays intact until the candidate
  one-pod profile passes canary and rollback gates.
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
8. Admit MaskFactory contracts and golden-mask fixtures without cross-repo writes;
   bind exact source, candidate, accepted-golden, and overlay artifacts while
   retaining candidate-only/no-promotion authority.
9. Qualify the workflow diagnosis/patch service and sandbox regression suite.
10. Install and independently qualify the primary and InternVL juror packages on
    the existing pod using measured quantization/offload envelopes.
11. Qualify Omni, ASR, Coder, and golden-mask roles independently by modality,
    duration, resolution, memory, latency, and quality scope.
12. Canary a one-pod 2x A40 profile first and a single 96 GB Blackwell profile
    only if A40 capacity/latency fails; migrate after volume, tensor topology,
    model residency, failure recovery, cost, and quality-equivalence gates pass.

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
