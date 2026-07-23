# W64-AQA sole-pod qualification campaign

RunPod pod `1q4ji0gg1fkhvt` is the sole active production runtime and storage
platform. CPU-only local package, license, schema, workflow, and evidence work
does not need a lease. Every GPU-affecting action requires the shared capacity
coordinator. If admission is unavailable, switch to another local or current-
RunPod-safe dependency lane; never fall back to AWS, S3, or EC2. Historical
cloud receipts remain immutable audit evidence and W64-AQA-012 is not on the
production critical path.

The authoritative queue is
`Plan/Tracker/Evidence/W64_AQA_SOLE_POD_QUALIFICATION_CAMPAIGN_QUEUE_20260722.json`.
It is a repository plan, not a live coordinator snapshot and not runtime
authority. Replay it before selecting a campaign:

```powershell
python Plan/07_IMPLEMENTATION/scripts/compile_wave64_aqa_sole_pod_qualification_queue.py --validate Plan/Tracker/Evidence/W64_AQA_SOLE_POD_QUALIFICATION_CAMPAIGN_QUEUE_20260722.json
```

The first GPU campaign was the exact Wav2Vec2 expanded-alignment admission. Its
retained 2026-07-22 execution is partially adopted under evidence-set identity
`6f7d8add2df118bbfed3926b472d919765973fbaf472983d37537731aab06c3b`:
three calibration cases and five held-out cases passed under one released 4 GiB
exclusive lease, with process-exit cleanup deltas of 0 MiB and 6 MiB. This
qualifies only the frozen English transcript-bound controls and the exact
non-speech, mismatch, and overlap refusal behavior. Spanish and code-switch
remain diagnostic; general alignment, multilingual, overlap, audio-event,
audio-semantic, product, and promotion authority remain false. An unchanged
Wav2Vec2 rerun is forbidden.

The separate MIT AST campaign reached calibration under a valid 4 GiB exclusive
lease after the 48 kHz-to-16 kHz preprocessing repair. Runtime and process-exit
cleanup passed, but `event_room_ambience` failed the frozen top-three semantic
gate: Silence, Music, and Static ranked above the nearest required-family result,
White noise at rank five. Held-out was not opened. Treat the campaign as
`REJECTED_SEMANTIC_CALIBRATION_TOP3_GATE_MISS`; never retry it unchanged, expand
aliases, or weaken the threshold. The checked-in queue binds this terminal
rejection and selects the next dependency-unblocked role campaign.

Idle GPU telemetry does not authorize execution. Admission must be enabled by
the shared coordinator, and no ComfyUI action may clear, replace, or override a
foreign recovery state or lease. Only one GPU campaign may be resident at a
time. Alternative-pod watching and external inference remain disabled.

Use the queue's remaining dependency-unblocked role entries in sequence. The
broad audio-semantic role remains blocked by the rejected MIT AST dependency. A
package is prepared only when exact identity or revision, project
license acceptance, installed artifact digest, and role binding are all
present. A local digest with unverified upstream revision, an upstream model
name without installed bytes, or the provisional InternVL3.5-8B package cannot
stand in for the declared 241B independent juror. Golden-mask handling remains
a read-only consumer lane until MaskFactory publishes a versioned release.

For every role: bind the exact checkpoint, runtime, prompt, corpus and matrix;
acquire one exact lease; run calibration; freeze thresholds; run held-out once;
compile the capacity/quality/repeatability/refusal certificate; verify cleanup;
release; and keep activation false until Codex acceptance. Never infer broad
quality, juror, golden-mask, activation, or promotion authority from this queue.

Qualification reports must label every fixture `calibration` or `held_out` and
bind the execution-matrix SHA-256. Calibration fixtures require at least two
runs and are the only source of repeatability metrics. Every held-out fixture
must have exactly one run; repeated held-out execution is a contract failure,
not additional confidence. A certificate with matrix-identity drift must be
suspended.

