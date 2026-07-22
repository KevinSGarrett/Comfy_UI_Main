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
   sufficient. Before every GPU-affecting action, obtain and validate an exact
   shared-coordinator lease with fresh telemetry, reserved peak VRAM, intensity,
   and lease-mode evidence. Retain foreign process and internal lock observations
   in the receipt, but do not treat process presence or a project-internal lock as
   cross-project authority. Never kill, unload, or steal another owner's process,
   model, or lease.

## 2. Storage rules

- `/workspace` is the durable RunPod root.
- Set `OLLAMA_MODELS=/workspace/ollama` before serving or listing reviewers.
- Keep model binaries, ComfyUI inputs/outputs, reviewer artifacts, and evidence
  off the 20 GB overlay.
- Warn at 75% overlay use; block new downloads at 85% until reconciled.
- S3 writes require an exact bucket/prefix, content hash, manifest, encryption
  policy, cost posture, and a non-secret receipt.
- The qualified evidence-staging boundary is Codex integration authority only,
  bucket `comfy-ui-main-runtime-029530099913-us-east-1`, prefix
  `evidence/w64-aqa/qualification/objects`, a SHA-256-derived key, conditional
  create, AES-256, versioning, and checksum-enabled `HeadObject` replay. Never
  overwrite or delete qualification objects. This boundary does not authorize
  an LLM cloud tool, a full bundle promotion, or product acceptance.
- Full qualification bundles use
  `evidence/w64-aqa/qualification/bundles/{bundle_id}`. Verify every record
  against deterministic replay, conditionally stage content-addressed records,
  and write `bundle.json` last. On interruption, retain the immutable records
  and resume by checksum-enabled head verification. Rollback is nonpublication,
  never object deletion. A complete staged bundle still grants no acceptance.
- After the evidence commit is pushed, stage one content-addressed binding under
  `evidence/w64-aqa/qualification/bindings/{commit}` containing the exact commit,
  bundle ID, manifest key/version, and transaction receipt IDs. Verify it by
  checksum-enabled head replay and retain the non-promotional receipt in Git.
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
technical gates pass, Codex whole-image QA rejects the placement/shadow defects.
The bound 32B model has now passed an exact-digest load, missing-media refusal,
and unload canary under an exclusive shared-coordinator lease, but it has not yet
reviewed this artifact or passed image-quality calibration. A technical or
generic runtime PASS must not enter promotion or correction retention by itself.

