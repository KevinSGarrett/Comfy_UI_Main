# Wave64 RunPod Autonomous Multimodal QA and Bounded-Correction Master Plan

Updated: 2026-07-21 America/Chicago
Program ID: `W64-AQA`

## Decision

The project will use a fail-closed, evidence-producing QA controller rather than
one unrestricted "master LLM." Every required Qwen, InternVL, Omni, Coder,
generation, QA, and golden-mask role is targeted to the existing self-hosted
production RunPod `1q4ji0gg1fkhvt`. This RTX 6000 Ada 48 GB pod is the sole
deployment target until the user explicitly changes that decision. Alternative
pod migration, 2x A40 stock checks, candidate creation, and migration holds are
retired. The controller runs roles sequentially and may unload, reload,
quantize, or CPU/NVMe-offload models under a shared-coordinator phase lease.
Large roles are not deferred for different hardware: each receives an exact
current-pod package, capacity canary, quality calibration, and bounded operating
envelope before authority.

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
that role unqualified while a safer precision, quantization, sharding, or
CPU/NVMe-offload envelope is tested on the same production pod. No secondary
pod, external inference service, or future-hardware wait is part of the active
strategy.

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

The active architecture is a pool of isolated role packages with one
deterministic policy authority on the current production pod. Packages load on
demand and are never assumed to be resident together. No replacement-pod,
2x-A40, or external-inference branch is active: oversized roles must first use
exact quantization, bounded context, sequential unload/reload, and CPU or NVMe
offload on this pod. A failing role remains unqualified but does not stop other
dependency-unblocked current-pod roles.

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
inherits its authority. On the current production pod it must use an exact
quantized and CPU/NVMe-offloaded package with measured peak VRAM, host RAM,
latency, cleanup, and quality behavior.

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

The first real retained image shadow is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_IMAGE_SHADOW_20260721T223341Z.json`.
Its 1024x1024 artifact and historical lineage/review records match by hash, and
all deterministic gates pass. Whole-image Codex QA nevertheless rejects the
candidate: the hand remains on the shoulder/top sleeve rather than the requested
lower upper arm, and the contact shadow is not clear. The exact installed 32B
digest has passed a coordinator-admitted load, missing-media refusal, and clean
unload canary. It has not reviewed this artifact or passed image-quality
calibration. Product promotion remains false.

### Video and GIF

Validate container, codec, duration, frame rate, frame count, decode, audio
presence, and sampled-frame hashes. Measure motion, optical-flow consistency,
flicker, temporal identity, scene continuity, object persistence, and boundary
stability. Review representative frames, transitions, worst-metric spans, and
the full clip only within the certified context/VRAM envelope.

The first real retained video shadow is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_VIDEO_SHADOW_20260721T224034Z.json`.
The lossless 480x640 24 fps source fully decodes as 49 frames; all 24 sampled
frame hashes are retained, duplicate fraction is zero, motion is positive, and
exposure/sharpness gates pass. The hash-bound frames 0/12/24/36/48 contact sheet
shows stable gross subject, wardrobe, framing, and background structure. It is
not a whole-clip motion or temporal-identity review. The bound 32B model's
generic runtime canary passes, but sampled-video calibration and this artifact's
strict review have not executed, so product promotion remains false.

### Audio and audiovisual

The current tier is deterministic unless a semantic audio model has a current
qualification certificate. Validate codec, duration, channels, sample rate,
true peak, clipping, LUFS, DC offset, silence, discontinuities, phase, expected
script/ASR alignment when an ASR certificate exists, and AV event offset.
NISQA, DNSMOS, CLAP, speaker embeddings, forced alignment, and omni-modal judges
remain optional gates that must identify their exact implementation and scope.

The first real retained audio shadow is now bound at
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AUDIO_SHADOW_20260721T221732Z.json`.
The tracked 2.04-second 48 kHz stereo production mix matched its delivery
manifest and passed all eleven deterministic contract/signal gates: full decode,
sample rate, channel count, duration, loudness, clipping, DC offset, silence,
true peak, stereo phase, and duplicate-segment checks. Its rendered waveform and
spectrogram were inspected only as technical diagnostics. No listening, ASR,
speaker, event-semantic, perceptual, or independent-juror authority is claimed;
therefore product promotion remains false and the semantic audio gate stays
`BLOCKED_UNQUALIFIED`. This lane is non-GPU and does not compete with a
MaskFactory GPU lease.

The paired lossless AV review mux is retained at
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AV_SHADOW_20260721T222452Z.json`.
Its FFV1 video and PCM stereo audio fully decode, and both stream-start and
audio/video duration deltas measure 0 ms. A decoded 1.20-second frame was
inspected for gross structure only. Strict motion/continuity review, listening,
semantic AV sync, and independent-juror approval did not execute, so this second
real shadow also remains evidence-only and cannot promote product.

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
Producer-side masking remains exclusively owned by MaskFactory task
`019f4cfc-60c3-7500-8626-261dcf70db5d`. W64-AQA-007 is deferred until that task
publishes a versioned integration release with exact model/artifact hashes,
schemas, target semantics, runtime envelopes, qualification evidence, fixtures,
licensing/provenance, and rollback instructions. Non-mask lanes continue.

### Workflow review and correction

Before execution, validate JSON/schema, graph connectivity, input/output types,
installed custom nodes, exact model and LoRA identities, engine compatibility,
paths, sampler/scheduler/CFG/step/denoise limits, mask bindings, output capture,
and predicted VRAM. Bind runtime errors and QA defects to graph nodes and
approved patch points. Patch a candidate graph, run static validation and one
bounded sandbox generation, compare with the accepted graph, then promote or
revert through the same evidence policy used for media artifacts.

The first retained workflow-inspection shadow is
`Plan/Tracker/Evidence/W64_AQA_WORKFLOW_RECEIPT_BOUND_SHADOW_20260721T231000Z/evidence.json`.
Four distinct qualified `artifact_read` receipts bind the exact workflow,
object-info snapshot, immutable verified contract, and model inventory before
the graph validator runs. The synthetic graph passes node, edge, model, path,
range, output, and acyclicity checks. This is static inspection only: no
RunPod contact, ComfyUI sandbox, candidate write, model inference, Coder
proposal authority, or product promotion occurred. Those capabilities remain
separately unqualified and cannot inherit authority from this PASS.

The next retained qualification at
`Plan/Tracker/Evidence/W64_AQA_WORKFLOW_LOGICAL_TOOL_QUALIFICATION_20260721T232000Z/evidence.json`
executes exactly two logical actions against that same four-receipt bundle:
`workflow_inspect` for `workflow.graph` and `validator_run` for
`validate.workflow.v1`. Both recompute the gateway decision, bind the contract
and job, enforce the separate shadow-only executor policy, return the same
receipt-bound static PASS, and retain zero content, sandbox, target-write,
network, runtime, or promotion claims. Other validator targets and production
mode remain denied.

The retained local transaction at
`Plan/Tracker/Evidence/W64_AQA_WORKFLOW_CANDIDATE_STAGING_20260721T232803Z/evidence.json`
then admits one exact `candidate_write` target, verifies the four input receipts,
applies a typed bounded patch, and publishes a new immutable candidate without
altering the base workflow. Overwrite, path aliasing, policy weakening, invalid
patch, elapsed-limit, publish-crash, and source-race cases fail closed. This is
candidate staging only: RunPod, GPU, ComfyUI sandbox execution, model inference,
regression replay, Coder authority, production write, and promotion remain
unqualified pending an owned phase lease.

## Bounded correction policy

- Preserve the accepted parent and immutable baseline before every repair.
- The retained Row011 fixture at
  `Plan/Tracker/Evidence/W64_AQA_CORRECTION_TRANSACTION_20260722T000248Z/evidence.json`
  binds the exact candidate-staging, deterministic-measurement, and synthetic-
  sandbox receipts. It injects a crash after immutable state publication,
  resumes by exact reuse, completes an immutable receipt, and replays exactly.
  The non-improving candidate reverts to the accepted parent. This proves
  transaction recovery only; ComfyUI/runtime measurement and promotion remain
  false until the owned current-pod E2E run.
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