The current matrix-bound deterministic campaign is accepted at
`Plan/Tracker/Evidence/W64_AQA_DETERMINISTIC_ROLE_QUALIFICATION_20260723T004500Z`.
Use its executor only in `validate` mode. The retained output directory is an
immutable guard: `execute` must fail before any held-out re-execution. Its
certificate is operational only for deterministic 1024-square image technical
gates and matrix-declared out-of-scope refusal. It is not semantic QA.

Validate the inactive generation candidates before using the generation queue
entry:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_generation_stack_registry.py
```

The selected `W64-AQA-GEN-FLUX2-KLEIN-4B-FP8` record proves exact promoted
storage identity and candidate ordering only. It is deliberately non-executable.
Do not remove its license-acceptance, text-encoder/VAE dependency, workflow,
coordinator lease, model-load/cleanup, capacity, quality, or failure-injection
blocks until separately retained evidence passes. Never infer generation
runtime or quality authority from a promoted model file or a registry binding.

Replay the selected Flux.2 Klein dependency identity before any companion
transfer or workflow work:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_dependency_bundle.py
```

The bundle is identity-complete, not current-pod-complete. Promote only the
exact `qwen_3_4b.safetensors` hash and exact Klein VAE hash through a separate
atomic storage transaction. Never substitute the retained Flux.2 Dev VAE: its
size and hash differ from the Klein companion. Storage promotion still does not
authorize `object_info`, model load, generation, visual QA, activation, or
product promotion.

Validate the prepared companion storage transaction with:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_model_storage_transaction.py
```

`PASS` means only that the non-executable plan is internally consistent. Before
execution, resolve every blocker and issue a new exact transaction state with a
fresh content ID. Never edit the current record to imply that quota, remote
targets, permit, acquisition, transfer, or promotion occurred. Never overwrite
a hash-different target or delete anything outside the transaction-owned
staging directory.

Validate the companion provenance decision before any acquisition or transfer:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_companion_provenance.py
```

The BFL 4B family Apache-2.0 label and the exact Comfy-Org companion identities
are separate facts. The selected consolidated text encoder and Comfy VAE are
byte-distinct from BFL's Diffusers distributions, and the Comfy-Org repository
has no model card, exact-artifact license metadata, or retained provider
declaration linking those packaged bytes to the upstream license. Until one of
the decision's explicit resolution artifacts is retained and accepted, keep
exact companion redistribution, project license acceptance, acquisition,
storage mutation, runtime, activation, and promotion false. Do not repeat the
same web/license probe against an unchanged repository; advance workflow, node,
and dependency-version binding instead.

Before selecting a new major batch, changing the pursuing goal, or accepting a
completion claim, read the latest finalized audit from the sole active
`comfy-ui-main-timed-probe-anti-loop-supervisor`. Adopt its recommendation or
record an evidence-backed rejection. This six-hour automation is read-only and
must not dispatch workers, mutate the repository, obtain leases, contact cloud
runtimes, or change authority. Every other recurring ComfyUI automation stays
paused unless the user explicitly changes that policy.

Validate the selected static workflow and dependency contract with:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_workflow_contract.py
```

The official workflow-template bytes are an immutable upstream reference, not
the selected execution graph. They contain an unselected base branch and a
non-FP8 distilled filename. Use only the separately hash-bound 13-node API
candidate for the selected FP8 stack after its remaining gates resolve. Never
silently rename a model at submission time, run both upstream branches, or
infer current-pod node/dependency availability from the local checkout.

Static contract PASS proves JSON graph integrity, exact model names, four-step
sampling parameters, node-source coverage, local installed-template equality,
and local dependency observations. It does not prove current-pod object info,
dependency parity, model resolution, execution, output quality, capacity,
cleanup, failure isolation, activation, or promotion.

Validate the Wave42 object-info admission contract before any quarantined
custom-node import:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_wave42_object_info_admission_contract.py
```

Static PASS binds the exact 77-file quarantine, both workflow hashes, all 17
custom-node pins, the five project evidence inputs, and the commercial DWPose
overlay. The workflows contain 40 serialized types, but `Note` is a frontend-
only non-executable annotation, so the object-info canary requires exactly 39
executable types. The candidate must expose
`Wave64CommercialDWPosePreprocessor` and must not expose the legacy
`DWPreprocessor` implementation.

