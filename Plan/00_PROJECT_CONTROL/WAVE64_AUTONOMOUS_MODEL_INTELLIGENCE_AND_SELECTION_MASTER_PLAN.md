# Wave64 Autonomous Model Intelligence and Selection Master Plan

Updated: 2026-07-16 America/Chicago

## Decision

Wave64 Rows221-260 are an additive child program of Rows165-172, 197-204,
209-212, and 217-220. The program converts a large discovery library into an
evidence-backed Model Intelligence and Qualification System for character,
image, video, audio, and AV workflows.

The Wave30 Model OS archive is admitted as immutable discovery metadata. It is
not a runtime registry and does not grant selection authority. Its tags,
triggers, folders, selector scores, estimated accuracy, family cards, and
copy-ready labels are useful priors for retrieval and qualification priority.
They cannot prove that an asset exists locally, loads, is compatible with an
exact checkpoint, produces the intended effect, preserves a character, fits the
runtime, or is safe to promote.

Planning coverage is not implementation, installed model evidence, visual or
audio QA, certificate authority, runtime proof, or release completion.

## Current activation state: execution deferred

The complete intended model library has not yet been downloaded. The current
gate is `deferred_waiting_for_complete_model_download`, and no bulk Wave30
staging import, operational-registry mutation, acquisition, installation,
bundle-solver runtime use, qualification, benchmark, pilot, selector/RAG
activation, App Mode runtime integration, certificate generation, or
production routing is authorized.

Before any of that work begins, the main task must receive the user's explicit
download-complete signal and the control plane must bind:

1. an expected-download scope manifest defining every intended model binary;
2. a download-completion manifest with immutable paths or URIs, bytes, and
   hashes and no incomplete transfer files;
3. a deterministic binary-inventory verification report reconciling the
   intended scope with zero missing, hash-pending, corrupt, or unresolved
   assets; and
4. a main-task activation acknowledgement binding the exact package, source,
   download, inventory, and preservation evidence.

The 7,282 catalog rows are not automatically 7,282 distinct binary downloads;
aliases, revisions, duplicate hashes, and modalities must be reconciled in the
expected scope. Unless the user explicitly revises that intended scope, the
gate requires every intended model to be present and verified. Archive
metadata and the 187 copy-ready labels cannot satisfy this gate.

Until it passes, only planning preservation, static schema/registry/test
validation, the already-completed read-only archive audit, read-only download
progress observation when requested, and main-task status communication are
allowed. Missing or conflicting evidence fails closed and unrelated project
work may continue.

## Source facts that shape the design

- The cumulative package is a clean raw-split ZIP stream of five parts,
  367,893,277 bytes, with 675 text members and no model weights.
- It describes 7,282 artifacts, 3,770 model families, 13 selector profiles, and
  650 precomputed recommendations.
- It contains 3,278 FLUX-labeled, 890 Pony-labeled, 875 WAN-video-labeled, and
  836 SDXL-labeled artifacts, plus other families.
- 5,056 artifacts are caution-first-pass candidates, 2,039 require manual
  review, and only 187 are copy-ready for hash verification.
- Every artifact QA state is open. The classification accuracy score is an
  internal-consistency heuristic, not a measured generative-quality score.
- Wave12L planned 4,978 ComfyUI jobs and 71,800 renders but explicitly generated
  no images; several referenced job, sweep, score, prompt, and rubric assets are
  absent.
- The current Main model registry has tens of operational records, not a
  qualified mirror of the 7,282-artifact discovery library.

## Required outcome

The completed system must:

1. admit large source catalogs without converting claims into authority;
2. identify every exact asset by immutable hash, revision, aliases, and lineage;
3. fingerprint engine, architecture, loader, base-family, adapter, and runtime
   compatibility before GPU execution;
4. construct exact selectable execution bundles rather than selecting filenames
   or model brands;
5. qualify assets and bundles through progressive, baseline-controlled,
   capability-specific tests;
6. issue scoped certificates and bucket-specific champions, never a universal
   best-model label;
7. select first-pass, specialist, video, speech, Foley, audio, and AV bundles
   using hard filtering followed by conservative empirical ranking;
8. generate an immutable observation and report for every use;
9. update performance profiles through reproducible batch evidence jobs;
10. detect drift, suspend affected scope, revoke certificates, and roll back;
11. provide cited retrieval and bounded LLM/VLM roles without promotion or
    arbitrary tool authority;
12. expose selection reasons, comparisons, failures, reports, certificates, and
    qualification queues through the operator application.

## Three authority planes

### Discovery plane

Contains source claims, Civitai metadata, Wave30 taxonomy, tags, triggers,
folders, sample metadata, classification confidence, and selector priors. These
records answer what might be relevant and what should be tested next.

### Operational plane

Contains exact hashes, storage instances, binary inspection, architecture
fingerprints, installed paths, loader visibility, workflow bindings, runtime
envelopes, and exact execution bundles. These records answer what can actually
run and under which technical constraints.

### Empirical plane

