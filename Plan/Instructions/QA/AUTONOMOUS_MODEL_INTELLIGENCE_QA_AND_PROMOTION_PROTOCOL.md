# Autonomous Model Intelligence QA and Promotion Protocol

## Core rule

The model library has two separate QA questions:

1. Is the catalog and classification record internally correct?
2. Does the exact execution bundle measurably work for the requested context?

Wave30 substantially addresses the first question as planning metadata. This
package defines the second and prevents the first from being mistaken for it.

## Gate families

### MI-QA-00 Model-library download readiness and activation

Before L0 or the 7,282-row dry-run import, validate the expected-download scope,
download-completion manifest, stable binary locations, bytes and hashes,
absence of incomplete transfers, deterministic inventory reconciliation, zero
missing/hash-pending/corrupt/quarantined/failed/unresolved in-scope assets, and
main-task acknowledgement of the exact evidence. The current gate is deferred
and `runtime_execution_allowed` is false. Archive integrity, metadata, planning
tests, copy-ready labels, and unrelated installed models cannot pass this gate.

### MI-QA-01 Source and archive integrity

Verify part order, bytes, hashes, ZIP integrity, member counts, path safety,
compression limits, encoding, row counts, unique IDs, references, embedded
JSON, and source-manifest inconsistencies.

### MI-QA-02 Identity and binary integrity

Verify exact SHA-256, size, format, tensor structure, architecture fingerprint,
base family, target modules, loader expectation, corruption, duplicate group,
and installation instance.

### MI-QA-03 Compatibility

Verify engine, checkpoint, VAE, encoder, LoRA, control, scheduler, workflow,
node, runtime, prompt translator, precision, and hardware compatibility.
Unknown is not pass.

### MI-QA-04 Runtime load and resource

Verify clean-process load, bounded output, accessed files, peak VRAM/RAM, wall
time, timeout, teardown, repeatability, and the certified envelope. OOM narrows
or suspends the envelope.

### MI-QA-05 Target effect

Verify that the selected asset or bundle produces the declared effect in the
owned target with sufficient magnitude and correctness.

### MI-QA-06 Protected preservation

Verify identity, morphology, pose, count, ownership, target-external regions,
wardrobe, environment, color, grain, timing, voice, stems, and synchronization
as applicable.

### MI-QA-07 Regional and mask quality

Verify target ownership, mask authority, transforms, leakage, boundary,
seam, crop, padding, feather, denoise, reinsertion, and whole-artifact
regression.

### MI-QA-08 Temporal and audio quality

Verify frame continuity, motion, contact, identity, flicker, transition, event
timing, intelligibility, voice identity, Foley accuracy, artifacts, loudness,
spatial behavior, and AV synchronization.

### MI-QA-09 Attribution

Verify baseline, matched variables, seeds, prompts, masks, workflows,
ablation, confounders, and attribution confidence before updating an individual
component profile.

### MI-QA-10 Evidence and statistics

Verify sample floors, missingness, outliers, negative evidence, confidence
bounds, serious-failure rates, calibration, freshness, holdout separation, and
reproducible aggregation.

### MI-QA-11 Selection replay

Verify registry, feature, policy, certificate, and context snapshots; candidate
exclusions; Pareto frontier; score components; uncertainty; selected bundle;
fallback; challenger; and identical replay from identical inputs.

### MI-QA-12 Autonomous role quality

Verify structured-output validity, ID resolution, citations, evidence
grounding, uncertainty, abstention, prompt-injection resistance, tool
authorization, role task quality, and no unauthorized state change.

### MI-QA-13 Lifecycle and certificate

Verify scope, evidence, authority, expiry, suspension, revocation, rollback,
and requalification. No generator or reviewer approves itself.

### MI-QA-14 Recovery, security, and operations

Verify leases, idempotency, cancellation, restart, event replay, artifact
reconciliation, backups, storage, cache invalidation, least authority, path and
archive attacks, unsafe loaders, and denied tool actions.

## Metric model

There is no universal model score. Applicable metrics are selected by
capability bucket. Each metric records direction, unit, authority, sample count,
distribution, confidence, evidence, and calibration.

Image dimensions include target-effect accuracy, identity similarity,
morphology preservation, pose error, count and ownership, anatomy stability,
skin/hair/material fidelity, protected-region drift, mask leakage, seam,
prompt/control adherence, photoreal coherence, and artifacts.

Video dimensions add temporal identity, flicker, motion, camera, contact,
transition, span-repair boundary, duration, and frame integrity.

Audio dimensions add intelligibility, voice identity, prosody, event accuracy,
timing, acoustic fit, noise, clipping, loudness, spatial coherence, and full-mix
regression.

AV dimensions add frame/sample/PTS alignment, lip and event sync, stream
integrity, mux, duration, and complete playback.

Operational dimensions include load success, serious failure, OOM, peak memory,
latency, throughput, cache behavior, storage, transfer, determinism, and cost.

## Evidence authority

From weakest to strongest:

1. source claim;
2. normalized discovery metadata;
3. static measurement;
4. runtime observation;
5. controlled qualification measurement;
6. calibrated or adjudicated review;
7. scoped certificate.

Higher authority does not erase contradictory lower evidence. It determines
which facts may satisfy a gate.

## Initial qualification floors

The exact threshold registry is calibrated and frozen before production, but
the following minimum structure applies:

- L2 load smoke: at least one successful bounded output and one clean reload;
- L3 functional candidate: baseline plus at least three matched seeds across a
  minimum four-point initial weight or strength sweep;
- provisional bucket evidence: at least 20 paired outputs across at least five
  distinct benchmark cases, with no unresolved hard failure;
- production certificate: at least 50 paired outputs across at least ten cases,
  required hard gates passing, calibrated critic coverage, rollback proof, and
  confidence/risk bounds inside the bucket policy;
- high-risk pair or bundle: single-component baselines, pairwise comparison,
  full-recipe comparison, and protected-invariant QA;
- bridge certificate: at least ten paired source/bridge outputs across at least
  three target classes plus seam and whole-artifact regression;
- shadow challenger promotion consideration: at least ten successful shadow
  comparisons in addition to offline certificate evidence.

Policies may require higher floors by risk, modality, character count, target,
or certificate scope. Floors never transfer to another hash or bundle.

## Existing Wave64 floors retained

- router: at least 100 valid and 100 adversarial fixtures, zero incompatible
  selections;
- single-character image: at least 30 cases across six or more buckets;
- two-character/contact: at least 24 cases across at least three character
  pairs and four interaction buckets;
- video: at least 12 clips including failed-span repair;
- speech: at least 30 held-out utterances;
- Foley: at least 30 held-out events;
- AV: at least 12 complete clips;
- planner: at least 100 held-out requests;
- reviewer: at least 200 adjudicated panels;
- tool gateway: at least 100 adversarial authorization, path, and injection
  cases;
- autonomy: at least 30 complete shadow jobs before activation.

## Wave30 pilot strategy

Do not begin this strategy until MI-QA-00 passes for the exact activated phase.
After activation, do not run all planned 71,800 renders immediately. First:

1. reconcile all 7,282 discovery rows;
2. deduplicate hashes and family/revision clusters;
3. identify the 187 copy-ready candidates and currently installed models;
4. stratify by engine, role, region, modality, demand, uncertainty, and risk;
5. qualify representative assets and high-value job blockers;
6. use early stopping to remove no-effect and high-regression candidates;
7. expand promising candidates into bucket and interaction benchmarks;
8. keep the long tail discoverable and on-demand-testable.

Copy-ready means eligible for verified acquisition, not runtime authority.

## Ranker validation

Validate the ranking policy through:

- deterministic replay from frozen snapshots;
- zero scores for ineligible candidates;
- lower-confidence benefit and upper-confidence risk behavior;
- sparse-evidence conservatism;
- metadata-prior authority ceiling;
- correct Pareto frontier;
- job-policy weight and normalization versioning;
- tie, fallback, abstention, and challenger behavior;
- ranking regret against held-out outcomes;
- subgroup and capability calibration;
- stale evidence and drift response;
- latency with the full discovery registry.

An LLM explanation is not the ranking calculation.

## Critic calibration

For every VLM, video, or audio reviewer stack:

- bind exact model/runtime/template/parser/quantization/context;
- label held-out cases with artifact, region, frame, span, or stem truth;
- measure false accept, false reject, localization, confidence calibration, and
  disagreement;
- include negative, subtle, multi-character, occluded, temporal, and acoustic
  cases;
- prevent candidate identity leakage where practical;
- compare reviewer revisions before activation;
- retain abstention and disagreement;
- revoke or narrow authority on drift.

Critic observations never override deterministic facts.

## Promotion transaction

A certificate or lifecycle promotion is atomic:

1. freeze source, bundle, workflow, runtime, benchmark, metric, reviewer, and
   policy snapshots;
2. validate every reference and hash;
3. verify sample floors and confidence;
4. verify all applicable hard gates;
5. verify no unresolved serious failure or conflicting authority;
6. verify rollback champion and requalification triggers;
7. issue the policy decision;
8. append the lifecycle event;
9. write the certificate and new projection;
10. invalidate affected selection and cache projections;
11. retain all prior records.

Any failure leaves the prior state authoritative.

## Per-use report acceptance

A report is accepted only if it resolves the exact decision, bundle, context,
parents, outputs, metrics, critic observations, failures, learning eligibility,
and evidence snapshot. Generated notes cite evidence and are labeled as
summaries. Operator annotations are separate records. Missing evidence appears
as missing; it is not synthesized.

## Release blockers

Rows221-260 cannot be called complete while any of these remain:

- complete intended model download has not been declared to the main task;
- expected-download scope manifest is absent, stale, or unresolved;
- download-completion manifest is absent or contains incomplete transfers;
- deterministic binary inventory does not reconcile every in-scope asset;
- any in-scope model is missing, hash-pending, corrupt, quarantined, failed, or
  unresolved;
- main task 019f422f-88b1-7382-872b-21de2089e983 has not acknowledged the exact
  download, inventory, package, source, and preservation evidence and activated
  the required phase;
- unresolved archive or row-count reconciliation;
- selectable asset without verified identity and lifecycle;
- selectable bundle without complete component and workflow hashes;
- untested hard compatibility;
- production route without a matching current certificate;
- rank feature without evidence and policy version;
- per-use execution without a terminal observation;
- direct online score mutation;
- uncalibrated critic used as a hard authority;
- LLM with registry, certificate, credential, or promotion authority;
- unrehearsed drift, revocation, restore, or rollback;
- missing main-task adoption and preservation decision.