The retained receipt at
`Plan/Tracker/Evidence/W64_AQA_S3_OBJECT_STAGING_RECEIPT_20260721T233801Z.json`
qualifies one Codex-authority content-addressed object stage to the configured
versioned bucket. Conditional create, SHA-256 checksum replay, AES-256 server-
side encryption, metadata, version ID, and `HeadObject` verification pass. No
overwrite or delete occurred, and S3 presence granted no product promotion.
Bucket public-access-block inspection remains unavailable to the session role,
so production bundle promotion stays unqualified.

The live qualification at
`Plan/Tracker/Evidence/W64_AQA_S3_BUNDLE_TRANSACTION_20260721T234740Z/evidence.json`
stages nine unique records and writes the bundle manifest last. All ten objects
pass conditional creation, checksum, encryption, metadata, version, and head
verification. A second execution creates zero objects and verifies/reuses all
ten, proving restart-safe idempotence. The bundle decision is deliberately
`BLOCKED`; no RunPod, GPU, ComfyUI, semantic review, overwrite, delete, or
promotion claim is made.

Commit `372bc28ac1af30a496da71c72bb1dac6308b1993`, which contains the retained
bundle evidence, is named by a separate content-addressed S3 binding object.
Its conditional-create receipt verifies checksum, AES-256, version, length, and
head replay. The binding is evidence lineage only and grants no acceptance.

## Security and cost controls

- Secrets remain in process/credential stores and are never written to Plans,
  receipts, prompts, logs, tests, tracker notes, or worker packets.
- Reviewer and repair services receive only allowlisted tools and paths.
- Model cards, prompts, metadata, archives, and generated text are untrusted.
- Model downloads and package activation require exact storage/cost receipts
  and reversible package-level rollout. The current pod remains authoritative;
  no alternate-pod migration gate or hardware-availability wait is active.
- Record pod cost, run duration, storage target, and unexpected overlay growth.
- Fail closed on missing hashes, unknown model identity, invalid JSON, stale
  calibration, unavailable reviewer, queue conflict, or budget exhaustion.

The model-facing tool gateway remains decision-only. The first independently
qualified executor action is `artifact_read`, and its scope is deliberately
narrow: it recomputes the exact admission decision and policy hashes, accepts an
integration-authority-supplied job root, rejects path escapes, sensitive names,
secret-like content, symlinks and Windows reparse points, enforces a 16 MiB
and five-second elapsed guard, verifies file identity before/open/after, and
emits only a SHA-256, byte count, and immutable receipt. It never returns
artifact bytes, writes the target, or uses a network. The retained qualification receipt is
`Plan/Tracker/Evidence/W64_AQA_TOOL_EXECUTOR_QUALIFICATION_20260721/receipt.json`.
Every write, validator, workflow-inspection, generation, shell, Git, cloud,
Tracker, promotion, or network action remains unqualified and fail-closed until
it receives a separate bounded executor and fault campaign.

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
12. Qualify every remaining role on the current production pod using one-resident-
    GPU-role scheduling, exact quantization/offload envelopes, cleanup proof, and
    measured quality; never wait for or create an alternative pod.

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

The infrastructure phase exits earlier and without weakening those role gates:
one retained current-pod shadow job must pass admission, workflow execution or
generation, deterministic and contract-applicable semantic QA, one bounded
correction, evidence replay, owned cleanup, and fail-closed evidence-only
acceptance. Remaining unqualified required roles and deferred MaskFactory
integration stay explicit tracker limitations, but neither blocks other
current-pod lanes. After this exit, selection
defaults permanently to dependency-unblocked functional ComfyUI delivery rather
than another broad infrastructure or inventory cycle.

The exit gate passed on 2026-07-22. A first current-pod runtime packet was
retained but integration-rejected because independent visual review caught a
3:4 source forced into a distorted 1:1 candidate despite deterministic PASS.
The corrected square-source packet then passed shared admission, current-pod
ComfyUI execution, one bounded correction, deterministic QA, applicable semantic
scope handling, independent visual review, evidence replay, owned cleanup, and
fail-closed evidence-only acceptance. It grants no product, generative-model,
identity, or image-quality authority. The default project lane is now functional
ComfyUI delivery; remaining model qualifications are advanced as explicit gates
for real output milestones rather than as another broad setup cycle.

## Role package identity and current-production-pod capacity lane

The authoritative package inventory is
`Plan/10_REGISTRIES/wave64_runpod_autonomous_role_package_inventory.json`.
It separates official upstream identity, installed local digest, activation,
qualification, and operational authority. A repository name or upstream license
never implies that weights were downloaded, accepted, hashed, capacity-tested,
or authorized. The concrete ASR target is `Qwen/Qwen3-ASR-1.7B`; the generic
family label `Qwen3-ASR` is not an install target.

No alternative-hardware watcher or migration candidate is active. The existing
pod remains authoritative and continues sequential unload/reload/offload
qualification. The shared coordinator serializes Comfy_UI_Main and MaskFactory
GPU phases; CPU-only installation, hashing, static validation, and evidence work
continue without a GPU lease. Every package requires an independent current-pod
capacity, runtime, calibration, quality, cleanup, and failure certificate.

The first admitted missing package is `Qwen/Qwen3-ASR-1.7B` at verified
revision `7278e1e70fe206f11671096ffdd38061171dd6e5`. Its two weight-shard
SHA-256 identities, exact byte envelope, immutable `/workspace` target, license
decision, and storage-only authority are bound in
`wave64_runpod_qwen3_asr_17b_install_admission.json`. Admission is not
installation: download, model load, inference, activation, service changes,
lease polling, and product authority remain false until separately evidenced.

The storage installer is `install_wave64_runpod_model_package.py`. It pins the
admission manifest's canonical SHA-256, enforces the free-space floor, resumes
only inside a private revision-named staging directory, verifies small files by
Git-blob identity and weights by SHA-256, rejects symlinks and extra files, and
publishes by atomic no-overwrite rename. A completed target is reusable only
after its receipt and every file reverify. The installer imports no model or GPU
library and exposes no load, inference, service, lease, or activation action.

The current pod now contains the exact Qwen3-ASR file set at the admitted
revision. The first install and a verification-only replay passed; the retained
remote receipt mirror is byte-identical to the pod receipt. This proves storage
installation only. It does not prove that runtime dependencies import, the model
fits or loads, transcription is correct, latency or cost is acceptable, faults
recover, or the ASR role can participate in a product decision.

The next gate is a metadata-only dependency preflight. It may read the admitted
model configuration, Python version, installed distribution metadata, and the
installed Transformers file manifest. It must not import Torch, Transformers,
Qwen-ASR, construct a model, allocate a tensor, inspect CUDA, poll the GPU lease,
or access the network. Missing support is a typed dependency action, not a model
failure. Any dependency remediation must use a separately admitted immutable
isolated environment and may not mutate the active ComfyUI environment.

The pushed metadata-only preflight ran on the current pod and passed all four
model/config identity assertions. It found the active environment has Python
3.11.10, Torch 2.4.1+cu124, and Transformers 4.46.3, but no `qwen-asr`
distribution and no installed Transformers Qwen3-ASR support files. Therefore
the file set remains installed and non-operational. The admitted next step is a
hash-locked isolated dependency environment; the active ComfyUI environment is
not an upgrade target.

The official minimal Transformers dependency closure is resolved and hash
locked for Python 3.12.13, Linux x86-64, and CUDA 12.4. The lock contains 105
packages and 109 SHA-256-bound wheels from only PyPI's file host and the
official PyTorch wheel host. It pins `qwen-asr==0.0.6`,
`transformers==4.57.6`, and `torch==2.4.1+cu124`; vLLM and FlashAttention are
deliberately absent. Build authority is limited to a new immutable environment
under `/workspace/w64_aqa`; it cannot mutate active ComfyUI or claim imports,
GPU access, model load, inference, activation, or product authority.

That exact isolated environment is now atomically published on the current pod.
It contains Python 3.12.13 and exactly 105 compatible distributions; its 5.96 GB
tree is retained by SHA-256. The active ComfyUI metadata signature before and
after the build is identical. The initial inline metadata check had a quoting
error after installation, so acceptance used an independent stdin-delivered
metadata check; the correction changed no installed bytes. This completes only
the dependency-environment gate. Import, model construction, GPU, weights,
inference, role activation, and product decisions remain unqualified.