Contains benchmark cases, outputs, metrics, critic observations, comparisons,
per-use observations, confidence intervals, failure distributions, performance
profiles, certificates, champions, drift, suspension, and revocation. These
records answer what has been proven to work for an exact context.

No fact automatically moves from one plane to the next.

## Selectable unit

The router selects:

    engine family
    + exact base checkpoint or generative model hash
    + VAE and encoder hashes
    + ordered LoRA, adapter, ControlNet, reference, or audio component bundle
    + weights, target instances, target regions, and prompt triggers
    + workflow/API graph hash
    + sampler, scheduler, denoise, and prompt-translation profile
    + custom-node and runtime lock
    + precision, offload, hardware, and resource envelope
    + capability certificate set

A LoRA is not independently selectable when its behavior depends on the
checkpoint, weight, prompt, target, mask, workflow, or neighboring adapters.

## Autonomous decision flow

    job and pass objective
      -> canonical selection context
      -> structured and semantic candidate retrieval
      -> lifecycle, availability, compatibility, certificate, mask, and
         resource hard filters
      -> exact legal execution bundles
      -> matching capability-bucket evidence
      -> Pareto frontier
      -> conservative contextual utility ranking
      -> certified champion, bounded shadow challenger, explicit fallback,
         qualification request, or abstention
      -> execution
      -> deterministic and calibrated critic QA
      -> per-use observation and report
      -> versioned batch profile update
      -> future ranking snapshot

The LLM translates intent, proposes alternatives, designs tests, summarizes
evidence, and explains trade-offs. Deterministic services resolve IDs, enforce
compatibility, calculate ranking features, authorize tools, apply hard gates,
issue certificates, and promote or revoke.

## Progressive qualification

### L0 catalog admission

Validate archive structure, source row counts, IDs, references, encodings,
taxonomy values, JSON embedded in CSV, duplicate groups, and source
contradictions. Authority gained: discovery only.

### L1 binary admission

For a prioritized asset, acquire or locate the exact file, verify the expected
hash, scan its format, inspect tensors and architecture, identify base-family
and loader expectations, and record an installation instance. Authority gained:
binary integrity and architecture evidence.

### L2 isolated load smoke

Load the exact bundle inside a bounded process with a read-only model mount,
ephemeral outputs, memory and time limits, clean teardown, and no arbitrary
network or registry writes. Authority gained: load-smoke evidence for one
runtime envelope.

### L3 functional baseline A/B

Run adapter-off and adapter-on cases with matched prompts, seeds, masks,
workflow, and parent artifacts. Sweep an initial parameter range and measure
target effect and protected invariants. Authority gained: functional candidate.

### L4 capability benchmark

Evaluate held-out characters, scenes, regions, poses, references, masks,
resolutions, and failure cases for one capability bucket. Authority gained:
certificate candidate.

### L5 bundle interaction

Test single components, high-risk pairs, ablations, and the complete recipe.
Authority gained: bundle-specific evidence. An asset certificate does not imply
all stacks are safe.

### L6 cross-engine bridge

Test decoded-artifact round trips, region transforms, color and grain
continuity, identity, seams, and whole-artifact regression for an exact
base/specialist engine pair. Authority gained: pair-specific bridge evidence.

### L7 shadow routing

Keep the current champion authoritative while challengers are proposed or run
without replacing accepted parents. Measure quality, risk, cost, and regret.

### L8 production eligibility

The deterministic policy engine issues a scope-bounded, expiring certificate
only after sample floors, hard gates, evidence completeness, rollback, and
reviewer calibration pass.

## Scalable strategy for 7,282 assets

Brute-force qualification of every model and every pair is neither intelligent
nor affordable. The scheduler first deduplicates identical hashes and clusters
related revisions, architectures, functions, and embeddings. It prioritizes:

    expected route demand
    x uncovered capability value
    x classification or behavior uncertainty
    x expected information gain
    x risk reduction
    / estimated qualification cost

Installed assets, job blockers, high-demand capabilities, current champions,
credible challengers, coverage gaps, high-risk ambiguity, and representative
cluster members run first. Long-tail assets remain searchable and can trigger
on-demand qualification. Family evidence may support discovery and shared
technical facts but never substitutes for artifact and bundle behavior proof.

## Contextual ranking policy

Hard eligibility precedes every score. For eligible candidate c, context x, and
capability bucket b:

    quality_lcb =
        weighted lower confidence bound of required benefit and preservation

    risk_ucb =
        weighted upper confidence bound of serious failures, drift, OOM,
        instability, and regression

    utility(c | x, b) =
        quality_lcb
        - risk_ucb
        - latency, memory, storage, transfer, and monetary cost
        - evidence staleness and scope-distance penalties
        - cross-engine bridge and cache-miss penalties
        + declared cache and batching affinity

Metadata classification priors affect discovery and qualification priority,
not production-quality utility. Required dimensions and weights are frozen by
a versioned job policy. Candidate selection begins with a Pareto frontier so a
single composite number does not erase quality, preservation, reliability, and
resource trade-offs.

New or sparse candidates use uncertainty-aware exploration only in
qualification or shadow modes. Production required passes exploit a current
certificate-covered champion. If no candidate covers the context, the correct
result is qualification enqueued, fallback selected through a new immutable
decision, or abstention.

