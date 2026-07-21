# RunPod Autonomous Multimodal QA Operating Protocol

Program: `W64-AQA`

## 1. Authority and preflight

1. Work only from `C:/Comfy_UI_Main` and record branch, HEAD, upstream, and exact
   dirty ownership before edits or promotion.
2. Query RunPod through configured credentials without printing secrets.
3. Bind pod, GPU, volume, image, cost, overlay, ComfyUI health, Ollama health,
   model digests, queue state, and foreign process state to a timestamped receipt.
4. Never start EC2 or local ComfyUI for a current RunPod claim.
5. Treat all supplied sibling repositories, transfers, backups, WSL images,
   MaskFactory stores, and `F:/Models` as read-only evidence unless a separate
   exact-path reconciliation authorizes bytes.
6. An idle ComfyUI queue and empty Ollama residency are necessary but not
   sufficient. Classify active foreign GPU workloads immediately before lease
   acquisition and again before inference. If one is present, emit a no-action
   hold receipt, preserve it, and switch tracker lanes; never kill, unload, or
   delay the foreign owner through an uncoordinated lock.

## 2. Storage rules

- `/workspace` is the durable RunPod root.
- Set `OLLAMA_MODELS=/workspace/ollama` before serving or listing reviewers.
- Keep model binaries, ComfyUI inputs/outputs, reviewer artifacts, and evidence
  off the 20 GB overlay.
- Warn at 75% overlay use; block new downloads at 85% until reconciled.
- S3 writes require an exact bucket/prefix, content hash, manifest, encryption
  policy, cost posture, and a non-secret receipt.
- Every required role package is installed on the primary pod's durable volume.
  Installation is not activation; only an exact capacity-and-quality certificate
  can mark the package operational.

## 3. Exclusive GPU phases

### Generation phase

1. Confirm no foreign lease or unknown job owns the queue.
2. Unload Ollama reviewers with `keep_alive=0`.
3. Reconcile GPU memory and submit one authorized ComfyUI job.
4. Wait using bounded event/status checks; do not create an infinite monitor.
5. Record generation receipt and wait until the ComfyUI queue is idle.

### Review phase

1. Confirm the generated artifact hash and complete required measurements.
2. Use the approved ComfyUI unload/free helper and record free VRAM.
3. Confirm the reviewer digest and role-registry state.
4. Run only the allowed artifact/crop/frame package through the strict prompt.
5. Validate the response against the decision schema.
6. Record raw-response hash, latency, VRAM, and disposition.
7. Unload the reviewer before returning to generation.

Never run generation and a reviewer concurrently without an exact combination
certificate. Before each sequential role transition, stop accepting work, drain
the owned queue, unload the prior model, reconcile VRAM/RAM, load the pinned
quantization/offload package, run its bounded phase, retain the receipt, and unload it.

## 4. Reviewer roles

- `qwen2.5vl:32b`: strict image and sampled-video reviewer only within its
  calibrated scope. Its PASS still requires deterministic gates.
- 4B/7B/8B/13B installed models: connectivity, triage, crop/frame selection,
  and known-bad smoke tests only.
- Text-only models: summarization or correction-plan formatting only; no visual,
  audio, mask, promotion, or runtime authority.
- Qwen3.5-122B, InternVL3.5-241B, Qwen3.5-397B, Qwen3-Omni, Qwen3-ASR,
  Qwen3-Coder-Next, and the complete golden-mask ensemble: install to the primary
  durable volume, then keep each role blocked until its own registry activation
  contract is satisfied.

Deterministic audio measurement is a non-GPU lane and must continue while a
foreign workload owns the pod GPU. Compile it as an audio shadow requiring only
`W64-AQA-ROLE-DETERMINISTIC`, retain exact artifact/manifest/diagnostic hashes,
and record semantic audio as a separate release gate. Never substitute the
visual reviewer for audio authority and never interpret waveform/spectrogram
inspection as perceptual playback. The current canonical receipt is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AUDIO_SHADOW_20260721T221732Z.json`;
it passes deterministic gates only and cannot promote product.
For AV technical shadowing, use the same deterministic-only stage and require
zero-tolerance lineage plus bounded container start/duration alignment. A
decoded still proves decode and gross frame structure only. The paired receipt
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AV_SHADOW_20260721T222452Z.json`
has zero stream-start and duration deltas, but strict motion, semantic audio,
AV-sync, and independent-juror gates remain unexecuted or unqualified.

Known-bad image artifacts are first-class calibration evidence. Preserve their
original lineage and rejection rather than regenerating or relabeling them. The
current canonical image shadow is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_IMAGE_SHADOW_20260721T223341Z.json`:
technical gates pass, Codex whole-image QA rejects the placement/shadow defects,
and the bound 32B strict-model step remains held until the foreign GPU lease is
released. A technical PASS must not enter promotion or correction retention by
itself.

For video, run the full deterministic decode before constructing review inputs.
Retain the exact sampled-frame hashes and metric-selected motion, exposure, and
sharpness spans. The current canonical receipt is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_VIDEO_SHADOW_20260721T224034Z.json`:
49 FFV1 frames and 24 samples pass with no sampled duplicates, while the viewed
five-frame sheet remains diagnostic-only. Do not promote until strict sampled-
video and whole-clip temporal review execute after the typed GPU hold clears.

## 4A. One-pod capacity migration

1. Preferred profile: one pod with 2x A40, 96 GB aggregate VRAM, at least 100 GB
   RAM and 18 vCPU. Require same-host topology, peer access, NCCL/tensor-parallel,
   per-GPU OOM, aggregate throughput, and role-quality canaries.