The import-only canary is independently bounded before execution. It must run
from the immutable environment with CUDA hidden, Hugging Face and Transformers
offline, bytecode writes disabled, and an audit hook that rejects network,
subprocess, shell, and model-weight file opens. Its only positive authority is
to import the isolated Qwen-ASR, Transformers, and Torch libraries and resolve
the four required class objects. Model construction, tensor requests, weight
access, GPU or lease polling, inference, services, activation, and product
authority remain false.

The first live canary attempt failed closed after recording one unconnected
IPv6 socket-construction event; all four required imports nevertheless
completed. The audited arguments prove this was `socket.__new__` only, not
connect, bind, DNS, listen, send, or receive. The corrected policy records
socket construction as a non-I/O capability probe while continuing to reject
every audited network-I/O action. This correction requires a new pushed canary
and does not retroactively accept the first attempt.

The next pushed attempt also failed closed, this time on `socket.bind`. An
independent outer audit retained its exact arguments: IPv6 loopback `::1`,
ephemeral port `0`, stream socket. The final policy recognizes only IPv4 or
IPv6 loopback at port zero as a recorded local capability probe. Wildcard,
external, malformed, and fixed-port binds remain rejected, as do every
connect, DNS, listen, send, subprocess, shell, and weight-file event.

The commit-addressed rerun passed. Qwen-ASR, Transformers, and Torch imported,
and all four required Qwen3-ASR classes resolved. The receipt records one
socket-construction event, one exact loopback/ephemeral bind probe, zero
blocked side-effect events, and zero weight opens. The full 28,403-file,
5.96-GB environment tree retained the exact pre-canary digest
`6625aa3c76c411424ede40ce6275d0fb378a1d9a017c205f74ffd356386f7c4a`.
This closes only the import gate. Model construction, weights, tensors, GPU and
lease access, transcription, alignment, semantic quality, capacity, runtime,
latency, cost, recovery, activation, and product authority remain unqualified.

The repository already contains the authoritative Apache-2.0 project-use
decision in the pinned install admission. The verified storage receipt binds
all twelve source files, including both safetensor shards at their exact
SHA-256 values, to the admitted manifest and revision. A retained static
qualification certificate now closes the license-decision and artifact-hash
gates without contacting the pod or GPU. Capacity, language calibration,
runtime, quality, cost, failure recovery, activation, and product authority
remain open.

The first functional Qwen3-ASR runtime gate is now accepted at exact-fixture
scope. Under an exclusive shared-coordinator lease, revision `7278e1e` loaded
offline, transcribed retained audio SHA-256 `5a07f0a6...d924a` as
`Once upon a midnight.`, identified English, and exited back to within +5 MiB
of the parent's pre-worker GPU baseline. The original worker-local cleanup
measurement saw 3,810 MiB of CUDA context residency and failed; that receipt is
retained. Commit `0854c5b7` corrected the evidence boundary by isolating CUDA
work in a child and measuring again only after child exit, without changing the
model, audio, phrase, or threshold. This closes current-pod capacity, exact
fixture transcription, runtime, and cleanup only. General ASR quality,
language/duration calibration, forced alignment, audio semantics, AV review,
cost, fault injection, activation, and promotion remain open. The next bounded
functional gate is Qwen3-Omni audio-semantic review of the same retained
fixture under a new exclusive lease.

The next non-GPU admission targets Qwen3-Omni-30B-A3B-Thinking as the planned
audio and audiovisual semantic reviewer. Official metadata pins revision
`2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b`, 26 source files, and sixteen
SHA-256-bound safetensor shards totaling 63,440,997,640 bytes. The model card
uses `license_name: apache-2.0`, and the official Qwen3-Omni repository carries
the Apache-2.0 license. The current pod reported 145,773,754,646 free workspace
bytes, exceeding the 79,547,125,000-byte admission floor.

This is storage authority only. The generic installer is now bound to both the
existing Qwen3-ASR manifest and this exact Omni manifest; no arbitrary
repository or revision is admitted. The official current runtime recommendation
of Transformers 5.2 or later must be handled in a later immutable isolated
environment. Download, import, quantization, model load, GPU, lease, inference,
audio/AV authority, activation, and product decisions are not implied by this
admission.

The first Omni storage invocation used the installer default of one download
worker. It was intentionally interrupted after retaining 4,357,229,845 staging
bytes because the observed single-stream rate would make the bounded gate
unnecessarily long. No target or receipt was published, and no GPU or lease
action occurred. The installer now supports one through eight download workers
while preserving serial mode as the default. Parallel mode keeps one distinct
path per task and returns verified receipt records in manifest order. The
production resume is bounded to four workers and reuses verified files and the
existing range-resumable partial shard.

The four-worker resume completed and atomically published the exact Omni
revision. All 26 source identities and sixteen shard SHA-256 values passed; a
second existing-target replay returned `REUSED_VERIFIED_INSTALL`. The durable
directory contains 27 regular files including its receipt, zero symlinks, and
63,450,501,064 bytes. This closes storage and artifact-hash gates only. The
model remains unloaded and has no GPU, lease, inference, semantic review,
activation, or product authority.

The Omni dependency preflight is now implemented but not yet executed. It reads
only `config.json`, `preprocessor_config.json`, Python distribution metadata,
and the installed Transformers file manifest. It verifies the top-level model,
architecture, processor, thinker, audio, vision, text, and revision identities.
It cannot import model libraries, open weights, allocate tensors, inspect GPU
or lease state, use the network, or start a process. Any missing Transformers
5.2-plus or Qwen-Omni support becomes a typed isolated-environment action.

The pushed preflight executed successfully. All eight configuration and
revision assertions passed. The active Python 3.11.10 environment has Torch
2.4.1+cu124 and Transformers 4.46.3, but lacks Qwen-Omni Utils and contains no
Qwen3-Omni support paths. The active environment remains unchanged. This
authorizes only resolution of a hash-locked isolated Transformers 5.2-plus
environment; import, weights, GPU, lease, inference, and authority remain false.

The isolated Omni dependency closure is resolved, corrected, built, and
metadata-verified. Its Pylock contains 75 packages and 78 SHA-256-bound wheels
from only `files.pythonhosted.org` and `download-r2.pytorch.org`. It pins
Transformers 5.2.0, Qwen-Omni Utils 0.0.9, Accelerate 1.14.0, Torch
2.4.1+cu124, and TorchVision 0.19.1+cu124. The optional Decord 0.6.0 extra was
removed after `uv pip check` proved its published wheel's internal tag is
CPython 3.6 only. vLLM and FlashAttention remain excluded. The verified Python
3.12.13 runtime is reuse-only and active ComfyUI was not modified.

The corrected lock-addressed build contains 75 compatible distributions,
23,097 regular files, four symlinks, and 5,749,106,791 regular-file bytes at
tree SHA-256 `2ae7708993cab848861688ae1b89a2233d61fa02b49e1c14bf51b188a2dd59c5`.
Direct compatibility validation and full replay pass, and the active Python
metadata signature is identical before and after. No model library was
imported, no weights were opened, and no tensor, GPU, lease, inference,
service, semantic, activation, or product authority is claimed. The next safe
gate is a separately admitted import-only canary from a pushed commit.

The separately admitted CPU-only import canary then passed from pushed commit
`6a1fa04b`. Qwen Omni Utils, Transformers, Torch, and TorchVision imported and
the exact Qwen3-Omni config, processor, and conditional-generation classes
resolved in 26.877 seconds with a 495,255,552-byte RSS increase. CUDA was
hidden, network and weight-file operations were blocked, the GPU lease was not
polled, and the full post-canary environment replay retained tree SHA-256
`2ae7708993cab848861688ae1b89a2233d61fa02b49e1c14bf51b188a2dd59c5`.
No model construction, weights, tensors, inference, semantic authority,
activation, or product authority is implied. Runtime qualification remains a
typed GPU-lease hold while independent-juror source qualification continues.