## Per-use intelligence and reports

Every attempt creates a model-use observation containing the selection request,
decision, candidate exclusions, complete bundle, context, parent and output
hashes, prompts, controls, masks, resource telemetry, metrics, critic
observations, failures, repair, and disposition.

Normal production observations update the complete bundle. Individual component
conclusions require controlled A/B, ablation, or otherwise qualified causal
evidence. Mask, prompt, pose, source, workflow, and parent failures are retained
as confounders rather than attributed to the selected LoRA.

The living report card shows:

- exact asset and bundle identities;
- discovery claims versus measured facts;
- certified, provisional, shadow, untested, suspended, and revoked scopes;
- best and worst contexts;
- base checkpoints and bundle partners;
- prompt and weight response curves;
- target improvement and protected-region preservation;
- identity, anatomy, pose, mask, temporal, audio, and sync behavior;
- sample counts, confidence bounds, outliers, and serious failures;
- VRAM, RAM, latency, load, cache, and cost distributions;
- current certificates, expiry, drift, fallback, and rollback;
- cited generated summaries and separately identified operator annotations.

The execution that produced an observation cannot directly rewrite its score or
promote itself. A versioned recalculation job validates learning eligibility,
keeps holdouts isolated, aggregates immutable records, produces a new profile
revision, and optionally submits a lifecycle decision.

## Content treatment

Content-based suppression is false. Adult or NSFW concepts remain ordinary
descriptive taxonomy and benchmark context. They do not cause hiding,
deprioritization, or a separate model-selection blocker. Binary integrity,
compatibility, provenance, runtime, ownership, evidence, and quality gates
remain technically identical across content categories.

## LLM and VLM architecture

Separate roles are required for planning, prompt composition, retrieval
analysis, router advice, defect classification, image/video review, audio
review, reporting, summarization, and drift triage. Each role receives an
evidence bundle small enough for its context window. It never receives an
unbounded dump of 7,282 cards.

Every self-hosted role binds an exact model revision, runtime, quantization,
template, structured-output parser, context limit, batching policy, hardware
envelope, and role qualification certificate. Exact stacks must pass held-out
grounding, schema, uncertainty, hallucinated-ID, citation, prompt-injection,
tool-authorization, and task-quality benchmarks before activation.

The planner and router advisor may propose model needs, candidates, comparisons,
and repair hypotheses. The VLM and audio critic may emit artifact-, region-,
frame-, span-, or stem-bound observations. They cannot change registry truth,
execute arbitrary graphs, access credentials, satisfy deterministic hard gates,
issue certificates, or promote their own outputs.

## Model change and drift

Model hash, base checkpoint, component order, weight range, VAE, encoder,
workflow, node lock, sampler, prompt template, translator, runtime, precision,
offload, driver, hardware, mask provider, metric, benchmark corpus, or reviewer
changes can invalidate scope. The drift controller identifies affected
certificates, route decisions, cached computations, reports, and fallbacks.

Hash mismatch, corruption, incompatible load, repeated serious deterministic
failure, or a certified risk bound crossing policy suspends new selection for
the affected scope. Requalification, revocation, or rollback occurs through an
immutable policy decision.

## Storage and operations

SQLite in WAL mode may support the single-node prototype event and projection
stores. PostgreSQL is the multi-executor target. High-volume observations,
artifacts, and benchmark media belong in the event/object stores; Git contains
schemas, policies, frozen fixtures, signed snapshots, reports, certificates,
and release projections.

The qualification scheduler uses leases, idempotency, bounded retries,
heartbeats, cancellation, resource admission, clean-process isolation, and
content-addressed caching. The local 8 GiB development GPU retains the existing
7,127 MiB initial certification ceiling and one heavy GPU lease. Heavy
generation and heavy planner/VLM service do not share it without a measured
certificate.

## Implementation sequence

1. Preserve and hash the source archives and current Wave64 package.
2. Freeze schemas, authority tiers, lifecycle axes, IDs, and source crosswalk.
3. Keep all model-library execution deferred while the intended model binaries
   are still being downloaded.
4. After the user reports completion to the main task, freeze the exact
   expected-download scope and download-completion manifest.
5. Run deterministic inventory reconciliation over the completed download and
   require zero missing, hash-pending, corrupt, incomplete-transfer, or
   unresolved in-scope assets.
6. Require the main task to acknowledge the verified evidence and explicitly
   activate staged ingestion. This acknowledgement does not grant model
   capability or production authority.
7. Run the full Wave30 staging import and contradiction report.
8. Build hash, dedupe, static inspection, installation, and compatibility
   services.
9. Build the exact execution-bundle compiler and solver.
10. Build isolated smoke, A/B, sweep, comparison, and benchmark execution.
11. Build evidence aggregation, profiles, reports, certificates, drift, and
   rollback.
12. Build hard-filtered contextual ranking and bounded exploration.
13. Build cited RAG, structured proposals, tool gateway, and role qualification.
14. Qualify the 187 copy-ready pilot plus representative high-value installed
    candidates without treating copy-ready as runtime-ready.