Do not run the optional `--object-info` evaluation until the foreign
MaskFactory recovery owner clears its state and one exact `comfyui_main` lease
is granted. The canary must be disposable, no-network, no-secret, and limited
to imports plus `/object_info`; it may not create an ONNX or model session,
submit a workflow, perform GPU inference, or write outside its transaction-
owned evidence directory. Object-info PASS grants only import and schema
compatibility for that retained snapshot. It does not grant model resolution,
model load, workflow execution, quality, activation, or promotion.
# Qwen3-VL 4B static admission update (2026-07-22)

`W64-AQA-PKG-QWEN3VL4` has exact official-manifest identity and accepted
Apache-2.0 project-use licensing. Treat the manifest digest as the immutable
runtime identity. Do not infer operational or quality authority. Keep the
fast-triage campaign in queue sequence 5 and require fresh shared-coordinator
admission, exact model/prompt identity, calibration and held-out partitions,
refusal checks, cleanup proof, and Codex acceptance before activation.
# Guarded migration watcher coexistence (2026-07-22)

Qualification campaigns continue on pod `1q4ji0gg1fkhvt` under the shared
coordinator. The singleton watcher
`runpod-us-wa-1-2xa40-guarded-migration-watcher` may observe and qualify only
its exact US-WA-1 Secure Cloud 2xA40 migration target. It grants no campaign
lease, creates no product authority, and does not change the active pod until
verified migration-complete evidence is accepted. Never start a competing
watcher or an independent migration.

# FLUX.2 Klein current-pod reconciliation gate (2026-07-22)

Validate the additive current-pod reconciliation before relying on FLUX.2
object-info or component-presence claims:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_current_pod_reconciliation.py
```

PASS grants only these current-pod facts: the 13 selected API graph node types
are visible, loader options include the three planned filenames, and the
diffusion model plus Qwen text encoder match their exact planned hashes. The
live VAE is hash-different and is the known FLUX.2 Dev variant, so exact Klein
VAE identity remains false. Never infer model resolution from filename-only
loader visibility.

The probe is CPU-only and required no lease because it did not load a model,
submit a workflow, mutate storage, or affect GPU state. Any later VAE move,
copy, rename, download, or promotion is a shared-storage mutation and requires
the exact coordinator permit plus a fresh transaction. Preserve the existing
Dev VAE; never overwrite or delete it. Model load, smoke, cleanup, capacity,
quality, failure injection, activation, and promotion remain GPU-gated and
false.

Validate the prepared FLUX.2 dependency overlay with:

```powershell
python Plan/07_IMPLEMENTATION/scripts/validate_wave64_aqa_flux2_klein_dependency_overlay_admission.py
```

PASS proves the live version mismatch, exact two-wheel resolution, immutable
overlay tree, and CPU-mode import compatibility only. The live port-8188
service remains unchanged. Attaching the overlay to a disposable ComfyUI instance or
loading any model is a later lease-bound action.

## Campaign executor rollout lane

W64-AQA-019 is the CPU-safe orchestration and evidence-compaction lane for the sole production RunPod architecture. Its static schemas, journal, CAS/Merkle, result seal, policy, role families, coordinator adapter contract, renderer, proposed-delta compiler, and exact 18-task CPU shadow require no GPU lease. They grant no model, media, workflow, reviewer, golden-mask, runtime, or product authority.

The role registry remains `BLOCKED_UNQUALIFIED`. After static and crash/restart replay acceptance, a 5–10-artifact isolated image/short-video/audio shadow may run only when its exact generator, deterministic QA, primary reviewer, independent juror, arbiter, audio/Omni, repair, and evidence roles are independently qualified. Each GPU phase requires a fresh valid shared-coordinator lease; CPU-only work does not. A passing small multimodal shadow permits only a 25–100-artifact qualification expansion, not production promotion or long-duration operation.