The independent-juror source lane selected the official native Transformers
InternVL3.5-241B-A28B-HF repository. Revision `b941ed62...` has no custom
Python files or `auto_map`, so `trust_remote_code` is now forbidden. Its
136-file manifest, all 97 weight-shard hashes, Apache-2.0 weight metadata, and
the official project's MIT code license are pinned and accepted for project
use. The raw source is 481,433,908,402 bytes and fits the current pod's latest
filesystem-reported 142,706,362,155,008 free bytes. The same probe measured
540,844,122,112 total host-memory bytes, 438,214,877,184 available bytes, 128
CPUs, and 47,993 MiB free VRAM. The unquantized package leaves no safe runtime
headroom and is not admitted for loading. A reproducibly hash-locked
quantized/offloaded artifact, current-pod runtime-capacity proof, and durable
storage verification are the next juror gates while all other current-pod lanes
remain nonblocking.

## Current-pod promoted storage intake

The additive 2026-07-22 storage reconciliation accepted byte transfer for 56
live files totaling 55,804,915,269 bytes plus three hash-verified symlink
aliases. Source, staging, and live SHA-256 values are equal with zero reported
mismatches. The accepted live set includes Qwen3-TTS Base and VoiceDesign,
LAION CLAP, Kokoro, SDXL Base, Flux 2 Klein FP8, selected Wave42 generation
assets, and retained MaskFactory provenance manifests. This is storage authority
only; package identity, revision, license, dependency, capacity, runtime,
quality, cleanup, failure, cost, rollback, and product authority remain separate.

The first promoted package replay now closes exact storage identity for
Qwen3-TTS 12Hz 1.7B Base only. The live directory contains exactly 11 regular
files and 4,544,170,364 bytes, with no extra member; an independent current-pod
SHA-256 replay matched every transfer-ledger entry, including main weight
`38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c`
and speech-tokenizer weight
`836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`.
The package is bound to official revision
`fd4b254389122332181a7c3db7f27e918eec64e3` and Apache-2.0 metadata from the
canonical asset catalog. No dependency environment, model load, synthesis,
voice cloning, speaker identity, operational activation, or product promotion
follows from this storage result.

The separate Qwen3-TTS 12Hz 1.7B VoiceDesign package also passed its own exact
live replay: 11 regular files and 4,520,159,099 bytes, with main weight SHA-256
`391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`.
It is independently bound to official revision
`5ecdb67327fd37bb2e042aab12ff7391903235d3`; shared tokenizer bytes do not merge
the Base and VoiceDesign authorities. This remains storage identity only, with
dependency, load, synthesis, designed-voice quality, speaker identity,
activation, and product authority false.

Kokoro 82M then passed an exact three-file, 327,738,002-byte live replay, but
its canonical repository revision, license, and complete provider manifest are
not bound in the current asset catalog. This is therefore only a partial
storage adoption. Filename-based provenance inference is forbidden; provider,
license, dependency, load, synthesis-quality, activation, and product authority
remain false while another provenance-complete package may continue.

Flux.2 Klein 4B FP8 is the next provenance-complete promoted storage package.
Its single regular 4,070,624,520-byte live file independently rehashed to the
published SHA-256
`97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6`
and binds immutable provider revision
`c30fa39e0d916333415ae96c66169d8cfdca3e63` plus Apache-2.0 metadata. Storage,
provider revision, published hash, and license metadata are accepted. Existing
license-acceptance authority, complete execution-bundle, load, generation,
activation, and promotion gates remain false and are not bypassed.

Two Wave42 UI workflows and their 75-file fixture tree remain inactive under
`/workspace/wave64_quarantine/aws_ec2_20260722`. Seventeen clean repositories at
exact EC2-recorded pins remain dependency-free and inactive under
`/workspace/custom_node_quarantine/aws_ec2_pins_20260722`. No quarantined path
may be linked into active ComfyUI until live `/object_info`, exact model and node
identities, fixture governance, isolated sandbox, regression, security, cleanup,
and rollback gates pass. The repository-backed disposition is
`W64-AQA-018`; transfer integrity may advance package qualification but cannot
mark any role or workflow operational.

The accessible-source Google Drive archive is also accepted as recovery
integrity, independently of RunPod activation. Its payload inventory contains
335 unique paths and Drive object IDs totaling 395,510,389,604 bytes; a full
machine parse found zero invalid sizes, invalid SHA-256 values, duplicate paths,
or duplicate object IDs. The accepted completed classes are 283 selected local
archive files and the 2,938-object S3 non-model archive. EC2 remains explicitly
partial: 51 Drive objects are retained, while 411 audited model files totaling
281,349,317,254 bytes remain on stopped `i-0560bf8d143f93bb1`. The instance must
not be terminated because its root volume has `DeleteOnTermination=true`.
Resume that archive only when g5 capacity exists or exact type-change authority
is granted. The separately approved stale F: Docker VHD rehashed equal to its
Drive object, but local execution policy rejected deletion before process start,
so the source remains present. Archive integrity grants recovery authority only,
not runtime, capacity, license, workflow, quality, cleanup-completion, or product
authority.

## Qwen3-Omni exact-fixture runtime disposition

The corrected current-pod Qwen3-Omni canary at revision
`2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b` loaded and executed successfully
against the retained audio SHA-256
`5a07f0a654499266509453421c3efdc1b2e4ce83b8706e0138ebc4b1d3ad924a`.
Its response had the exact required schema, recognized "Once upon a midnight",
and passed the exact-fixture intelligibility gate. Load took 364.702 seconds,
inference took 1,153.675 seconds, observed GPU use peaked at 37,762 MiB, worker
process exit returned GPU use to the 648 MiB baseline, and the temporary offload
directory was removed.

The run is `PARTIALLY_ADOPTED`, not operational. Immediate post-worker
`MemAvailable` was 31,923,978,240 bytes below the pre-worker observation, so
full lifecycle cleanup, general semantic-audio quality, ASR quality, forced
alignment, speaker identity, AV sync, independent-juror, and product authority
remain false. No unchanged high-cost rerun is allowed. A later Omni attempt must
first add non-destructive process-RSS, anonymous-memory, clean-file-cache,
cgroup-memory, and delayed-availability observations and must never drop caches
or touch foreign processes.

That prospective cleanup discriminator is now implemented before any rerun. It
captures global available/cache/reclaimable memory plus container-scoped
`memory.current`, anonymous, and file-cache counters before the child starts
and after it exits. Cleanup acceptance prefers return of cgroup current memory,
then return of anonymous memory with reclaimable file-cache retention, and only
then the legacy global-availability tolerance. If all scoped signals drift, the
result is `INDETERMINATE_SHARED_HOST_MEMORY_DELTA`, not a claimed process leak;
exact semantic and GPU-cleanup results remain separately visible while lifecycle
authority stays false. The probe is read-only, bounded to the canary invocation,
does not drop caches, and does not inspect, signal, or mutate foreign processes.

The promoted `laion/larger_clap_general` package at revision
`ada0c23a36c4e8582805bb38fec3905903f18b41` is now partially qualified. Its
exact 15-file, 777,702,854-byte package matches aggregate manifest SHA-256
`b35a1ac3fc7cf0ed32822667e85240b0620cba5ed65988c0a707445ef7e593cc`.
On the current pod it loaded in 0.910 seconds, produced finite 512-dimensional
audio and text embeddings in 0.574 seconds, repeated with maximum absolute
delta 0, and returned GPU use exactly to the 648 MiB pre-worker baseline after
process exit.

The predeclared speech-event gate failed truthfully: the retained mixed
speech-plus-sustained-tone fixture ranked `silence` above `a person speaking
clearly` with a 0.121600 margin. The result is retained without post-result
label tuning. Exact-package identity, bounded CUDA inference, embedding shape,
repeat determinism, and cleanup are accepted; speech-event recognition,
general audio semantics, alignment, speaker, AV-sync, juror, operational, and
product authority remain false. No unchanged rerun is allowed. The next audio
lane must prospectively bind clean-speech, tone-only, silence, and mixed
controls before forced-alignment or event-model execution.

## Wav2Vec2 exact-matrix forced-alignment disposition

The hash-bound `facebook/wav2vec2-lv-60-espeak-cv-ft` package at revision
`ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4` passed the frozen four-fixture
matrix on the current pod. Clean speech and speech plus tone each produced
greedy phoneme-token similarity `1.0`, complete monotonic transcript-bound
spans, and mean aligned-token posterior above `0.91`. Tone-only and silence
each produced similarity `0.0`, posterior below `0.003`, and correctly refused
the speech gate. The model loaded in 1.222 seconds, incremental GPU use peaked
at 1,842 MiB, and process exit returned to the 648 MiB baseline with delta `0`.

