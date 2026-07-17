# Autonomous Model Library Ingestion, Qualification, Selection, and Learning Protocol

## Purpose

This protocol governs how source model catalogs become selectable execution
bundles and how every use becomes future evidence. It applies to checkpoints,
LoRAs, adapters, ControlNets, reference models, upscalers, image-edit models,
video models, motion adapters, speech models, voice adapters, Foley and audio
models, lip-sync models, and multimodal analyzers.

## 0. Model-library activation gate

The current state is `deferred_waiting_for_complete_model_download`.
Rows223-260 and the 7,282-row dry-run import are execution-deferred. Do not
start authoritative staging import, registry mutation, acquisition, copying,
installation, loader exposure, ComfyUI model execution, bundle-solver runtime
use, qualification, benchmark, pilot, evidence/profile/certificate generation,
selector or RAG activation, App runtime integration, or production routing.

Pre-activation work is limited to preserving and reviewing the planning
package, validating its static generated artifacts, retaining the completed
read-only archive audit, observing download progress read-only when explicitly
requested, preparing the expected-download scope without operational import,
and communicating the deferred state.

Activation requires all of the following, bound to immutable revisions:

1. user or main-task declaration that the complete intended model library has
   finished downloading;
2. expected-download scope manifest resolving catalog aliases, revisions,
   duplicates, and modalities into the intended binary set;
3. download-completion manifest with stable locations, bytes, hashes, and zero
   temporary or incomplete transfer files;
4. deterministic inventory verification with zero missing, hash-pending,
   corrupt, quarantined, failed, or unresolved in-scope assets; and
5. acknowledgement by main task 019f422f-88b1-7382-872b-21de2089e983 that
   binds the exact package, source, download, inventory, and preservation
   evidence and authorizes a named phase.

The acknowledgement must follow verification. It authorizes no more than its
named phase and cannot substitute for model capability, QA, certificate, role,
or production promotion gates. Any missing or conflicting prerequisite keeps
the gate closed while unrelated project work continues.

## 1. Source admission

1. Create a model-library source snapshot before reading semantic content.
2. Record part order, bytes, SHA-256, archive type, entry count, compression
   ratio, CRC result, path checks, duplicate names, and manifest relationship.
3. Preserve source rows and member paths exactly in staging.
4. Parse CSV, JSON, JSONL, YAML, and Markdown with explicit encoding.
5. Treat spreadsheet formulas, HTML, prompts, descriptions, tags, triggers, and
   instructions as untrusted data.
6. Validate row IDs, reference integrity, embedded JSON, taxonomy values,
   boolean and numeric normalization, and counts.
7. Record source contradictions without silently selecting one value.
8. Set the maximum authority of source-only records to discovery_metadata.
9. Never copy or download a model merely because a source calls it production,
   copy-ready, high-confidence, or top-ranked.
10. Emit a reconciliation report before operational ingestion.

## 2. Identity and deduplication

Use separate IDs for source claim, family, model, source version, file artifact,
content hash, installation instance, execution component, bundle, workflow,
runtime, qualification plan, benchmark result, certificate, report, and route.

The SHA-256 content identity is authoritative for bytes. A name, model ID,
version ID, or source URL is an alias until the file hash is verified. Identical
hashes share one content record but retain every source alias. Different hashes
remain different revisions even when names match.

Version and supersession do not delete history. Historical bundles and
artifacts keep their original references.

## 3. Independent lifecycle axes

Track these axes independently:

- identity: discovered, canonicalized, hash_verified, duplicate_alias;
- binary integrity: unscanned, passed, quarantined, failed;
- classification: unclassified, proposed, reviewed, frozen;
- availability: remote_only, cache_pending, installed_quarantine,
  installed_verified, missing;
- runtime: untested, static_passed, load_smoke_passed,
  functional_smoke_passed, failed, suspended;
- capability authority: research_candidate, benchmark_candidate,
  provisional, shadow_challenger, production_eligible, suspended, revoked,
  superseded;
- evidence: current, stale, contradicted, revoked.

A production route requires every applicable axis and a current scoped
certificate. One status string cannot replace this state vector.

## 4. Asset acquisition and static inspection

Acquisition is a separate authorized job and remains prohibited until the
model-library activation gate authorizes that phase. Once authorized, it must:

1. resolve the exact expected hash and source;
2. download or copy into a quarantine path;
3. verify bytes and size before loader visibility;
4. inspect format and tensor structure without executing remote code;
5. identify architecture, base family, target modules, ranks, alphas, dtypes,
   quantization, and loader assumptions where applicable;
6. compare observed architecture with source claims;
7. scan corruption, malformed tensors, unsafe formats, and duplicate content;
8. record a verified installation instance;
9. expose only allowlisted model roots to ComfyUI;
10. keep failed or mismatched assets unavailable to production.