15. Run held-out and shadow selection across image, video, audio, and AV.
16. Integrate Model Explorer and route explanation into the operator app.
17. Expand the long tail by demand, coverage, risk, and information value.
18. Complete release, recovery, security, rollback, and final main-task
    adoption. Final release adoption is separate from the earlier bounded
    activation acknowledgement.

## Definition of done

This program is done only when the archive import reconciles; every selectable
bundle resolves exact hashes and compatibility; every production route is
covered by a current certificate; selection replay produces the same candidate
set and decision from the same snapshot; every use produces an attributable
report; model and reviewer drift can suspend and roll back; shadow floors pass;
the operator can inspect the full reasoning and evidence; and the main task
records formal adoption. Static planning validation alone cannot satisfy done.
The complete-download, deterministic inventory, and main-task activation gate
must also remain traceable to the exact source and package revisions.

## Authoritative Rows221-260 requirement catalog

### Row221 - Wave30 Source Snapshot and Integrity Admission

- Workstream: `W64-MI-GOV`; phase: `MI-00`; domain: `source_governance`.
- Action: Register every multipart archive part, logical ZIP hash, patch relationship, inventory count, CRC result, source defect, and authority ceiling without importing model authority.
- Acceptance: The five-part stream and patch are hash-bound; unsafe paths, missing parts, duplicate names, manifest inconsistencies, and the metadata-only authority ceiling are explicit.
- Dependencies: Row149, Row152, Row165, Row201
- Runtime truth: `not_started_static_control_allowed`; activation gate required: `false`.

### Row222 - Discovery, Operational, and Empirical Authority Tiers

- Workstream: `W64-MI-GOV`; phase: `MI-00`; domain: `source_governance`.
- Action: Separate source claims, normalized discovery metadata, installed operational assets, runtime observations, scoped certificates, and production selection authority.
- Acceptance: No Wave30 score, tag, copy-ready label, Civitai sample, or LLM statement can satisfy a runtime capability or promotion gate.
- Dependencies: Row150, Row152, Row165, Row166, Row209, Row221
- Runtime truth: `not_started_static_control_allowed`; activation gate required: `false`.

### Row223 - Model Asset Identity, Deduplication, and Version Lineage

- Workstream: `W64-MI-GOV`; phase: `MI-00`; domain: `source_governance`.
- Action: Resolve family, model, version, file, SHA-256, duplicate group, supersession, preferred revision, and storage identity as separate immutable entities.
- Acceptance: Aliases converge on one content identity while distinct revisions remain independently testable and historically addressable.
- Dependencies: Row043, Row051, Row152, Row153, Row221, Row222
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row224 - Model Lifecycle, Decision Authority, and Revocation State Machine

- Workstream: `W64-MI-GOV`; phase: `MI-00`; domain: `source_governance`.
- Action: Define discovery, admitted, installed, load-proven, benchmark-candidate, provisionally-certified, production-certified, suspended, revoked, rejected, and superseded transitions.
- Acceptance: Every transition has one authority, evidence prerequisites, expiry, rollback, and immutable event history; an LLM cannot certify or promote.
- Dependencies: Row150, Row152, Row197, Row198, Row201, Row221, Row222, Row223
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row225 - Strict Model Asset Intelligence Card

- Workstream: `W64-MI-CAT`; phase: `MI-01`; domain: `catalog_intelligence`.
- Action: Normalize Wave30, Civitai, local, S3, EC2, ComfyUI, hash, loader, taxonomy, prompt, trigger, compatibility, rights, availability, and evidence fields into a strict versioned card.
- Acceptance: Each card distinguishes claimed, inferred, observed, measured, and certified facts and carries source-level citations and freshness.
- Dependencies: Row044, Row054, Row165, Row221, Row222, Row223
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row226 - Capability, Role, Region, Modality, and Defect Ontology

- Workstream: `W64-MI-CAT`; phase: `MI-01`; domain: `catalog_intelligence`.
- Action: Map checkpoints, LoRAs, adapters, controls, video, audio, speech, Foley, upscalers, and analyzers to normalized pass intents, targets, defects, controls, and risks.
- Acceptance: The selector can query exact functional meaning across character, scene, image, video, audio, and AV work without relying on filenames.
- Dependencies: Row051, Row054, Row153, Row155, Row165, Row173, Row209, Row225
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row227 - Family, Artifact, Revision, Bundle, and Certificate Separation

- Workstream: `W64-MI-CAT`; phase: `MI-01`; domain: `catalog_intelligence`.
- Action: Model discovery operates at family level while execution, evidence, and certification bind exact artifact revisions and execution bundles.
- Acceptance: No family summary is used as artifact proof and no artifact certificate silently transfers to another hash, workflow, adapter bundle, or runtime.
- Dependencies: Row152, Row156, Row165, Row223, Row224, Row225
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row228 - Hybrid Retrieval Index and Immutable Citation Projection