For video, run the full deterministic decode before constructing review inputs.
Retain the exact sampled-frame hashes and metric-selected motion, exposure, and
sharpness spans. The current canonical receipt is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_VIDEO_SHADOW_20260721T224034Z.json`:
49 FFV1 frames and 24 samples pass with no sampled duplicates, while the viewed
five-frame sheet remains diagnostic-only. Do not promote until strict sampled-
video and whole-clip temporal review execute after the typed GPU hold clears.

## 4A. Current-production-pod capacity

1. The sole active target is RunPod `1q4ji0gg1fkhvt`: one RTX 6000 Ada with
   49,140 MiB VRAM. The latest direct probe measured 540,844,122,112 total host-
   memory bytes, 438,214,877,184 available bytes, 128 CPUs, and
   142,706,362,155,008 filesystem-reported free bytes under `/workspace`.
2. Alternative pod stock watching, candidate creation, migration, and external
   inference are disabled. Do not wait for future hardware before installing or
   qualifying a required role on the current pod.
3. Run at most one heavy GPU role at a time unless the shared coordinator has
   separately qualified the exact shared profiles. Use sequential unload/reload,
   quantization, CPU offload, NVMe offload, bounded context, and chunked media.
4. Before authority, record exact package hashes, precision, peak VRAM, peak host
   RAM, storage, latency, quality, cleanup, failure recovery, and cost. A role
   that misses a gate remains unqualified; immediately test a safer same-pod
   envelope or continue another current-pod role rather than waiting for hardware.
5. Do not assume simultaneous writable access to one network volume. Transfer
   immutable packages and artifacts by hash through approved durable storage.
6. Keep the current pod authoritative while each package independently proves
   identity, license, dependencies, capacity, runtime, quality, cleanup, failure
   recovery, cost, replay, and rollback. Storage presence never activates a role.
7. Do not create, watch, or wait for replacement or burst pods. A second
   inference pod remains forbidden unless the user later changes this policy.
8. When one role is held, record its exact gate and continue the next
   dependency-unblocked current-pod role; never reduce the required role set.

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

1. Snapshot the accepted workflow JSON, object-info/node inventory, immutable
   job contract, installed models, custom-node lock, runtime policy, and
   accepted output receipt.
2. Obtain four distinct qualified `artifact_read` receipts for the workflow,
   object-info, contract, and model-inventory bytes. The contract ID is the
   shared authority binding and its job ID must match every receipt.
3. Run graph schema, node existence, connection type, required input, model
   identity, compatibility, path, parameter range, and resource validation.
4. Provide only these snapshots, defect JSON, logs, and approved patch points to
   the qualified workflow-engineer service.
5. Require a typed patch with rationale, expected effect, risks, target nodes,
   protected invariants, and rollback parent; reject arbitrary code or shell.
6. Apply the patch to a candidate copy, rerun static validation, and execute one
   bounded sandbox job under the phase lease.
7. Run applicable media/mask QA and workflow regressions. Promote only through
   integration authority when the candidate improves with no invariant regression.
8. Revert automatically on validation, execution, QA, cost, or regression failure.

CLI workflow validation fails closed without the four-receipt bundle. The
`--allow-unbound-static-test` escape hatch is limited to unit fixtures and must
never support a runtime, candidate, acceptance, or promotion claim.

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

Two logical workflow actions have a separate qualified executor in shadow mode:
`workflow_inspect` must target exactly `workflow.graph`, and `validator_run`
must target exactly `validate.workflow.v1`. Both require the four-receipt input
bundle, empty parameters, an exact admitted role, the contract-ID authority
binding, at most 16 MiB total input, 4096 nodes, 1024 findings, and the
five-second elapsed guard. They perform static validation only.

Do not map any other validator target, `proposal_write`, `candidate_write`,
`evidence_append`, `object_info_read`, or `shadow_generation_submit` to either
qualified executor. Production mode, sandbox execution, content exposure,
target writes, and network use remain denied. Qualify every expansion with its
own exact schema, policy, limits, rollback, and fault campaign.

One candidate stager is qualified locally for the exact shadow target
`jobs/{job_id}/candidates/workflow.candidate.json`. It requires the immutable
contract, all four digest receipts, the typed patch allowlist, an empty parameter
object, and a pre-created plain sandbox directory tree. It publishes by
no-overwrite atomic copy-on-write, verifies the base bytes remain unchanged, and
removes its candidate if a source race is detected. It must never be treated as
ComfyUI sandbox execution or regression evidence. Those steps wait for the
repository-backed phase lease release.

Correction transactions must bind three immutable files: candidate-staging,
deterministic measurement, and sandbox receipt. Publish the next state before
the transaction receipt. If interrupted at that boundary, rerun must verify and
reuse the exact state, then publish the receipt; a completed rerun must return
the same receipt. Any divergent journal byte fails closed. Synthetic sandbox
fixtures never count as ComfyUI execution.

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

The W64-AQA infrastructure exit is accepted at
`Plan/Tracker/Evidence/W64_AQA_E2E_SHADOW_20260722T034500Z/integration_acceptance.json`.
The preceding rectangular-source run is retained as a rejected packet because
visual review caught aspect-ratio distortion that deterministic dimensions did
not. Do not reopen broad infrastructure setup by default. Continue functional
ComfyUI delivery and advance a remaining LLM qualification when a concrete
workflow, artifact, modality, or acceptance gate needs it.

## 10. Role package and current-pod residency discipline

Validate `wave64_runpod_autonomous_role_package_inventory.json` before any
role install or activation action. `OFFICIAL_UPSTREAM_IDENTITY_VERIFIED` means
only that the publisher repository exists; it grants no download, load,
inference, tool, review, or promotion authority. Pin the revision, accept and
record licensing, hash every artifact, keep it under `/workspace`, and issue
separate capacity, calibration, runtime, quality, cost, and failure certificates.
Only one heavy GPU role may be resident unless the exact pair of coordinator
profiles has passed shared-capacity and cleanup qualification. The authorized
singleton 2xA40 watcher is active, but no migration candidate or authority
switch is verified. All required Qwen, InternVL, Omni, Coder, generation, QA,
and MaskFactory packages target `/workspace` on the current production pod and
execute sequentially through the shared coordinator until verified migration
completion.

For the admitted Qwen3-ASR package, use only revision
`7278e1e70fe206f11671096ffdd38061171dd6e5` and the exact twelve-file install
manifest. Require at least 15,435,939,752 free bytes before starting, download
into a private temporary sibling, verify Git-blob identities and both weight
SHA-256 values, and publish atomically without overwrite. Storage installation
must not probe the GPU or lease, load the model, install runtime dependencies,
restart services, or activate the role.

Run the installer only from the pushed commit that matches the admission
manifest. On interruption, retain the private `.installing` directory and rerun
the same bytes; verified files are reused and partial downloads resume. Do not
manually rename or edit staging. On mismatch, preserve the failure evidence and
do not publish. A verified storage receipt changes installation state only; it
does not satisfy capacity, runtime, calibration, quality, cost, fault, or role
activation gates.

Current storage state: Qwen3-ASR-1.7B revision `7278e1e` is installed and
file-verified at its immutable target; a completed replay returned
`REUSED_VERIFIED_INSTALL`. Treat the directory as read-only. Do not create a
`latest` alias, move it into Ollama, import weights, or add service bindings.
The next lease-independent step is an import-only configuration/dependency
preflight that must fail before any tensor allocation.

Use `preflight_wave64_qwen3_asr_dependencies.py` for that gate. The command is
metadata-only: model configuration and installed distribution records are its
entire read authority. Treat `CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED`
as an admitted next-step result, never as permission to upgrade the active
ComfyUI Python environment. Build a hash-locked isolated environment under a
new immutable path only after a separate dependency admission is reviewed.

Current preflight result: config identity passed and dependency action is
required. The active environment lacks both the `qwen-asr` distribution and
Transformers Qwen3-ASR support files. Do not run `pip install` in the active
environment. First resolve and retain an official dependency lock with hashes;
then create an immutable isolated environment and prove an import-only canary.
Model construction, CUDA access, weight load, and inference remain forbidden
until their later gates are explicitly admitted.

For the isolated dependency build, use only
`wave64_qwen3_asr_0_0_6_py312_cu124.pylock.toml` at SHA-256
`241dfaab72cea25fe705693ef715e8368d171720ae3dc37e1c17ecc81b18ba22`.
Require at least 20 GiB free, exact `uv 0.11.30`, exact Python 3.12.13, and the
admitted immutable target. Sync only lock-selected wheels and retain the
installed-distribution manifest and environment tree digest. A successful
build still does not permit importing Qwen-ASR, Torch, or Transformers; that is
a separate canary gate.

Current dependency state: the exact environment is published at the admitted
lock-addressed root, `uv pip check` passed all 105 packages, and the retained
tree digest is `6625aa3c76c411424ede40ce6275d0fb378a1d9a017c205f74ffd356386f7c4a`.
Treat it as immutable. The next gate is an import-only canary with CUDA hidden;
it may import the isolated libraries and inspect registered classes, but it may
not construct the model, open safetensors, allocate tensors, inspect the GPU or
lease, run inference, bind a service, or activate the role.

Run `canary_wave64_qwen3_asr_imports.py` only from the pushed commit that
contains its schema and tests. Set `CUDA_VISIBLE_DEVICES` empty,
`NVIDIA_VISIBLE_DEVICES=none`, both Hugging Face and Transformers offline, and
`PYTHONDONTWRITEBYTECODE=1`. Write one no-overwrite receipt under a commit-named
control root. After the canary, recompute the environment tree digest; any byte
change, network attempt, weight-file open, missing class, or nonempty GPU
visibility rejects the canary.

Audit classification: `socket.__new__` alone is a recorded non-I/O capability
probe. It cannot establish a connection or transfer data and does not pass or
fail the canary by itself. `socket.connect`, `connect_ex`, DNS lookup, listen,
and send operations remain hard-blocked, as do subprocess and shell execution.
Bind remains hard-blocked except for the exact local probe below. Never
generalize either exception to other socket events.

Observed import behavior adds one further exact exception: an IPv4 or IPv6
loopback stream bind at ephemeral port zero may be recorded as a local
capability probe. The classifier must verify loopback address, port zero, and
AF_INET or AF_INET6. Wildcard addresses, external addresses, fixed ports,
malformed addresses, connect, DNS, listen, and send remain hard-blocked. The
accepted receipt is bound to commit `79b24a0a`, and its post-canary environment
tree digest must equal the admitted pre-canary digest. Passing this import gate
does not authorize model construction, weight access, CUDA, inference, a
service, role activation, or any product decision.

Static gate reconciliation: the Qwen3-ASR install admission is the
authoritative `ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE` Apache-2.0 decision.
The storage receipt is the artifact-hash certificate basis because it binds
the exact revision, all twelve admitted source identities, both safetensor
SHA-256 values, and the no-load runtime claims. Do not rerun or reinterpret
these completed static gates.

The exact-revision runtime canary now passes on the current production pod for
one hash-bound retained audio fixture. Invoke it only through an exclusive
shared-coordinator lease and from commit `0854c5b7` or a later reviewed commit.
The parent process must launch CUDA inference in an isolated child, retain the
child's in-process GPU observation, wait for child exit, and make the parent's
post-exit GPU snapshot authoritative for cleanup. The accepted receipt records
`Once upon a midnight.`, English, 5,656 MiB peak GPU use, 10.843-second load,
10.260-second inference, and a +5 MiB post-exit delta. This grants exact-fixture
transcription and current-pod runtime-capacity authority only. It does not grant
general ASR quality, forced alignment, listening, speaker, event, semantic
audio, AV-sync, product-promotion, or service-binding authority. The first
in-process-only cleanup failure remains retained and must not be deleted.

For Qwen3-Omni storage, use only repository
`Qwen/Qwen3-Omni-30B-A3B-Thinking` at revision
`2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b`. The manifest contains exactly
26 files and sixteen safetensor shards totaling 63,440,997,640 bytes. Require
79,547,125,000 free bytes before starting. Publish only by same-volume atomic
rename to the revision-addressed root and never overwrite an existing target.
The installer may download and hash files but may not inspect GPU or lease
state, load the model, install dependencies, restart a service, activate a
role, or produce an audio, AV, or product decision.

Do not install Omni runtime dependencies into active ComfyUI. Its current
official recommendation is Transformers 5.2 or later in a new environment;
resolve, hash-lock, build, and import-test that environment only after the
storage receipt is independently accepted.

Omni download concurrency is bounded: production may use exactly four workers
for this admission. Each worker owns one manifest path; receipt order remains
the manifest order. One through eight is the only accepted implementation
range, serial remains the default, and crash-injection tests remain serial.
After interruption, retain the private `.installing` directory and `.part`
file, then resume the same manifest; never rename partial bytes manually.

Current Omni storage state: revision `2f443cfc` is published at its immutable
target, all 26 source identities passed, and replay returned
`REUSED_VERIFIED_INSTALL`. Treat the directory as read-only. The next safe gate
is an isolated, hash-locked Transformers 5.2-plus dependency environment. Do
not import the model libraries or open weights until a separate import-only
canary is admitted and pushed.

Run `preflight_wave64_qwen3_omni_dependencies.py` only from a pushed commit and
write one no-overwrite receipt in a commit-named control root. This command is
metadata-only; execute it with the active pod Python solely to establish the
dependency gap. A passing config identity does not permit importing libraries,
building the model, reading safetensors, or changing the active environment.

Current Omni preflight result is
`CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED`: exact config identity passed;
Qwen-Omni Utils and installed Transformers support are absent. Do not upgrade
active ComfyUI. Resolve an exact Python target and hash-locked Transformers
5.2-plus closure, review it, then build a new immutable environment.

Use only `wave64_qwen3_omni_transformers_5_2_0_py312_cu124.pylock.toml` at
SHA-256 `a19d160721dfb74cf89bc70eebec10f45b2e6f58b7a109726d658db7d361277c`.
The corrected closure excludes the optional Decord 0.6.0 wheel because its
internal compatibility tag is CPython 3.6 despite its generic filename. It
instead pins `torchvision==0.19.1+cu124`, the deterministic fallback implemented
by Qwen Omni Utils 0.0.9. Never waive `uv pip check` for the Decord artifact.
Reuse the admitted Python 3.12.13 executable; do not install another Python.
Require 25 GiB free, exact uv 0.11.30, and the lock-addressed target. A build
may create the environment and install selected wheels only. It may not import
model libraries, open weights, inspect GPU/lease state, or activate a role.

The corrected isolated environment is installed at the `a19d1607` lock-addressed
target. Its retained receipt binds 75 compatible distributions, 23,097 regular
files, four symlinks, 5,749,106,791 regular-file bytes, and tree SHA-256
`2ae7708993cab848861688ae1b89a2233d61fa02b49e1c14bf51b188a2dd59c5`.
Direct `uv pip check` and full replay both pass, and the active environment
metadata signature is unchanged. This is metadata/build authority only. Do not
import the model libraries until a separately admitted import-only canary is
pushed; that canary must block network, model construction, weight access,
tensors, GPU/lease inspection, inference, service changes, audio/AV authority,
activation, and product authority.

The pushed CPU-only Omni import canary passed from commit `6a1fa04b` with CUDA
hidden and both Hugging Face and Transformers offline flags set. Qwen Omni
Utils, Transformers 5.2.0, Torch 2.4.1+cu124, and TorchVision 0.19.1+cu124
imported, and the config, processor, and conditional-generation classes
resolved. The canary recorded only one socket construction and one exact
loopback/ephemeral bind probe; all network, process, shell, and weight-file
events remained blocked. Post-canary full replay retained the exact environment
tree digest. This closes only the import/class-resolution gate. Runtime and
semantic qualification still require an owned GPU lease and separate evidence.

For the independent juror, use only the official native Transformers repository
`OpenGVLab/InternVL3_5-241B-A28B-HF` at revision `b941ed62...`. Do not use the
custom-code repository or `trust_remote_code`; the native route exposes no
Python files or `auto_map`. Its 136-file source manifest and all 97 weight-shard
SHA-256 values are pinned. The unquantized source is 481,433,908,402 bytes and
fits the latest filesystem-reported 142,706,362,155,008 free bytes. Treat that
filesystem value only as a capacity observation until durable-storage quota and
billing are independently verified. The current pod reported
438,214,877,184 available host-memory bytes and 47,993 MiB free VRAM; the raw
weights leave no safe runtime headroom. Installation and execution therefore
require a separately admitted reproducible current-pod quantized/offloaded
artifact. This runtime constraint must not block other current-pod lanes.
# Authorized guarded 2xA40 watcher (2026-07-22)

One migration watcher is active:
`runpod-us-wa-1-2xa40-guarded-migration-watcher`. Do not create or run another
watcher and do not initiate migration from project tooling. Continue all work
against pod `1q4ji0gg1fkhvt` with the shared capacity coordinator. Change the
authoritative pod only after verified migration-complete evidence binds the
exact candidate, volume `o9qv2ld91c`, 100 GB disk, dual-A40 telemetry,
coordinator rollback checks, and safe old-pod stop. The watcher has no AWS or
pod-termination authority.