This result is `ADOPTED` for exact-package identity, current-pod load and
inference, this transcript-bound matrix, negative-control refusal, bounded
capacity, and GPU cleanup. It does not grant general forced alignment,
multispeaker or multilingual coverage, speaker identity, general audio
semantics, AV sync, viseme/lip-sync integration, operational activation, or
product promotion. The next bounded speech action is to bind the retained word
and phoneme spans into prospective viseme and lip-sync fixtures, then expand
calibration across speakers, accents, noise, duration, overlap, and transcript
mismatch before any broader authority claim.

The first expanded calibration package is now prospectively frozen. It binds
eight exact retained sources spanning a generated English speaker, a distinct
public-domain natural English speaker, Spanish, English-Spanish code switching,
room ambience, rights-scoped cloth/body-shift foley, a speech/foley/ambience
mix, and two-speaker overlap. Eight forced-alignment cases add natural-speaker,
language-scoped diagnostic, transcript-mismatch, overlap-refusal, ambience-
refusal, and foley-refusal coverage; four audio-event cases add calibration and
held-out label-family controls. Calibration partitions must run first, observed
thresholds must be frozen before held-out inspection, and unchanged reruns are
forbidden. This package grants exact-source admission and prospective case
binding only. General, multilingual, or overlap alignment, audio-event
recognition, independent listening, operational activation, and product
promotion remain false until their separate runtime and review gates pass.

The expanded Wav2Vec2 executor is also statically admitted. It reuses only the
previously accepted exact model and dependency environment, requires an exact
sanitized `comfyui_main` exclusive lease, and runs calibration and held-out
partitions as separate immutable worker processes. Held-out execution requires
a passing calibration receipt bound to the same plan and model revision.
Transcript mismatch must lose at least `0.15` greedy similarity relative to the
matched calibration source; nonspeech and overlap remain refusal controls; and
Spanish/code-switch results remain diagnostic with no language authority. The
executor is runtime-pending while the coordinator retains the foreign
MaskFactory recovery hold. Audio-event execution is intentionally excluded
until a separate exact event-model admission exists.

The MIT AST AudioSet fallback is now installed and byte-verified on the current
production pod at immutable Hugging Face revision
`f826b80d28226b62986cc218e5cec390b1096902`. The selected
`model.safetensors` is exactly `346404948` bytes with SHA-256
`ae0c1e2ad4e1381d851fa9bf298ba13ebc9c5a914cdee2dbe427a6583869924d`;
atomic installation and verified replay both passed without polling GPU or
lease state. This is a storage-identity adoption only. The official BEATs
AudioSet checkpoint remains separately blocked because its original-author
OneDrive download endpoints returned HTTP 403, and AST is not evidence of
BEATs equivalence. AST dependency activation, model load, inference,
calibration and held-out event recognition, independent listening review,
operational activation, and product promotion remain false. The next event
lane action is to admit an exact isolated AST dependency/load/event canary and
execute it only after the foreign coordinator recovery hold clears and an
exact sanitized `comfyui_main` lease is acquired.

That isolated AST canary is now statically admitted. It binds the exact six-file
installed package, the already accepted Python 3.12.13 / Torch 2.4.1 CUDA 12.4
/ Transformers 5.2.0 environment, the immutable four-case expansion plan, and
the retained WAV identities. Calibration and held-out partitions are separate
immutable executions; held-out measurement requires a passing calibration
receipt with the same plan and model identities. The runner is offline-only,
requires a sanitized exact `comfyui_main` exclusive lease, executes in a child
process, and fails closed on package, source, environment, lease, capacity, or
cleanup drift. Its calibration gate checks prospectively declared AudioSet
label families in the top three; held-out results are measurements only and do
not grant single-model authority. Execution remains pending while the foreign
MaskFactory coordinator recovery hold exists.

The prospective Row136 control package is now frozen before execution. It
binds the accepted canary receipt, a versioned English IPA-to-viseme registry,
an exact output schema, and a deterministic compiler. The compiler creates a
contiguous sample-level timeline with explicit inferred-silence gaps and a
single center-sample owner for every output frame; adjacent-viseme
coarticulation weights must remain bounded and normalized. It must compile both
accepted speech fixtures with identical ordered phoneme-to-viseme coverage
before exact-fixture authority is accepted. No rendered lip-sync, identity,
AV-sync, general inventory, operational, or product authority follows from a
control compilation.

Both frozen Row136 compilations passed. Each contains 59 contiguous sample
events, 77 single-owner frame controls, normalized adjacent-viseme blends, and
complete required category coverage. Clean speech and speech plus tone preserve
the identical ordered 30-token IPA-to-viseme sequence. Their maximum observed
aligned-boundary difference is 20.125 ms and 71 of 77 primary frame labels
agree; these are retained diagnostics, not retroactive promotion thresholds.
The exact two-fixture compiler is accepted, but rendered lip sync, identity
preservation, AV sync, general phoneme inventory, operational activation, and
product promotion remain false. The next bounded action is an isolated Row137
candidate using immutable source video/audio and the accepted control track,
followed by temporal, identity, frame-integrity, whole-video, cleanup, and
rollback QA.

Row137 has begun with an exact current-pod admission rather than an unpinned
workflow install. Official LatentSync code is pinned at commit
`a229c3948406bc2cf6eaf4873e662e70c6a04746`; the model package is pinned at
revision `c42c7e6c8e9c213626389fa7d9a3c444b8536353` with 13 exact files and
9,635,782,864 weight bytes. The current pod has sufficient published inference
VRAM; the storage-reconciliation estimate falls from 73.0 GiB to 64.026 GiB
after this package and remains above the 50 GiB safety margin. Shared-filesystem
`df` output is not billing or quota authority. No admitted model bytes or eligible face-video
fixture were present at preflight. The storage transaction is therefore
admitted first, with model load, code/dependency activation, inference, source
video, identity, AV sync, operational, and product authority all false.

The storage stage subsequently passed: all 13 files and 9,635,785,477 payload
bytes were verified, atomically published, and rehashed through a read-only
`REUSED_VERIFIED_INSTALL` replay. The retained receipt SHA-256 is
`35510125ed8716193501f8ee5175abb2bc5c34f1610e29bd782865f1e3099b7d`.
This advances only exact storage authority. Code checkout, isolated dependency
environment, source-video and identity fixture, model load, inference, visual
and temporal review, cleanup, rollback, operational activation, and product
promotion remain pending.

The official code checkout also passes exact detached HEAD/tree verification:
commit `a229c3948406bc2cf6eaf4873e662e70c6a04746`, tree
`51f62bc8aea02da92b1a349077cfb78d0456f742`, 124 tracked files and
10,801,107 bytes, with a clean worktree, no submodules, and no symlinks. No
project code was imported or executed. The unsigned-commit caveat remains; the
next gate is an isolated hash-locked dependency environment plus an immutable
rights-qualified face-video identity fixture.

The LatentSync Python 3.11/cu121 graph now passes exact dependency-lock
validation at 149 packages: lock `ac29c11ced5d4be9b22ff4c0fcec9a9d48361d9dfcb1996bf2fdd2a8526b9605`,
with 152 wheel entries, 129 source entries, and no missing artifact hashes. A
prior resolver output is explicitly rejected for two unhashed transitive
artifacts. Runtime installation remains blocked until three source-only
packages are built into retained, hash-bound wheels in a separately controlled
builder and the resulting isolated environment is admitted. In parallel, the
immutable rights-qualified face-video identity fixture remains required before
any model-load lease or inference.

The three source-only LatentSync dependencies now pass a separately admitted,
hash-locked wheel build. The retained wheelhouse contains exactly three files,
1,215,560 bytes, tree SHA-256
`139140835f9e003c87187ee9d1f81edd458474ffb00c128fb3d844b505680ff6`;
all archives pass metadata, RECORD, path, symlink, ZIP-integrity, and controller
replay checks. The global Python distribution signature stayed unchanged. This
does not use the receipt's logical filesystem free-byte value as billing or
volume-quota authority, and it does not grant runtime install, import, model,
inference, activation, quality, or product authority. The next gate is the
isolated cu121 runtime environment plus the immutable rights-qualified video
fixture.