- Workstream: `W64-MI-CAT`; phase: `MI-01`; domain: `catalog_intelligence`.
- Action: Build structured filters, full-text search, embeddings, taxonomy joins, evidence joins, and materialized summaries over immutable source and empirical records.
- Acceptance: Every retrieved fact resolves to a versioned record and evidence reference; stale, conflicting, missing, and superseded records remain visible.
- Dependencies: Row051, Row054, Row198, Row202, Row221, Row225, Row226, Row227
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row229 - Engine, Base-Family, Loader, and Adapter Hard Compatibility Graph

- Workstream: `W64-MI-COMPAT`; phase: `MI-02`; domain: `compatibility_and_bundles`.
- Action: Represent exact compatible and incompatible edges for engines, checkpoints, LoRAs, VAEs, encoders, controls, schedulers, nodes, workflows, quantizations, and media adapters.
- Acceptance: Wrong-family assets and unproven cross-family assumptions fail before ranking with typed reasons.
- Dependencies: Row036, Row044, Row054, Row065, Row165, Row166, Row225, Row226, Row227
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row230 - Exact Model Execution Bundle Compiler

- Workstream: `W64-MI-COMPAT`; phase: `MI-02`; domain: `compatibility_and_bundles`.
- Action: Compile one selectable unit from base model, LoRA stack, VAE, encoders, controls, workflow hash, node/runtime lock, sampler, precision, hardware, and prompt adapter.
- Acceptance: Selection and evidence bind the complete reproducible bundle rather than a model brand or standalone LoRA.
- Dependencies: Row156, Row165, Row166, Row170, Row171, Row227, Row229
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row231 - LoRA and Component Interaction, Conflict, and Attribution Graph

- Workstream: `W64-MI-COMPAT`; phase: `MI-02`; domain: `compatibility_and_bundles`.
- Action: Record pairwise and higher-order compatibility, dominance, cancellation, overcook, trigger collision, regional overlap, identity drift, and checkpoint dependence.
- Acceptance: Unknown combinations are not assumed safe; tested interactions are scoped and combinatorial testing is prioritized by use and risk.
- Dependencies: Row013, Row014, Row015, Row165, Row173, Row174, Row225, Row229, Row230
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row232 - Availability, Residency, Resource, and Runtime Envelope

- Workstream: `W64-MI-COMPAT`; phase: `MI-02`; domain: `compatibility_and_bundles`.
- Action: Bind local/S3/EC2 availability, bytes, load time, VRAM/RAM, precision, offload, warm-cache affinity, concurrency, and failure telemetry to each bundle.
- Acceptance: No route assumes an absent asset or starts outside a measured resource envelope; quality is not silently downgraded under pressure.
- Dependencies: Row042, Row044, Row061, Row062, Row063, Row166, Row205, Row206, Row208, Row230
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row233 - Progressive Model Qualification Funnel

- Workstream: `W64-MI-QUAL`; phase: `MI-03`; domain: `qualification`.
- Action: Implement source admission, static scan, install/hash proof, loader smoke, baseline A/B, parameter sweep, capability benchmark, stack-interaction, shadow, and certification stages.
- Acceptance: Expensive rendering is reserved for eligible high-value or high-uncertainty candidates while every skipped stage and authority ceiling is explicit.
- Dependencies: Row037, Row038, Row044, Row054, Row063, Row165, Row209, Row210, Row221, Row224, Row229, Row230, Row232
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row234 - Canonical Multimodal Model Benchmark Corpus

- Workstream: `W64-MI-QUAL`; phase: `MI-03`; domain: `qualification`.
- Action: Create fixed and held-out cases for character identity, anatomy, skin, hair, clothing, pose, interaction, environment, motion, speech, Foley, audio, and AV behavior.
- Acceptance: Cases bind approved inputs, baselines, seeds, prompts, masks, controls, expected effects, protected invariants, metrics, and adjudicated outcomes.
- Dependencies: Row109, Row147, Row172, Row183, Row188, Row192, Row196, Row209, Row210, Row225, Row226, Row233
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row235 - Parameter, Trigger, Prompt, Weight, Denoise, and Seed Sweep Engine

- Workstream: `W64-MI-QUAL`; phase: `MI-03`; domain: `qualification`.
- Action: Generate reproducible baseline-controlled sweeps with early stopping, adaptive refinement, matched seeds, fixed workflows, and parameter-response curves.
- Acceptance: Best envelope, overcook threshold, instability, prompt sensitivity, and failure regions are measured without treating a single attractive output as proof.
- Dependencies: Row064, Row167, Row173, Row174, Row233, Row234
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row236 - Capability-Bucket Certificate, Expiry, and Requalification

- Workstream: `W64-MI-QUAL`; phase: `MI-03`; domain: `qualification`.
- Action: Certify exact bundles only for measured pass intent, target, checkpoint, stack, character count, mask tier, resolution, workflow, runtime, and hardware buckets.
- Acceptance: Certificates include sample floors, confidence, hard-gate results, validity window, exclusions, fallback, and revocation links; there is no universal best-model certificate.
- Dependencies: Row059, Row063, Row165, Row172, Row209, Row211, Row224, Row230, Row233, Row234, Row235
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row237 - Canonical Model Selection Context Envelope