2. Performance fallback: one RTX PRO 6000 Blackwell 96 GB pod with at least
   124 GB RAM and 32 vCPU. Treat its contiguous VRAM and Blackwell runtime as a
   different execution envelope; never reuse A40 certificates.
3. Capture live price, stock, datacenter, storage compatibility, CUDA/container,
   and bounded migration cost before creation. No candidate starts without a
   maximum overlap duration and automatic failure teardown.
4. Do not assume simultaneous writable access to one network volume. Attach only
   where the provider guarantees it, otherwise transfer immutable packages and
   artifacts by hash through approved durable storage.
5. Keep the current pod unchanged while the candidate proves ComfyUI, model
   inventory, generation, every claimed role, evidence replay, crash recovery,
   queue drain, and rollback. A model role can remain blocked after migration.
6. Drain the current pod, switch runtime identity, and stop the old pod only after
   all migration gates pass. Candidate failure returns to the current pod.
7. A second long-lived inference pod remains forbidden unless the user later
   approves a separate burst policy and dollar ceiling.

## 5. Bounded repair execution

1. Freeze the accepted parent and baseline receipt.
2. Convert blocking findings to typed defect codes and exact target spans.
3. Select one allowlisted repair patch; validate IDs, ranges, nodes, and models.
4. Create a candidate without mutating the accepted parent.
5. Rerun failed gates, adjacent/protected gates, and a reduced regression set.
6. Accept only measured improvement with no protected regression.
7. Otherwise revert and increment the defect/global attempt counters.
8. Stop at two attempts per defect, four total generations, or two no-progress
   cycles. Emit a typed terminal decision rather than lowering standards.

## 6. Workflow review and patch execution

1. Snapshot the accepted workflow JSON, object-info/node inventory, installed
   models, custom-node lock, runtime policy, and accepted output receipt.
2. Run graph schema, node existence, connection type, required input, model
   identity, compatibility, path, parameter range, and resource validation.
3. Provide only these snapshots, defect JSON, logs, and approved patch points to
   the qualified workflow-engineer service.
4. Require a typed patch with rationale, expected effect, risks, target nodes,
   protected invariants, and rollback parent; reject arbitrary code or shell.
5. Apply the patch to a candidate copy, rerun static validation, and execute one
   bounded sandbox job under the phase lease.
6. Run applicable media/mask QA and workflow regressions. Promote only through
   integration authority when the candidate improves with no invariant regression.
7. Revert automatically on validation, execution, QA, cost, or regression failure.

### Read-only MaskFactory intake

Compile every external mask package with
`compile_wave64_runpod_autonomous_maskfactory_consumer_contract.py` before QA.
The contract binds exact source, candidate mask, integration-accepted golden
reference, and target-overlay hashes; common geometry; and one target instance.
MaskFactory remains an external read-only candidate producer. The contract
never grants runtime, golden-reference, product-promotion, tracker, or
cross-repository write authority. Missing artifacts, unsafe relative paths,
geometry mismatch, incomplete gates, or an attempted authority expansion fail
closed while non-mask lanes continue.

MaskFactory task `019f4cfc-60c3-7500-8626-261dcf70db5d` is the sole producer-side
masking authority while active. Comfy_UI_Main must not implement candidate-mask
generation/refinement, tournaments, human-review/CVAT flow, accepted-golden
creation, training datasets, segmentation or matting training, serving,
producer qualification, or masking-specific RunPod runtime. Resume integration
only from a versioned release containing exact model/artifact hashes, API and
input/output schemas, target-instance semantics, runtime/resource envelopes,
qualification evidence, representative fixtures, licensing/provenance, and
rollback instructions. A live MaskFactory lease is recorded once as a transient
hold; switch to a non-mask lane without polling, competing, or stopping it.

## 7. Secrets and external systems

- Never display or store `.env` values, API keys, tokens, SSH private keys, or
  temporary credentials.
- GitHub, AWS/S3, RunPod, and MaskFactory mutations remain integration-authority
  actions with exact targets and receipts.
- Historical EC2 artifacts in S3 remain readable evidence but cannot authorize
  EC2 or claim current deployment.
- Recurring Admission/Cursor/Claude/Health/Lifecycle tasks remain disabled.

### Qualified read-only tool execution

The gateway decision is never itself execution authority. For the currently
qualified `artifact_read` scope, invoke
`execute_wave64_runpod_autonomous_readonly_tool.py` only with the exact request,
decision, policies, and an integration-authority-selected plain job root. The
executor must recompute the gateway decision and reject mismatches, nonempty
parameters, sensitive names or content, files above 16 MiB or the five-second
elapsed guard, path escapes, symlinks/reparse points, and any identity change
across lookup, open, read, and post-read verification. The receipt may disclose
a digest and byte count only.
It must record no content exposure, target write, or network use and publish
atomically without overwriting an existing receipt.

No other gateway action is executable yet. In particular, do not map
`proposal_write`, `candidate_write`, `evidence_append`, `validator_run`,
`workflow_inspect`, `object_info_read`, or `shadow_generation_submit` to this
executor. Qualify each separately with exact roots, schemas, ceilings, rollback,
and fault injection before runtime use.

## 8. Incident and recovery

On crash, timeout, invalid JSON, OOM, queue conflict, missing model, storage
pressure, or network failure:

1. Stop new submissions.
2. Preserve foreign jobs and accepted parents.
3. Record the last durable state, active phase lease, process and queue facts.
4. Unload only processes owned by this receipt when safe.
5. Reconcile artifact hashes and state transitions.
6. Resume from the last proven state or emit `BLOCKED`; never infer success.

## 9. Shift continuation

After each accepted bounded increment, update truthful evidence, commit/push
only reviewed exact paths, recompute dependencies, and move to the next
unblocked tracker row. A single accepted artifact or blocked GPU lane is not a
shift-complete condition.