The isolated LatentSync environment now passes after two retained fail-closed
install attempts exposed root-cache placement and the upstream decord wheel's
false internal CPython 3.6 tag plus one incorrect RECORD entry. A separately
admitted repair changed only decord's `WHEEL` and `RECORD`; its shared library
remains byte-identical at SHA-256
`98b260c5812106648ba299279916fbe98439893e346d4efdcf5cde66ba8973da`.
The repaired-wheel v2 lock installs exactly 149 distributions under Python
3.11.10/cu121, passes `uv pip check`, preserves the global Python metadata
signature, and replays against environment tree SHA-256
`9e95a8d17cf8b38fb93b117327c9e68b68c4bfd5935cca81fb67fd6e1798028b`.
All 18 admitted package and project imports also pass with CUDA hidden and
offline model controls. The conservative retained-environment size is 10.691
GiB, leaving an estimated 53.335 GiB provider-quota reserve; another large
admission requires fresh budgeting. Model configuration, weight access, model
construction, GPU/lease polling, tensors, inference, rights-qualified video,
identity, AV-sync, activation, and product authority remain pending.

Row137 now has an immutable rights-scoped functional fixture at
`/workspace/w64_aqa/fixtures/W64-AQA-017/latentsync-row137-fictional-adult-pd-speech-v1`.
It binds a project-generated unnamed fictional adult face clip and the existing
public-domain "Once upon a midnight" speech mix. The two files published
atomically, hash-verified, replayed, and left no transient staging. All 49 video
frames were already reviewed; subtle identity drift and side-light color drift
remain deliberately retained as known defects, so the fixture is not golden
identity or product-quality truth. The publisher did not poll the coordinator,
GPU, load a model, or infer. A separately observed foreign MaskFactory lease has
left the shared coordinator in `RECOVERY_REQUIRED` with admission disabled; the
ComfyUI shift did not clear or override it. Model-load execution remains pending
while other safe lanes continue.

W64-AQA-018 now also binds the promoted AnimateDiff SDXL v1.0 beta motion
checkpoint to the exact versioned Wave42 S3 mirror object already recorded in
the model registry. The current-pod regular file is 950,143,538 bytes with
SHA-256 `fa4950a062e892fca50d4c441fcd6130d1ad68a621a0404d155be17580072978`,
matching that immutable mirror record. This is a partial adoption: the mirror
does not establish original-publisher identity, original-publisher hash
provenance, or license authority. The retained exact-asset technical smoke is
not promoted because its strict visual review failed frames 5-7 and found
severe frame-7 color corruption. No new model load, generation, coordinator or
GPU poll, activation, or workflow promotion occurred.

The SDXL Base 1.0 promoted checkpoint is now independently rebound to the
official provider record at immutable revision
`462165984030d82259a11f4367a4eed129e94a7b`. Its current-pod regular file is
6,938,078,334 bytes with SHA-256
`31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b`,
exactly matching the provider's published LFS object. Provider metadata reports
`openrail++`; that records metadata but does not assert user license acceptance.
A prior exact-hash bounded EC2 smoke remains historical evidence, not current-pod
capacity, lifecycle, or image-quality qualification. No GPU or coordinator poll,
model load, generation, activation, or product promotion occurred in this gate.

Flux.1 Schnell FP8 promoted storage is now independently bound to official
`Comfy-Org/flux1-schnell` revision
`7d679837b018bfeb28eca55734b335efcd0e7100`. The current-pod regular file is
17,236,328,572 bytes with SHA-256
`ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72`,
matching the published LFS object. Apache-2.0 metadata is recorded without
asserting license-acceptance authority. The existing
`true_flux_schnell_reference_smoke` lane remains
`deconstruct_only_not_promoted`; no execution bundle, model load, image QA,
activation, workflow promotion, or product promotion is granted.

Z-Image Turbo BF16 is partially adopted at the exact promoted-storage boundary.
The current-pod regular file is 12,309,866,400 bytes with SHA-256
`2407613050b809ffdff18a4ac99af83ea6b95443ecebdf80e064a79c825574a6`,
matching `Comfy-Org/z_image_turbo` revision
`d24c4cf2a0cd98a42f23467e27e3d76ee9438b8e`. That exact single-file provider
record exposes no license metadata. Apache-2.0 metadata from a differently
packaged upstream repository is therefore not inherited. The
`flux_family_zimage` lane remains `deconstruct_only_not_promoted`; no model
load, image-quality, activation, workflow, or product authority is granted.

The CLIP ViT-H-14 image encoder required by the IP-Adapter lane now passes exact
promoted-storage and provider binding at `h94/IP-Adapter` revision
`018e402774aeeddd60609b4ecdb7e298259dc729`. Its current-pod file is
2,528,373,448 bytes with SHA-256
`6ca9667da1ca9e0b0f75e46bb030f7e011f44f86cbfb8d5a36590fcd7507b030`,
matching the published LFS object; Apache-2.0 metadata is recorded without
license-acceptance authority. This independently qualifies only the encoder's
storage identity. The paired IP-Adapter weight, dependency bundle, model load,
reference-conditioning quality, activation, and workflow promotion remain false.

The paired IP-Adapter Plus SDXL weight also passes exact promoted-storage and
provider binding at the same `h94/IP-Adapter` revision. Its current-pod file is
847,517,512 bytes with SHA-256
`3f5062b8400c94b7159665b21ba5c62acdcd7682262743d7f2aefedef00e6581`,
matching the published LFS object. Together with the accepted CLIP ViT-H-14
encoder, this proves the two-file storage identity pair and nothing beyond it.
Custom-node code and dependencies, model load, conditioning quality, activation,
workflow promotion, license acceptance, and product authority remain false.

The quarantined `ComfyUI_IPAdapter_plus` checkout now passes read-only static
identity at commit `a0f451a5113cf9becb0847b92884cb10cbdec0ef`, tree
`525f6f9c9a9804f178c13a81dd6e45dd3f7ceae3`, with 34 tracked files and a
clean worktree. Its GPL-3.0 code metadata remains distinct from the model
assets' Apache-2.0 metadata. Both quarantined Wave42 workflows have 50
IP-Adapter nodes: four unified loaders and 46 appliers. Forty-five expanded
appliers default to zero and carry explicit strict spatial gates; one legacy
applier remains nonzero at 0.45 and outside that expanded gate set. Static
integrity is partially adopted, but loader presets do not prove exact runtime
file selection. Dependencies, import, object-info binding, model load, visual
quality, activation, and promotion remain false.

The three promoted Wave42 SDXL LoRAs now pass exact live hash replay and Civitai
hash-to-version binding for 685,369,060 total bytes. Provider permissions are
not uniform: Wet Makeup records commercial image/rental categories; Big
Areolas requires credit, disallows derivatives, and is marked NSFW; Latina XL
records no commercial-use category. These permission fields are retained as
machine-readable constraints, not treated as license acceptance, consent, or
product authority. No workflow binding, model load, visual-quality review,
activation, or promotion occurred.

Kokoro 82M's former provider-provenance hold is now closed. The exact three
promoted files bind to official `hexgrad/Kokoro-82M` revision
`f3ff3571791e39611d31c381e3a41a3af07b4987`; both large artifacts match
published LFS hashes and the revision-pinned `config.json` independently hashes
to the live value. Apache-2.0 metadata is recorded without license acceptance.
Storage and provider identity are adopted; dependency environment, model load,
synthesis quality, lifecycle cleanup, activation, and promotion remain false.

The quarantined AnimateDiff-Evolved checkout passes clean exact-pin identity at
commit `d8d163cd90b1111f6227495e3467633676fbb346`, tree
`87c687b5bf14e6d9885f9ec770d767584d2e5c66`, with 62 tracked files and
Apache-2.0 code metadata. Neither quarantined Wave42 workflow contains an
AnimateDiff or ADE node, so workflow binding is false. This missing binding is
retained alongside the exact motion model's frames 5-7 continuity failure and
severe frame-7 corruption. No dependency install, import, object-info binding,
model load, activation, or promotion is authorized.

