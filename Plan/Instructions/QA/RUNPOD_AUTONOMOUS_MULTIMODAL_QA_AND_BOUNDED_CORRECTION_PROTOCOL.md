# RunPod Autonomous Multimodal QA and Bounded-Correction Protocol

Program: `W64-AQA`

## Core rule

Default disposition is `REJECT` or `BLOCKED`. Generation completion, process
success, bucket presence, Git push, model output, or one aggregate score is
never product approval.

## Gate AQA-00: contract and lineage

Require job ID, modality, specification/rubric version, source hashes, workflow
hash, model/component identities, runtime identity, expected outputs, protected
invariants, attempt limits, cost ceiling, and rollback parent.

## Gate AQA-01: deterministic media validity

- Image: decode, dimensions, channels, color/alpha, corruption and encoding.
- Video: container, codec, duration, FPS, frame count, sampled-frame manifest.
- Audio: codec, duration, rate, channels, true peak, clipping, silence, DC,
  loudness and phase where applicable.
- Mask: dimensions, target binding, binary/alpha semantics, empty/full/NaN and
  topology checks.

Any required hard failure blocks review-based promotion.

## Gate AQA-02: reviewer eligibility

Verify role state, exact digest/hash, runtime, GPU envelope, calibration ID,
scope, prompt/rubric/schema versions, expiry, latency/cost budget, and known
limitations. Small smoke models cannot substitute for the strict product role.

## Gate AQA-03: image review

Evaluate prompt/spec adherence, identity and protected morphology, anatomy and
hands, texture/material realism, lighting/shadow, perspective/geometry,
background integrity, seams/compositing, and technical defects. Every finding
has severity, evidence locator, confidence, and repairability.

Deterministic image success never overrides a visual rejection. The canonical
known-bad retained shadow at
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_IMAGE_SHADOW_20260721T223341Z.json`
passes decode, geometry, alpha, dynamic range, entropy, clipping, and sharpness,
yet remains rejected because hand placement misses the lower-upper-arm target
and the contact shadow is unclear. Its exact 32B digest is bound for later
strict replay, but no strict-model runtime or product approval is claimed.

## Gate AQA-04: temporal review

Evaluate sampled frames and metric-selected worst spans for temporal identity,
motion realism, flicker, object persistence, scene/background continuity,
lighting continuity, boundary stability, compression and AV alignment when
applicable. A still-frame PASS cannot approve a video.

The canonical retained sampled-video shadow is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_VIDEO_SHADOW_20260721T224034Z.json`.
It requires full decode and exact geometry/rate/duration/frame-count gates, then
hashes 24 uniform samples and measures duplicate fraction, motion, exposure
jumps, and minimum sharpness. Its separate five-frame contact sheet is a gross
structure diagnostic only. It cannot approve motion realism, temporal identity,
whole-clip continuity, or product quality, and the held 32B runtime is not
reported as executed.

## Gate AQA-05: audio and AV

Deterministic checks are mandatory. ASR, forced alignment, speaker identity,
NISQA, DNSMOS, CLAP, event detection, lip sync, or an omni-modal judge count
only when the exact implementation is qualified. Missing required semantic
audio authority produces `BLOCKED`, not a fabricated PASS.