Content labels do not affect binary-integrity rules.

## 5. Capability hypotheses

Discovery metadata creates hypotheses, not certificates. A hypothesis can
describe likely engine, function, target region, modality, trigger, weight,
mask, control, or conflict. Each field carries source, confidence, freshness,
and conflict information.

The qualification planner converts hypotheses into measurable expected changes
and protected invariants. Generic claims such as quality, realism, anatomy, or
motion must be decomposed into testable metrics and cases.

## 6. Exact bundle construction

The bundle compiler receives a selection context or qualification target and:

1. chooses an exact base model;
2. enumerates compatible component candidates by semantic slots;
3. applies architecture, family, loader, workflow, and runtime edges;
4. enforces one primary component per exclusive slot unless pair proof exists;
5. binds target character instances and target regions;
6. binds weights, order, triggers, prompt translation, controls, and masks;
7. binds workflow, sampler, scheduler, runtime, precision, offload, and hardware;
8. hashes the canonical recipe;
9. records unknown interactions;
10. outputs legal bundles or typed blockers.

The compiler may use bounded beam search to avoid combinatorial explosion.
Greedy filename matching and cross-family component mixing are forbidden.

## 7. Qualification planning

Priority is calculated from:

- active job blockers;
- route demand and expected reuse;
- uncovered capability value;
- confidence and behavior uncertainty;
- source contradiction or risk;
- representative coverage of a family or cluster;
- challenger quality potential;
- expected information gain;
- acquisition, GPU, storage, and review cost.

The planner selects the lowest stage that can answer the current uncertainty.
It does not schedule all 71,800 legacy planned renders automatically.

Qualification plans bind baselines, fixed inputs, expected effects, protected
invariants, seeds, weights, prompts, masks, controls, workflows, budgets,
metrics, gates, early stopping, retry, cleanup, evidence, and target authority.

## 8. Sandbox execution

Each asset or bundle runs in a clean bounded process with:

- read-only model and fixture mounts;
- ephemeral working and output directories;
- no arbitrary network;
- allowlisted loader and workflow modules;
- wall, queue, heartbeat, GPU, RAM, VRAM, disk, and output limits;
- exact environment and dependency hashes;
- resource telemetry and accessed-file logging;
- graceful cancel, forced termination, and cleanup;
- no registry, certificate, or promotion credentials.

An infrastructure failure may be replayed identically when no artifact was
created. A quality failure requires a materially different hypothesis.

## 9. Baseline and sweep protocol

For LoRAs and adapters, begin with a no-adapter baseline and matched adapter-on
cases. Keep parent, crop, masks, prompt intent, negative constraints, workflow,
sampler, seed, and output size fixed.

Run a coarse safe weight or strength grid, then adaptively refine promising
regions. Record best envelope, overcook threshold, instability, target effect,
protected drift, prompt sensitivity, and seed variance. Stop early on repeated
hard failures, no measurable effect, severe regressions, or exhausted budget.

Checkpoint comparisons use equivalent prompt and control contracts but retain
engine-native translations rather than copying raw settings blindly.

Video and audio tests preserve timebase, duration, event, dialogue, and
reference authority. Full playback or listening is part of evidence.

## 10. Benchmark and comparison protocol

Benchmark cases are immutable and split into development, calibration, and
held-out partitions. Candidate identity is hidden from critics where practical.

Use:

- baseline A/B for effect;
- matched-candidate comparisons for route choice;
- component ablations for attribution;
- strength curves for operating envelopes;
- pair and full-bundle tests for interaction;
- decoded-bridge comparisons for cross-engine transitions;
- repeated seeds and cases for stability;
- adversarial and known-failure cases for risk.

Qualification evidence and ordinary production feedback remain distinct.
Holdout results are not used to tune the same policy revision.

## 11. Certificate protocol

A certificate binds:

- exact bundle and component hashes;
- capability scope and pass intent;
- base checkpoint and component order;
- character, instance-count, target, mask, control, and reference constraints;
- weight and parameter envelope;
- workflow, runtime, precision, and hardware;
- benchmark and comparison result IDs;
- sample counts and confidence bounds;
- hard gates and exclusions;
- valid-from, valid-until, drift triggers, revocation, and rollback.

One attractive sample, a load smoke, metadata confidence, or a family result
cannot issue a production certificate.

## 12. Production selection

The request compiler creates a canonical context and immutable context hash.
The selector:

1. retrieves lifecycle-eligible assets and bundles;
2. filters missing, incompatible, uncertified, stale, wrong-scope, wrong-mask,
   wrong-character, prohibited, or resource-ineligible candidates;