Whole-workflow static ownership now covers all 40 raw node types in both
quarantined Wave42 workflows. Five of the 17 clean pinned repositories are
referenced; twelve are retained but unused. The 12 types absent from the older
inventory are exactly registered by Comfy core, Impact Pack, Impact Subpack, or
controlnet-aux. This is not runtime compatibility: the inventory records Comfy
core 0.26.0 while the current pod is tracked-clean ComfyUI 0.28.0 at
`66655153499f89052aa72d5a869f556b25f0e9c6`. An isolated `object_info` gate
must therefore prove all node types and model selections before activation.

Exact loader-widget reconciliation now blocks both quarantined workflows for
nine unique missing nonzero assets: OpenPose ControlNet, five actively weighted
LoRAs, the hands LoRA, SAM ViT-B, and the hand YOLO detector. Fourteen additional
zero-weight optional references are absent. Ten unique model paths are present,
but path presence alone does not grant hash, provider, permission, compatibility,
or quality authority. The four `PLUS FACE (portraits)` IP-Adapter loaders per
workflow remain preset-ambiguous until isolated `object_info` proves their exact
encoder and adapter file selections. Activation remains fail closed.

The nine required nonzero assets are now recovered from retained EC2 volume
`vol-0eb9b2c6d3d2706d6` into the inactive RunPod quarantine model tree. All
4,224,495,032 bytes pass source-to-destination SHA-256 equality. An ephemeral
transfer key was removed from both endpoints, and the g5 source was returned to
its stopped boundary without changing its type or DeleteOnTermination setting.
This closes the missing-byte recovery action only: none of the files is
loader-visible, and provider/permission completion, the renamed Double Kiss
provenance edge, dependencies, `object_info`, model load, execution, visual
quality, activation, and promotion remain fail closed.

Exact provider reconciliation now covers all nine recovered files. OpenPose is
the Apache-2.0 xinsir artifact at immutable Hugging Face revision `23f966c`; SAM
ViT-B exactly matches the official Meta checkpoint stream and Apache-2.0 model
license; the hand detector exactly matches Bingsu/adetailer revision `1a67ee2`
under that revision's AGPL-3.0 card. The detector contains pickle imports and
SAM is also a PyTorch checkpoint, so both require isolated sandboxed loaders.
All six LoRAs have exact Civitai by-hash bindings and use-permission snapshots.
The Hands LoRA specifically requires credit, permits commercial use only through
Civitai on-site rental, and forbids relicensing; this prevents unrestricted
product use. Civitai permissions remain snapshots rather than SPDX licenses and
must be rechecked before activation or distribution. The `adult_male` Double
Kiss workflow path is accepted as a governed alias of the byte-identical legacy
`body_male` catalog artifact. None of these static findings grants runtime or
quality authority.

Static dependency and loader review now covers all five workflow-used pinned
repositories. Their checkouts remain clean, but the dependency manifests are
not reproducible locks: Impact Pack includes mutable git-HEAD SAM2; Impact
Subpack uses a ranged Ultralytics dependency and mutable model downloads;
controlnet-aux has 25 mostly unpinned requirements; installers can mutate model
and config paths. The Subpack unsafe fallback is filename-whitelisted rather
than hash-bound, and other used repositories expose raw checkpoint loaders.
No installer or import was run. The selected DWPose widgets resolve an
Apache-2.0 ONNX detector and Apache-2.0 TorchScript pose model at exact provider
revisions, but the pinned executed DWPose implementation explicitly states CMU
non-commercial use only. Commercial activation therefore requires a reviewed
replacement implementation or accepted license authority, plus immutable
dependency locks and a disposable no-secret/no-network checkpoint sandbox.

W64-AQA-018 now has a project-owned commercial DWPose replacement contract and
deterministic copy-on-write workflow transformer. The design uses the exact
Apache-2.0 `yolox_l.onnx` and `dw-ll_ucoco_384.onnx` artifacts through ONNX
Runtime only; it forbids copied controlnet-aux DWPose code, TorchScript, pickle,
subprocess, package installation, shell, and runtime network access. Static
candidates were generated in the new inactive RunPod directory
`/workspace/wave64_quarantine/aws_ec2_20260722/candidates/commercial_dwpose_v1`.
The two original workflow hashes replayed unchanged, all three selected nodes
were transformed, and zero legacy `DWPreprocessor` nodes remain in the
candidates. This grants static design and candidate-transform authority only.
The adapter implementation, immutable environment lock, `object_info`, frozen
geometry equivalence, model load, workflow execution, activation, promotion,
and commercial runtime authority remain false; a valid coordinator lease is
still required before any runtime admission.

The corresponding project-owned custom node is now statically implemented at
`Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_commercial_dwpose`. It
matches the pinned wrapper's seven serialized controls in order, verifies both
model files as non-symlink regular files by exact size and SHA-256, requires
ONNX Runtime 1.27.0 with `CUDAExecutionProvider`, implements YOLOX decoding and
NMS, 133-point SimCC decoding, COCO WholeBody/OpenPose projection, filtering,
and pose-map rendering, and fails closed for the unqualified Xinsr scaling
mode. Exact CPython 3.11 Linux wheel identities for ONNX Runtime GPU, NumPy,
and Pillow are recorded as offline build inputs. Local static tests pass, but
the current pod exposes both GPU and CPU ONNX Runtime distributions and the
pose ONNX was not found by the bounded storage lookup. The offline wheelhouse,
target environment, target import, `object_info`, geometry equivalence, model
load, execution, commercial runtime, activation, and promotion therefore
remain unqualified and false.

The inactive RunPod runtime-staging directory now contains both exact ONNX
models and a six-wheel offline direct-dependency set for CPython 3.11 Linux.
All eight files independently replay to their contract or official PyPI sizes
and SHA-256 values. A nonzero initial transfer shell caused by text formatting
is retained as a finding and does not supply acceptance; the independent replay
does. No environment was created and no package, custom node, model, or GPU was
loaded. The next static design must preserve the ComfyUI Torch tensor boundary
while excluding the base environment's separate CPU ONNX Runtime distribution;
runtime import remains coordinator-gated.

The deterministic offline overlay is now built atomically at
`/workspace/wave64_quarantine/aws_ec2_20260722/candidates/commercial_dwpose_v1_overlay`.
It contains 1,625 files totaling 907,900,649 bytes, only the GPU ONNX Runtime
distribution metadata, the exact node, and both exact models. Its manifest and
bundled assets replay to the recorded hashes, and the node now fails closed
unless the imported ONNX Runtime module originates inside that overlay. The
offline install did not import the node or ONNX Runtime, create a model session,
use the GPU, or touch the coordinator. Import and `object_info` remain the first
lease-gated canaries, followed separately by frozen geometry equivalence.

W64-AQA-009 now also records the existing current-pod InternVL3.5-8B BF16
package as a provisional visual-juror canary. An independent provider replay
matched all 24 primary files and 17,072,800,269 bytes to official revision
`9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79`; all four safetensor shards match
their published SHA-256 values, with zero missing, extra, or mismatched primary
files. A high-risk-pattern scan of the five custom-code files found no network,
shell, pickle, dynamic-execution, raw checkpoint-load, or arbitrary file-open
calls, but full semantic review and an immutable dependency environment remain
required before import. This 8B package cannot substitute for the pinned
241B-A28B independent juror and grants no load, inference, quality, juror,
activation, or promotion authority.

The five pinned custom-code files now have both an AST receipt and a manual
semantic review. They contain no network, shell, pickle, dynamic execution,
raw checkpoint load, or arbitrary file-open path. Top-level effects are limited
to four local conversation-template registrations and optional FlashAttention
and Apex import attempts. Two code-quality findings remain explicit gates: the
FlashAttention import catches a broad exception, and the token-count mismatch
fallback uses chained advanced-index assignment that may not update the source
embedding tensor. The pod base stack cannot resolve `Qwen3ForCausalLM` because
it has Transformers 4.46.3 and no Accelerate. The immutable, already verified
Qwen3-Omni environment has Transformers 5.2.0, Accelerate 1.14.0, the Qwen3
modeling file, and no system-site-package inheritance; it is only a reuse
candidate because `timm` and `einops` are absent. A new immutable overlay must
add pinned copies of those two dependencies. No import, load, GPU use, or
runtime authority was claimed by this static preflight.