Audio shadow execution is explicitly two-stage. A deterministic-only shadow may
compile and measure a hash-bound artifact without a visual reviewer or GPU lease;
its only possible success is `PASS_DETERMINISTIC_GATES` with evidence-only
authority. Product release requires `W64-AQA-ROLE-AUDIO-SEMANTIC` and the
independent juror in addition to deterministic approval. Rendered waveform or
spectrogram inspection is technical diagnostic review, never listening, ASR,
speaker, event-semantic, perceptual, or AV-sync approval. The canonical retained
mix proof is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AUDIO_SHADOW_20260721T221732Z.json`.
The paired lossless AV-mux proof is
`Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AV_SHADOW_20260721T222452Z.json`.
It adds full decode, stream-start, and audio/video duration alignment, but its
single decoded-frame diagnostic grants no motion, continuity, AV-sync semantic,
perceptual-audio, or product-visual authority.

## Gate AQA-06: golden masks

Measure completeness, leakage, boundary distance, fine-detail preservation,
holes/islands, target-instance isolation, occlusion, alpha quality, overlay
appearance, and temporal stability. Multiple producer agreement is not ground
truth; disagreements become an uncertainty map and targeted refinement request.
Before measurement, compile a read-only consumer contract binding the source,
candidate mask, integration-accepted golden reference, and target overlay by
hash, geometry, relative path, and target instance. The contract is
candidate-only, forbids MaskFactory writes and product promotion, and grants no
runtime authority even when deterministic gates pass.
Producer-side mask quality, training, golden creation, and runtime qualification
remain outside this repository until MaskFactory supplies its versioned release.
This repository may then validate the immutable consumer boundary, run retained
ComfyUI workflows, measure downstream mask/image/video behavior, and accept or
reject the external release; it may not recreate the producer.

## Gate AQA-06W: workflow integrity and correction

Validate workflow JSON/schema, node availability, typed edges, required inputs,
exact model/LoRA/control identities, engine compatibility, parameter limits,
paths, output capture, and predicted VRAM. A proposed patch must use approved
operations and patch points, apply to a candidate copy, pass static validation,
run in a bounded sandbox, and improve downstream QA without workflow or media
regression. Coding-model prose or a syntactically valid graph is not acceptance.

Before static inspection, independently bind the raw bytes for workflow,
object-info, immutable contract, and model inventory through four distinct
qualified digest-only executor receipts. Recompute the receipt-bundle identity,
each receipt identity and current gateway/executor policy hash, require one job
and contract-ID authority binding, and reject any raw-byte hash change. An
unbound validation is `UNBOUND_STATIC_TEST_ONLY` and cannot support runtime or
acceptance evidence. Receipt-bound static PASS still grants no sandbox,
generation, patch-write, Coder, or promotion authority.

## Gate AQA-07: reviewer response integrity

Reject empty, generic, incomplete, unrelated, non-JSON, schema-invalid,
wrong-frame, missing-score, missing-evidence, or internally contradictory
responses. Permit a bounded schema retry, then another already qualified role,
or emit `REVIEW_BLOCKED`.

## Gate AQA-07T: tool execution and secret isolation

An admission receipt is necessary but not sufficient for execution. The
executor must independently recompute the exact request, decision, gateway
policy, executor policy, actor, job, action, and target binding. The only
currently qualified action is job-scoped `artifact_read`, and its result is a
bounded digest receipt without content exposure, target writes, or network use.

Qualification must retain negative coverage for decision tampering, denied or
unqualified actions, nonempty parameters, traversal, absolute/URI/cross-job
targets, sensitive filenames and suffixes, secret-like content, oversized
or over-time artifacts, symlinks and reparse points, pre-open and during-read
identity changes, policy expansion, weakened controls, receipt overwrite, and
crash-before-publish.
A skipped host symlink fixture does not waive the platform-independent reparse
classification test.

The separate workflow logical executor qualifies only `workflow_inspect` on
`workflow.graph` and `validator_run` on `validate.workflow.v1`, and only in
shadow mode with the exact four-receipt bundle. Retain negative coverage for
other validator targets, production mode, nonempty parameters, role/job/contract
mismatch, policy expansion, limit changes, elapsed time, and any content,
sandbox, write, or network enablement. Every other action remains
`UNQUALIFIED_DENY`.

For the exact workflow candidate stager, retain a successful bounded numeric
copy-on-write fixture plus negative coverage for alternate targets, overwrite,
production mode, nonempty parameters, policy weakening, invalid patch values,
reparse roots, elapsed limits, publication crash, and a base-source race. The
candidate receipt must prove immutable publication and unchanged base bytes,
while all RunPod, GPU, ComfyUI execution, inference, regression, and promotion
flags remain false.

## Gate AQA-08: correction admission

Before any S3 evidence promotion, validate the exact bucket and prefix policy,
content-derived key, conditional-create requirement, SHA-256 checksum, server-
side encryption, version ID, metadata, and replayed object length. A staged
object passes storage qualification only. It cannot substitute for bundle
replay, integration-authority approval, known bucket public-access posture, or
product acceptance.

For a complete S3 bundle transaction, inject a crash before manifest creation
and prove rerun verifies and reuses the already staged content-addressed records.
Require a second live replay with zero creates, all objects reused, and the
manifest verified. Tampered metadata, missing checksums or versions, changed
local records, policy weakening, overwrite, delete, and manifest-first ordering
must fail closed.

The proposed repair must identify exact defects, targets, allowed patch class,
expected benefit, risks, protected checks, parent hash, and rollback. Arbitrary
node creation, shell, secret access, cloud mutation, threshold change, or model
substitution outside the eligible set is rejected.

## Gate AQA-09: improvement and regression

Rerun failed gates, adjacent regions/spans, protected invariants, and a reduced
passing regression set. Retain only if hard gates pass, total applicable score
improves, and no protected category materially regresses. Otherwise revert.

## Gate AQA-10: attempt and no-progress ceilings

- Maximum repair attempts per defect: 2.
- Maximum total generation attempts per job: 4.
- Maximum consecutive no-progress cycles: 2.

An explicitly versioned job policy may be stricter. It may not silently exceed
these defaults or turn exhaustion into PASS.

## Gate AQA-11: evidence and replay

Require immutable artifact, measurement, reviewer, policy, repair, runtime,
cost, decision, and rollback records. Replaying a decision against the same
snapshots must reproduce its eligibility, hard gates, counters, and disposition.

## Gate AQA-12: calibration and drift

Calibration sets include known-good, known-bad, borderline, adversarial,
invalid-input, refusal-prone, identity, temporal, audio, and mask cases.
Measure miss, false-positive, refusal, invalid-JSON, evidence-localization, and
repeatability rates. Suspend a role on digest, prompt, runtime, threshold,
material dataset, or measured-behavior drift until requalified.

## Gate AQA-13: human exception

Human input may resolve subjective intent, approve cost, supply missing licensed
assets, or adjudicate a declared borderline case. It cannot erase evidence or
retroactively convert a failed hard gate. Record actor, reason, scope, expiry,
and the preserved automated decision.

## Promotion rule

Promotion requires all applicable deterministic gates, an eligible strict
review when required, complete evidence, unexpired calibration, no blocking
defect, no protected regression, and integration-authority acceptance. Future
reviewer names or planned metrics have no authority until qualified.