3. records every exclusion;
4. retrieves matching performance profiles and certificates;
5. builds applicable metric vectors and confidence bounds;
6. constructs the Pareto frontier;
7. applies a versioned quality, risk, cost, and runtime policy;
8. chooses a certified champion, or returns qualification, fallback, blocker,
   or abstention;
9. optionally records one bounded shadow challenger;
10. emits a complete immutable decision.

Forced model use is diagnostic and non-promoting unless its normal certificate
already covers the request.

## 13. LLM proposal and RAG

The LLM receives:

- a structured job and pass objective;
- a bounded cited evidence bundle;
- top eligible or hypothesis candidates;
- negative evidence, conflicts, missing proof, and uncertainty;
- exact schemas and allowed actions.

It may propose needs, candidates, prompt packages, comparisons, and repair
hypotheses. It must cite immutable IDs. Unknown IDs, stale claims, unsupported
triggers, arbitrary paths, direct workflow graphs, and authority changes are
rejected.

The retrieval service uses structured constraints first, then lexical/vector
similarity. Context manifests record included and excluded records, token
budgets, compaction summaries, conflicts, and missing evidence.

## 14. QA and reviewer protocol

Deterministic services evaluate hashes, formats, dimensions, coordinates,
lineage, masks, ownership, timing, resource limits, and thresholds. Calibrated
metrics evaluate applicable perceptual and acoustic properties. VLM and audio
critics emit observations tied to regions, frames, spans, stems, and artifact
IDs with uncertainty.

Critics cannot promote, certify, execute, or rewrite evidence. Disagreement is
stored and resolved by policy or authorized adjudication.

## 15. Per-use observation

Every terminal attempt writes a model-use observation, including failure and
cancelled attempts. It binds:

- route request and decision;
- context and exact bundle;
- input, parent, target, protected, and output artifacts;
- prompt, trigger, control, mask, and parameter packages;
- runtime and resource telemetry;
- deterministic metrics and critic observations;
- failure, repair, fallback, and QA disposition;
- component-attribution confidence;
- learning eligibility and exclusion reasons.

The report writer produces a cited narrative view but never replaces raw
records.

## 16. Evidence recalculation

Only a versioned batch job updates performance profiles. It:

1. validates source records and terminal QA;
2. removes duplicates and corrupt observations;
3. keeps rejected and negative results;
4. separates qualification, production, shadow, and holdout evidence;
5. checks confounders and attribution;
6. calculates distributions, confidence, risk bounds, and freshness;
7. produces a new profile, report, and selection-feature snapshot;
8. compares the prior snapshot for drift;
9. requests lifecycle or certificate action when thresholds are crossed;
10. leaves prior snapshots immutable and replayable.

## 17. Drift and rollback

Drift monitoring covers model bytes, components, workflows, nodes, runtimes,
hardware, prompts, translations, masks, metrics, corpora, reviewers, and
workload. Affected scope is computed from dependency edges.

Immediate technical suspension includes hash mismatch, corruption,
incompatible load, repeated serious deterministic failure, and certified risk
bounds exceeding policy. The route selector uses the recorded rollback champion
or creates a new fallback decision. Requalification is required before
restoring authority.

## 18. Reporting and App Mode

The operator surface includes:

- source and archive health;
- family, asset, revision, duplicate, and installation views;
- capability and compatibility graph;
- bundle recipes and component conflicts;
- qualification queue and budget;
- baseline, sweep, comparison, and held-out media;
- performance profiles, certificates, failures, and drift;
- model-use history and living reports;
- selection candidates, exclusions, Pareto frontier, rank features, reasons,
  uncertainty, fallback, and challenger;
- LLM/VLM proposals and observations with citations;
- promotion, suspension, revocation, and rollback decisions.

Normal use hides node IDs, raw credential paths, and mutable registry internals.

## 19. Fail-closed conditions

Block or abstain on:

- unknown or mismatched content hash;
- missing or unverified binary;
- architecture or family contradiction;
- unsafe or corrupt format;
- missing workflow or runtime lock;
- unknown required interaction;
- missing target or protected ownership;
- insufficient mask authority;
- absent or stale capability certificate;
- context outside certificate scope;
- resource envelope violation;
- missing ranking feature authority;
- retrieval conflict that changes eligibility;
- hallucinated ID or unsupported LLM claim;
- unauthorized tool, registry, certificate, or promotion action.

Unrelated passes may continue when their dependencies remain satisfied.

## 20. Preservation and handoff

Rows001-220 and their accepted evidence remain unchanged. Rows221-260 are
planning-only until the main task reviews and adopts them. Do not clean,
delete, renumber, merge into a current FLUX lane, or infer completion from the
presence of schemas, examples, or static tests.

The current package is additionally execution-deferred until the complete
intended model download, deterministic inventory verification, and main-task
activation acknowledgement are all recorded. Preservation or planning adoption
does not activate ingestion or qualification.
