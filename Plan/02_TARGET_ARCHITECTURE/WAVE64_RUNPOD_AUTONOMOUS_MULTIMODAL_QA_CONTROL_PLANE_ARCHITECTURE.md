# Wave64 RunPod Autonomous Multimodal QA Control-Plane Architecture

Program ID: `W64-AQA`

## Component map

```text
job request
  -> immutable quality contract
  -> deterministic admission and lineage gate
  -> exclusive RunPod phase lease
  -> ComfyUI candidate generation
  -> modality-specific measurements
  -> smoke/triage reviewer (optional, no approval authority)
  -> strict calibrated reviewer (when qualified for the scope)
  -> deterministic policy decision
       -> PASS and promotion request
       -> bounded targeted repair
       -> REJECT / BLOCKED / HUMAN_EXCEPTION_REQUIRED
  -> immutable decision receipt and rollback pointer
```

## Service boundaries

### Job contract compiler

Normalizes requested modalities, subject and identity references, prompt,
expected duration, protected regions, quality floors, hard failures, reviewer
requirements, cost ceiling, attempt ceiling, and human-exception policy. The
contract is immutable after execution begins; revisions create a new job.

### Artifact and lineage service

Hashes source, baseline, generated, repaired, measurement, crop, frame, mask,
audio, workflow, and receipt artifacts. It rejects broken parentage and stores
promotion candidates separately from accepted artifacts.

### Deterministic measurement services

Image, video, audio/AV, and mask analyzers emit versioned measurements with
applicability and missingness. A metric implementation, threshold set, and
normalization version are required. Missing required measurements fail closed.

### Reviewer gateway

Resolves a role from the role registry, checks checkpoint/digest, runtime,
calibration and scope, constructs the bounded input package, enforces JSON
schema, and records raw response hash. It does not grant promotion authority.

### Deterministic tool admission and execution

The model-facing gateway is a pure decision service. A physically separate
executor recomputes the exact request, decision, policy, role, job, action, and
target binding before doing anything. Its first qualified capability is a
job-scoped `artifact_read` that returns a stable SHA-256 and byte count only.
It rejects path escapes, sensitive names and content, oversized files,
symlinks/reparse points, identity changes, nonempty parameters, and receipt
overwrite; it cannot expose content, write the target, or use the network.
Every other admitted action remains unqualified until it has its own isolated
implementation, exact root/target contract, rollback model, and fault campaign.

### Phase lease and resource arbiter

Owns the mutually exclusive `GENERATION`, `MEASUREMENT_GPU`, `REVIEW`, and
`IDLE_RECONCILE` phases for the single GPU. It records foreign queue state,
ComfyUI unload, reviewer load/unload, free VRAM, timeouts, and lease recovery.
Unknown jobs are preserved and produce a typed blocker.

### Correction planner and patch gateway

Accepts only typed defects and allowlisted patch classes: prompt fragment,
bounded sampler setting, model from an already eligible set, regional mask,
image region, frame span, audio span, or predeclared workflow patch point.
Every proposal is schema-validated, range-checked, tested on a candidate copy,
and reversible. Arbitrary shell, node invention, secret access, Git, cloud
mutation, threshold changes, and tracker writes are forbidden.

### Workflow inspection and sandbox service

Parses ComfyUI API and UI workflows, validates node and connection types against
the live object-info snapshot, resolves exact model/component identities,
checks engine compatibility and resource policy, and maps runtime errors or QA
defects to approved patch points. A coding model may propose RFC 6902-style or
typed graph operations, but this service applies them only to a candidate copy.
The candidate must pass static validation, bounded sandbox execution, artifact
capture, applicable media QA, and regression comparison before promotion.

The inspector accepts production-shaped inputs only after four independent
digest receipts bind workflow, object info, immutable contract, and model
inventory to one job and contract authority. The CLI has no permissive default:
unbound input is an explicit unit-test-only mode. This binding does not qualify
the later validator-run, workflow-inspect, candidate-write, or generation tools.

### Policy engine

Applies hard gates before weighted scores. It owns retry/no-progress ceilings,
compare-improve-or-revert, reviewer disagreement, abstention, promotion request,
and human exception decisions. It never converts exhaustion or missing evidence
to PASS.

### Evidence and promotion service

Writes append-only measurements, observations, repair attempts, decisions, and
rollback pointers. Promotion is a separate integration-authority action bound
to the exact accepted receipt.

## State machine

```text
CREATED
  -> ADMISSION_BLOCKED | ADMITTED
ADMITTED
  -> GENERATING
GENERATING
  -> GENERATION_FAILED | MEASURING
MEASURING
  -> HARD_REJECT | REVIEW_PENDING | REVIEW_BLOCKED
REVIEW_PENDING
  -> REVIEW_REJECT | POLICY_PENDING | REVIEW_BLOCKED
POLICY_PENDING
  -> PROMOTION_CANDIDATE | REPAIR_PLANNED | REJECTED | HUMAN_EXCEPTION_REQUIRED
REPAIR_PLANNED
  -> REPAIRING -> MEASURING
PROMOTION_CANDIDATE
  -> ACCEPTED | PROMOTION_REJECTED
```