The immutable dependency action is now complete without mutating the verified
Qwen3-Omni environment. Two official pure-Python wheels—`timm==1.0.28` and
`einops==0.8.2`—were pinned by exact PyPI size and SHA-256, downloaded into a
dedicated wheelhouse, and extracted into an atomic add-on overlay. The first
builder attempt correctly failed before target creation because the deliberately
minimal base environment has no `pip`; partial cleanup passed. The accepted
builder therefore performs no resolver execution: it admits only exact
`py3-none-any` wheels, verifies their purity metadata, and rejects traversal,
symlink, duplicate-member, or hash drift before atomic publication. The final
overlay contains 345 regular files and 9,389,082 bytes with tree digest
`1191178fb3f8ff148b7330767f8d0e1dd0f3418cfacd29d0f3ce19490f6895b7`.
Metadata-only validation under the base Python resolved all five active `timm`
requirements across 75 base plus two overlay distributions with zero errors.
No base file had a timestamp change after the build boundary. Package import,
custom-code execution, model load, GPU use, runtime quality, and authority are
still false until their separately admitted canaries pass.

The next import-only canary is now fully admitted but not executed. Its lock
binds the five reviewed source hashes, exact interpreter and overlay manifest,
expected InternVL and Qwen3 class identities, exact versions, and the one
allowed FlashAttention-absent message. The runner forces offline operation,
disables bytecode writes and CUDA visibility, verifies the source tree did not
gain cache directories, and grants no config instantiation, model
instantiation, weight access, model load, GPU, or inference authority. A fresh
coordinator read still reports the expired foreign MaskFactory lease in
`RECOVERY_REQUIRED`; ComfyUI did not clear or override it, so `executed` remains
false. Once that owner restores admission, the canary must run once under an
exact `comfyui_main` lease before any load/unload capacity canary is admitted.

Project-use license reconciliation is also complete for this exact provisional
package. The pinned package README (SHA-256 `47383e97...`) declares the project,
weights, and Qwen3 component Apache-2.0. Four exact InternVL code files carry
MIT headers; `conversation.py` records derivation from FastChat, whose official
pinned repository license is Apache-2.0. The model snapshot has no standalone
`LICENSE` file, so that absence is retained as a packaging finding rather than
silently inferred away. Use in Comfy_UI_Main is accepted only with notice
retention: any candidate promotion must include the exact package README plus
the pinned InternVL MIT and FastChat Apache-2.0 license texts. This closes the
license-acceptance gate only; it grants no import, runtime, quality, juror,
activation, or product authority.

The 241B independent-juror route now has a bounded static admission decision.
The pinned community `i1-IQ4_XS` candidate consists of three raw continuation
parts totaling 125,283,908,960 bytes and requires ordered concatenation; its
separate pinned Q8 vision projector is 5,976,491,584 bytes. HTTP 206 range
audits fetched only the first 8 MiB of the model's first part and projector.
The complete metadata regions fit within those bounds and identify
`qwen3moe` for the language model and `internvl` for the projector. No model or
projector payload was downloaded.

Pinned llama.cpp revision
`e8e6c7af2456fd50bb62f7a2bbd642e6fb14ae77` contains both the `qwen3moe`
architecture mapping and an InternVL multimodal projector implementation.
This is a static identifier match, not a runtime qualification: the official
multimodal documentation describes the subsystem as under heavy development
and names InternVL 2.5 and InternVL 3, not InternVL 3.5. The current pod has no
pinned llama.cpp runtime binary, so a reproducible immutable build plus exact
metadata-open, projector-open, single-image, capacity, cleanup, and quality
campaigns remain mandatory.

Storage admission fails closed. The four files total 131,260,400,544 bytes
(122.245774 GiB). Preserving the required 50 GiB post-install reserve requires
at least 172.245775 GiB exact free quota before transfer. The latest defensible
project estimate is only 53.335322 GiB, while the 1,000 GB control-plane volume
size and shared-backend `df` do not prove current tenant free quota. The
candidate alone exceeds that estimate by 68.910452 GiB and the full admission
threshold by 118.910452 GiB. No download, concatenation, build, load,
inference, visual-quality, arbitration, golden-mask, activation, or product
authority is granted. The fail-closed sequence is maintained in
`Plan/Instructions/QA/WAVE64_INTERNVL35_241B_JUROR_ADMISSION.md`.

## Retained role-qualification corpus

W64-AQA-013 now binds a private nine-case corpus spanning the required
known-good, known-bad, borderline, adversarial, refusal, identity, temporal,
audio-mask, and workflow categories across seven modalities. Every source and
truth-evidence file is repository-relative, byte-counted, SHA-256 bound, and
split prospectively into calibration and held-out partitions. Shared media may
carry different expected outcomes only when the task scope is explicitly
different, such as deterministic decode versus strict visual approval.

This frozen corpus grants source admission only. Each required role must later
run calibration first under its own exact coordinator lease, freeze thresholds,
and execute held-out cases once. No model capacity, quality, repeatability,
refusal, independent-juror, golden-mask, activation, or promotion authority is
inferred from corpus construction.

The corpus is expanded into a frozen 12-role execution matrix. Every role
receives all nine required categories; role-relevant cases keep their declared
expected result, while every out-of-scope request must be refused. This creates
108 explicit role-case bindings and prevents a specialist from gaining credit
by silently skipping categories it cannot judge. Declared model names are
planning targets only until immutable checkpoint, runtime, prompt, lease,
capacity, quality, cleanup, and lifecycle receipts bind each execution.

## Sole-pod qualification campaign queue

The frozen corpus and 12-role matrix now feed a deterministic 14-campaign
queue. The queue binds its matrix, role registry, package inventory, campaign
policy, and the exact admitted Wav2Vec2 and MIT AST inputs by SHA-256. It covers
two supporting audio campaigns followed by all twelve required roles. Three
campaigns are repository-prepared: the two exact audio admissions and the exact
ASR-plus-Omni audio-semantic role after both dependency receipts. The other
eleven role campaigns remain held on explicit package identity, project-license,
installation, executor, storage, provisional-substitution, or external-release
gates.

The first GPU action is Wav2Vec2 expanded alignment: acquire one exact
`comfyui_main` exclusive lease, execute calibration, freeze observed thresholds,
execute held-out once, verify child-process and VRAM cleanup, release the lease,
and retain immutable receipts. MIT AST AudioSet event calibration follows under
a separate lease with the same discipline. Only then may the exact ASR-plus-Omni
audio-semantic role campaign be considered. Every later role repeats the
matrix-defined identity, lease, calibration, threshold-freeze, held-out,
certificate, cleanup, release, and retention sequence.

This queue is execution planning only. It intentionally contains no live
coordinator snapshot, and `runnable_now` remains false until the recovery owner
restores admission and an exact lease is granted. Idle GPU telemetry is not
authority. ComfyUI must not override foreign recovery, run more than one GPU
campaign at a time, enable an alternative-pod watcher, or use external
inference. A local digest does not prove upstream identity or license; an
upstream model name does not prove installed bytes; InternVL3.5-8B cannot
substitute for the declared 241B independent juror; and golden-mask work remains
a read-only external-release consumer lane. No runtime, capacity, quality,
juror, golden-mask, activation, or promotion authority follows from queue
construction.

The role-certificate engine now matches this prospective partition discipline.
Every report binds the execution-matrix hash and labels each fixture as
calibration or held-out. Calibration fixtures require repeated runs and alone
contribute to repeatability. Held-out fixtures execute exactly once; a repeated
held-out run is rejected instead of being miscounted as repeatability evidence.
Certificates expose calibration, held-out, held-out-run, and repeatability
fixture counts, and matrix-identity drift suspends an otherwise qualified
scope. This contract correction grants no role authority by itself; the first
deterministic executor and report remain pending.

The aggregate control-package replay also exposed a stale 16-package schema
limit after the retained provisional InternVL3.5-8B record raised the truthful
inventory to 17. The inventory schema and aggregate validator now agree on all
17 records and accept the provisional package's static review, layered
environment, license, loader, and storage evidence extensions. This is schema
reconciliation only: the 8B package remains non-operational and cannot
substitute for the declared 241B independent juror.