- Workstream: `W64-MI-SELECT`; phase: `MI-04`; domain: `contextual_selection`.
- Action: Compile character revisions, scene/shot/take, pass objective, defect, target/protected scope, modality, references, controls, masks, quality, runtime, cost, risk, and downstream needs.
- Acceptance: Equivalent requests canonicalize identically while materially different targets, owners, engines, stacks, or constraints remain separate evidence buckets.
- Dependencies: Row153, Row154, Row155, Row161, Row162, Row165, Row168, Row173, Row189, Row193, Row225, Row226
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row238 - Hard Eligibility Solver and Scalable Candidate Retrieval

- Workstream: `W64-MI-SELECT`; phase: `MI-04`; domain: `contextual_selection`.
- Action: Apply lifecycle, availability, engine, bundle, certificate, mask, control, character, resource, evidence-freshness, and prohibited-combination filters before ranking.
- Acceptance: The solver can search thousands of assets without scoring ineligible entries and returns complete typed exclusion evidence.
- Dependencies: Row165, Row166, Row168, Row228, Row229, Row230, Row231, Row232, Row236, Row237
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row239 - Conservative Contextual Evidence Ranker and Pareto Frontier

- Workstream: `W64-MI-SELECT`; phase: `MI-04`; domain: `contextual_selection`.
- Action: Rank eligible bundles with quality lower-confidence bounds, risk upper-confidence bounds, preservation, failures, resource cost, bridge cost, cache affinity, evidence freshness, and policy weights.
- Acceptance: Scores are replayable, calibrated, versioned, uncertainty-aware, and scoped; metadata priors cannot outrank measured production evidence.
- Dependencies: Row063, Row167, Row168, Row208, Row209, Row211, Row225, Row228, Row236, Row237, Row238
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row240 - Exploration, Candidate Branch, Abstention, and Fallback Policy

- Workstream: `W64-MI-SELECT`; phase: `MI-04`; domain: `contextual_selection`.
- Action: Use bounded offline or shadow exploration for uncertain candidates, allow certified production champions for required passes, and emit abstention or explicit fallback when evidence is insufficient.
- Acceptance: Exploration never mutates an accepted parent or silently promotes a cold-start model; every candidate branch has budget, stop, QA, and learning eligibility.
- Dependencies: Row049, Row063, Row168, Row175, Row199, Row203, Row224, Row233, Row236, Row238, Row239
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row241 - Per-Use Model and Bundle Observation Record

- Workstream: `W64-MI-OBS`; phase: `MI-05`; domain: `observation_and_learning`.
- Action: Record why a bundle was selected, exact context, parents, prompts, controls, outputs, telemetry, deterministic metrics, critic observations, defects, repair outcome, and final decision.
- Acceptance: Every execution produces an attributable report even when rejected, blocked, cancelled, or excluded from learning.
- Dependencies: Row043, Row051, Row054, Row156, Row167, Row184, Row188, Row192, Row196, Row198, Row209, Row230, Row237, Row239
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row242 - Contextual Model Performance Profile and Living Report Card

- Workstream: `W64-MI-OBS`; phase: `MI-05`; domain: `observation_and_learning`.
- Action: Aggregate eligible observations by exact capability bucket with sample counts, confidence intervals, response envelopes, success/failure modes, drift risks, recommended uses, and exclusions.
- Acceptance: Reports distinguish metadata priors, qualification trials, production observations, reviewer opinions, and certified facts and preserve all source evidence.
- Dependencies: Row054, Row063, Row209, Row211, Row225, Row227, Row233, Row236, Row241
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row243 - Append-Only Evidence Recalculation and Continual Learning Job

- Workstream: `W64-MI-OBS`; phase: `MI-05`; domain: `observation_and_learning`.
- Action: Recalculate profiles and ranking features from eligible immutable observations through versioned batch jobs rather than mutable online self-training.
- Acceptance: A production run cannot directly rewrite its own score; updates are reproducible, leakage-checked, reversible, and separated from holdout evaluation.
- Dependencies: Row043, Row048, Row051, Row062, Row198, Row202, Row207, Row211, Row224, Row239, Row241, Row242
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row244 - Behavior Drift, Regression, Suspension, Revocation, and Rollback

- Workstream: `W64-MI-OBS`; phase: `MI-05`; domain: `observation_and_learning`.
- Action: Detect model, workflow, runtime, dependency, prompt-template, data, reviewer, and workload drift and bind affected certificates, routes, cached results, and fallbacks.
- Acceptance: Critical drift suspends new selection immediately; requalification or rollback restores authority without rewriting prior decisions.
- Dependencies: Row047, Row048, Row049, Row054, Row059, Row063, Row152, Row200, Row207, Row208, Row212, Row224, Row236, Row242, Row243
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row245 - Autonomous Planner, Prompt, Router-Advisor, Reviewer, and Summarizer Role Contracts