Terminal states are `ACCEPTED`, `REJECTED`, `HARD_REJECT`,
`GENERATION_FAILED`, `REVIEW_BLOCKED`, `PROMOTION_REJECTED`, and
`HUMAN_EXCEPTION_REQUIRED`. Crash recovery reconstructs state from receipts and
never assumes an in-flight phase succeeded.

## Reviewer activation contract

A reviewer role may be `ACTIVE_STRICT`, `ACTIVE_TRIAGE`, `SHADOW`,
`BLOCKED_UNQUALIFIED`, or `DISABLED`. Activation requires:

- exact model/checkpoint identity and hash or Ollama digest;
- license and allowed-use record;
- runtime, precision/quantization, GPU count and VRAM envelope;
- prompt, rubric, decision schema, and sampling configuration versions;
- representative calibration results including refusal and invalid-JSON rates;
- modality, content, resolution, duration, and defect scope;
- latency and monetary-cost envelope;
- known limitations, fallback, expiry, and rollback.

The current 48 GB pod remains the first qualification and rollback target. The
122B, 241B, and 397B packages must declare exact precision, quantization,
CPU/NVMe offload, peak VRAM/RAM/storage, latency, and quality envelopes. A model
that downloads or starts but misses any floor remains blocked. The preferred
single-pod successor is 2x A40 (96 GB aggregate); it must prove same-host GPU
topology and tensor-parallel/NCCL behavior because aggregate VRAM is not one
allocation. The fallback is one RTX PRO 6000 Blackwell with 96 GB contiguous
VRAM. Either successor is a new runtime identity and qualifies independently.

## Decision order

1. Validate schema, identity, hashes, lineage, and required artifacts.
2. Apply deterministic hard failures.
3. Confirm reviewer eligibility for this exact scope.
4. Validate reviewer output schema and completeness.
5. Resolve disagreement without averaging away hard failures.
6. Calculate applicable score vector and protected-regression checks.
7. Apply attempt and no-progress ceilings.
8. Emit one schema-constrained decision and immutable rollback parent.

## Modality contracts

- **Image:** decode, geometry, color/alpha, perceptual/identity evidence, crops,
  anatomy, materials, lighting, background, seams, and prompt adherence.
- **Video:** container/decode, duration/FPS, sampled-frame manifest, worst-span
  selection, motion, flicker, temporal identity, object and scene continuity.
- **Audio/AV:** codec, channels/rate, LUFS/peak/clipping, silence, phase,
  discontinuity, ASR/alignment and AV offset only when their models qualify.
- **Mask:** target-instance binding, dimensions, alpha semantics, completeness,
  leakage, topology, boundary/fine-detail, occlusion, and temporal stability.
- **Workflow:** schema, node availability, typed connections, exact model
  identity, parameter ranges, engine compatibility, path policy, resource
  envelope, sandbox execution, output capture, and regression comparison.

## Autonomous service pool

The deterministic controller selects among isolated, sequential role packages:

- fast planner/triage: target Qwen3.6-35B-A3B class;
- current strict visual: calibrated `qwen2.5vl:32b`;
- target primary visual: quantized/offloaded Qwen3.5-122B-A10B on the primary pod;
- independent juror: quantized/offloaded InternVL3.5-241B-A28B on the primary pod;
- senior arbitration: on-demand quantized/offloaded Qwen3.5-397B-A17B role;
- semantic audio/AV: Qwen3-Omni plus ASR/alignment and quantitative scorers;
- workflow engineer: Qwen3-Coder-Next proposal service behind patch gateway;
- golden masks: primary-pod SAM 3, SAM2Matting, MatAnyone2, PDFNet, BiRefNet
  HR-Matting, MODNet, and Robust Video Matting role packages under MaskFactory contracts.

Package absence or failed capacity/quality qualification degrades to a typed
blocker, smaller certified scope, or human exception. It never grants a weaker
model more authority. Migration uses a bounded overlap: create the candidate,
attach or copy durable state by verified hashes, run canaries, drain the current
pod, switch the runtime identity, then stop the old pod. Failure destroys only
the candidate and returns to the proven current pod without weakening gates.

## Storage and deployment

Durable models, Ollama blobs, workflows, outputs, evidence, and caches belong
under `/workspace` on the attached network volume or in the configured S3
project bucket. The 20 GB overlay is limited to the base image and disposable
packages. S3 manifests are content-addressed; historical EC2 paths remain
readable but cannot be selected as current runtime proof.

## Security

The gateway receives named credential capabilities, never secret values in
prompts or receipts. External metadata and model output are untrusted data.
Network destinations, filesystem roots, tools, workflow patch points, parameter
ranges, model identities, costs, and retries are allowlisted. Denied actions are
recorded as evidence.

## Degraded modes

- Strict reviewer unavailable: `REVIEW_BLOCKED`, never small-model PASS.
- Independent juror unavailable: follow the declared current-tier policy or
  require human exception; never invent agreement.
- GPU/queue conflict: wait within the lease budget, then typed blocker.
- S3 unavailable: retain local durable evidence and block promotion requiring S3.
- MaskFactory unavailable: continue non-mask lanes; mask-required jobs block.
- Cost ceiling reached: stop paid work and preserve resumable state.
- Invalid model response: bounded retry, alternate qualified reviewer, or block.
