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
- Model downloads and pod migration require an exact storage/cost receipt and a
  reversible rollout plan. The current pod stays intact until the candidate
  one-pod profile passes canary and rollback gates.
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