- Workstream: `W64-MI-LLM`; phase: `MI-06`; domain: `autonomous_intelligence`.
- Action: Define bounded planner, prompt composer, retrieval analyst, router advisor, defect classifier, VLM critic, audio critic, report writer, and summarizer inputs and outputs.
- Acceptance: Every role has exact authority, tools, context budget, schemas, escalation, and prohibited actions; no role promotes its own proposal or observation.
- Dependencies: Row150, Row197, Row201, Row203, Row224, Row228, Row237, Row241
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row246 - Registry-Grounded RAG, Evidence Bundle, and Context Memory Contract

- Workstream: `W64-MI-LLM`; phase: `MI-06`; domain: `autonomous_intelligence`.
- Action: Retrieve only versioned packages, model cards, certificates, benchmark results, failures, current run state, and policy records with citations, freshness, conflict, and compaction metadata.
- Acceptance: The LLM sees a bounded evidence packet rather than the whole library; missing or conflicting evidence causes uncertainty, alternatives, or abstention rather than invention.
- Dependencies: Row051, Row054, Row198, Row202, Row203, Row207, Row225, Row228, Row242, Row245
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row247 - Schema-Constrained Proposal, Prompt Package, Tool Gateway, and Policy Decision

- Workstream: `W64-MI-LLM`; phase: `MI-06`; domain: `autonomous_intelligence`.
- Action: Require typed planner proposals, prompt packages, reviewer observations, tool actions, policy decisions, uncertainty, evidence IDs, alternatives, and denied-action records.
- Acceptance: Invalid IDs, unsupported claims, arbitrary paths, unallowlisted workflows, credential access, registry mutation, and promotion attempts fail deterministically.
- Dependencies: Row035, Row048, Row049, Row051, Row062, Row197, Row201, Row202, Row203, Row224, Row245, Row246
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row248 - Exact Self-Hosted Role Stack, Benchmark, Shadow, and Activation Control

- Workstream: `W64-MI-LLM`; phase: `MI-06`; domain: `autonomous_intelligence`.
- Action: Register model, revision, runtime, quantization, chat template, parser, context, batching, hardware, fallback, and role-specific benchmark certificates.
- Acceptance: Only a role-qualified exact stack activates; planner and reviewer changes run in shadow, preserve prior decisions, and cannot silently change route or promotion behavior.
- Dependencies: Row044, Row054, Row063, Row201, Row202, Row203, Row204, Row205, Row208, Row210, Row211, Row245, Row246, Row247
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row249 - Deterministic, Perceptual, VLM, Audio-Critic, and Playback QA Ensemble

- Workstream: `W64-MI-QA`; phase: `MI-07`; domain: `model_qa`.
- Action: Evaluate technical validity, effect accuracy, target fidelity, identity, anatomy, preservation, mask leakage, temporal behavior, audio quality, sync, resource stability, and lineage.
- Acceptance: Hard facts remain deterministic, critics emit scoped observations with uncertainty, and no single scalar or reviewer overrides a hard failure.
- Dependencies: Row016, Row017, Row018, Row021, Row030, Row032, Row033, Row034, Row060, Row103, Row106, Row131, Row141, Row209, Row211, Row233, Row234, Row241, Row245
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row250 - Baseline, Counterfactual, Ablation, and Stack Attribution Protocol

- Workstream: `W64-MI-QA`; phase: `MI-07`; domain: `model_qa`.
- Action: Compare no-adapter baselines, matched seeds, component ablations, alternative bundles, strength curves, and protected outputs to isolate actual model contribution.
- Acceptance: A model receives credit or blame only where the experiment can attribute the change; checkpoint, prompt, seed, mask, and stack confounding are recorded.
- Dependencies: Row063, Row167, Row172, Row176, Row209, Row211, Row231, Row233, Row234, Row235, Row241, Row249
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row251 - Critic Calibration, Disagreement, Bias, and Adjudication Control

- Workstream: `W64-MI-QA`; phase: `MI-07`; domain: `model_qa`.
- Action: Measure false accept/reject rates, region and modality coverage, reviewer-version effects, uncertainty calibration, disagreement, and escalation against held-out adjudicated cases.
- Acceptance: Reviewer observations remain candidate evidence until calibration and policy authorize their exact use; disagreement is retained rather than averaged away.
- Dependencies: Row060, Row063, Row203, Row204, Row209, Row210, Row211, Row245, Row248, Row249
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row252 - Selection Decision Audit, Model Report, and Promotion Gate

- Workstream: `W64-MI-QA`; phase: `MI-07`; domain: `model_qa`.
- Action: Package candidate exclusions, rank features, uncertainty, selected bundle, execution, QA, comparison, observation, performance delta, certificate, and policy outcome.
- Acceptance: Every future run can explain why a model was selected, how it behaved, what changed in its report, and whether the evidence may affect future selection.
- Dependencies: Row035, Row043, Row051, Row054, Row059, Row063, Row150, Row156, Row167, Row168, Row198, Row209, Row211, Row236, Row239, Row241, Row242, Row249, Row250, Row251
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row253 - Event Store, Evidence Store, Feature Store, and Projection Boundaries

