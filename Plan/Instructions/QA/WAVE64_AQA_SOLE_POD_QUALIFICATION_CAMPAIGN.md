# W64-AQA sole-pod qualification campaign

The authoritative queue is
`Plan/Tracker/Evidence/W64_AQA_SOLE_POD_QUALIFICATION_CAMPAIGN_QUEUE_20260722.json`.
It is a repository plan, not a live coordinator snapshot and not runtime
authority. Replay it before selecting a campaign:

```powershell
python Plan/07_IMPLEMENTATION/scripts/compile_wave64_aqa_sole_pod_qualification_queue.py --validate Plan/Tracker/Evidence/W64_AQA_SOLE_POD_QUALIFICATION_CAMPAIGN_QUEUE_20260722.json
```

The first GPU campaign is the exact Wav2Vec2 expanded-alignment admission.
Acquire a fresh `comfyui_main` / `comfyui_model_qualification` exclusive lease,
run calibration, freeze the observed thresholds, run held-out once, verify child
exit and VRAM cleanup, release the lease, and retain immutable receipts. The
second GPU campaign is the exact MIT AST AudioSet event admission with the same
partition discipline. Never inspect held-out results before threshold freeze or
repeat an unchanged campaign.

Idle GPU telemetry does not authorize execution. Admission must be enabled by
the shared coordinator, and no ComfyUI action may clear, replace, or override a
foreign recovery state or lease. Only one GPU campaign may be resident at a
time. Alternative-pod watching and external inference remain disabled.

After the two supporting audio campaigns, use the queue's role entries in
sequence. A package is prepared only when exact identity or revision, project
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

The deterministic campaign is accepted at
`Plan/Tracker/Evidence/W64_AQA_DETERMINISTIC_ROLE_QUALIFICATION_20260722T163804Z`.
Use its executor only in `validate` mode. The existing output directory is an
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