- Workstream: `W64-MI-OPS`; phase: `MI-08`; domain: `operations`.
- Action: Persist source records, lifecycle events, bundles, trials, observations, certificates, reports, ranking features, decisions, and audit projections with immutable IDs and snapshots.
- Acceptance: State reconstructs from append-only events, feature values resolve to evidence, and no mutable cache becomes authority.
- Dependencies: Row043, Row051, Row062, Row198, Row200, Row202, Row207, Row221, Row224, Row228, Row241, Row242, Row243, Row252
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row254 - Resource-Aware Batch Qualification and Active-Learning Scheduler

- Workstream: `W64-MI-OPS`; phase: `MI-08`; domain: `operations`.
- Action: Prioritize installed, high-value, high-usage, high-risk, coverage-gap, and uncertain candidates; schedule sweeps, comparisons, and requalification under GPU, storage, time, and cost budgets.
- Acceptance: The scheduler avoids all-pairs explosion, respects leases and thermal/resource envelopes, resumes safely, and records why work was prioritized or deferred.
- Dependencies: Row042, Row061, Row062, Row063, Row199, Row200, Row205, Row206, Row207, Row208, Row233, Row234, Row235, Row240, Row243
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row255 - Model Explorer, Qualification Queue, Comparison, Report, and Route-Explanation UX

- Workstream: `W64-MI-OPS`; phase: `MI-08`; domain: `operations`.
- Action: Expose library health, source authority, availability, compatibility, test coverage, certificates, reports, failures, drift, decisions, and side-by-side media without raw node or credential exposure.
- Acceptance: Operators can trace every claim and approve policy changes or exceptions without manually editing graphs or registry bytes.
- Dependencies: Row047, Row051, Row107, Row145, Row202, Row213, Row214, Row215, Row216, Row228, Row242, Row252, Row253, Row254
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row256 - Telemetry, Capacity, Security, Backup, Recovery, and Degraded-Mode Control

- Workstream: `W64-MI-OPS`; phase: `MI-08`; domain: `operations`.
- Action: Monitor ingestion, index freshness, queue depth, load failures, QA latency, ranking drift, certificate health, storage, costs, untrusted metadata, model scans, tools, and recovery points.
- Acceptance: Outage or saturation changes routes only through declared policies; source text and model files cannot obtain tool, credential, registry, or promotion authority.
- Dependencies: Row040, Row041, Row042, Row047, Row048, Row049, Row061, Row062, Row063, Row200, Row205, Row206, Row207, Row208, Row212, Row244, Row247, Row253, Row254
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row257 - Wave30 Dry-Run Import, Reconciliation, and Exception Report

- Workstream: `W64-MI-REL`; phase: `MI-09`; domain: `release_and_adoption`.
- Action: Map all 7,282 artifacts and 3,770 families into discovery records, reconcile 675-member archive defects and selector/status disagreements, and emit no operational promotion.
- Acceptance: Counts, hashes, duplicates, missing fields, blocked rows, stale reports, absent visual-test assets, and migration mappings reconcile or produce typed exceptions.
- Dependencies: Row050, Row051, Row057, Row058, Row212, Row217, Row221, Row222, Row223, Row225, Row226, Row227, Row228
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row258 - Copy-Ready and High-Value Pilot Qualification Tranche

- Workstream: `W64-MI-REL`; phase: `MI-09`; domain: `release_and_adoption`.
- Action: Hash-verify and qualify the 187 Wave30 copy-ready candidates plus a stratified set of installed/high-value models across priority capability buckets.
- Acceptance: The pilot produces real bundles, A/B evidence, reports, scoped certificates, failures, cost measurements, and rollback without treating copy-ready as production-ready.
- Dependencies: Row037, Row038, Row044, Row054, Row063, Row218, Row229, Row230, Row232, Row233, Row234, Row235, Row236, Row249, Row250, Row251, Row252, Row254, Row257
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row259 - Value, Coverage, Risk, and Uncertainty-Driven Library Expansion

- Workstream: `W64-MI-REL`; phase: `MI-09`; domain: `release_and_adoption`.
- Action: Expand qualification by production demand, capability gaps, model diversity, uncertainty, expected value of information, and resource budget rather than archive order.
- Acceptance: Coverage grows measurably while unqualified long-tail assets remain discoverable, on-demand-testable, and excluded from certified production routes.
- Dependencies: Row219, Row233, Row234, Row236, Row239, Row240, Row242, Row243, Row244, Row249, Row251, Row252, Row254, Row258
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.

### Row260 - Autonomous Model Intelligence Release Certification and Main-Task Adoption

- Workstream: `W64-MI-REL`; phase: `MI-09`; domain: `release_and_adoption`.
- Action: Certify schemas, stores, ingestion, bundles, qualification, selection, LLM roles, QA, reports, App UX, recovery, security, rollback, and preservation handoff.
- Acceptance: Rows221-259 are traceable; runtime claims are evidence-backed; no critical gate is open; the main task formally adopts or rejects every additive artifact.
- Dependencies: Row059, Row060, Row066, Row112, Row148, Row204, Row208, Row212, Row216, Row220, Row224, Row236, Row244, Row248, Row252, Row255, Row256, Row257, Row258, Row259
- Runtime truth: `deferred_prerequisites_not_satisfied`; activation gate required: `true`.
