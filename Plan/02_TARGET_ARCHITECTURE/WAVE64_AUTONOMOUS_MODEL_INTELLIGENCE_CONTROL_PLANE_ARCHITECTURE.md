# Wave64 Autonomous Model Intelligence Control Plane Architecture

## Component map

    Wave30 and external catalogs
        -> model-library download readiness activation gate
        -> source admission and immutable claim store
        -> normalization, identity, dedupe, and lifecycle service
        -> compatibility and architecture graph
        -> installation and runtime inventory
        -> execution-bundle compiler
        -> qualification scheduler and sandbox executor
        -> benchmark, comparison, and QA services
        -> evidence aggregation, profiles, reports, and certificates
        -> contextual selector and challenger policy
        -> multimodal pass router and ComfyUI execution plane
        -> per-use observation stream
        -> drift, revocation, rollback, and future selector snapshots

    RAG service -> bounded LLM/VLM roles -> structured proposals/observations
                                      |
                           deterministic validator, tool gateway,
                           policy engine, and event store

The activation gate currently stops the pipeline before authoritative source
admission. The metadata archive audit and static planning package may exist on
the left side of the gate, but the 7,282-row staging import and every
operational or empirical service remain inactive until complete-download,
inventory-verification, and main-task acknowledgement evidence passes.

## Service boundaries

### Model-library activation gate

Owns the expected-download scope, download-completion manifest, observed binary
inventory report, main-task acknowledgement, and phase authorization. Its
current state is `deferred_waiting_for_complete_model_download` and its runtime
permission is false. It fails closed on missing, incomplete, stale,
contradictory, mismatched, or superseded evidence. Passing this gate authorizes
only the explicitly named staged-ingestion or qualification phase; it does not
certify any model, bundle, LLM/VLM role, artifact, or production route.

### Source admission

Reads archives and registries in staging, records byte and row provenance,
validates paths and formats, and emits immutable source claims. It cannot create
runtime authority.

### Identity and lifecycle

Owns content identity, aliases, family/version/artifact separation, dedupe,
availability, state axes, transition rules, supersession, suspension, and
revocation. It accepts only authorized lifecycle decisions.

### Compatibility graph

Owns architecture fingerprints and compatible, incompatible, conditional, and
unknown edges among exact component hashes, loaders, workflows, engines, and
runtimes. Unknown is not compatible.

### Bundle compiler

Constructs legal checkpoint, component, workflow, prompt, sampler, and runtime
recipes. It uses constraint solving and bounded beam search. It cannot silently
substitute a similarly named component.

### Qualification scheduler

Prioritizes candidates by demand, capability value, uncertainty, risk,
information gain, and cost. It controls leases, stages, retries, early stopping,
clean process isolation, and budgets.

### Sandbox executor

Runs static inspection, load smoke, A/B, sweep, ablation, bridge, and held-out
jobs. It has no arbitrary network, Git, registry-write, credential, or
promotion authority. Model files are read-only and outputs are ephemeral until
the artifact service records them.

### Evidence and report service

Stores raw observations, experiment designs, metric outputs, reviewer
observations, failures, telemetry, and QA dispositions. Versioned aggregation
jobs produce profiles and reports without mutating raw evidence.

### Certificate service

Applies deterministic sample, confidence, hard-gate, freshness, runtime, and
rollback policies. It issues, expires, suspends, and revokes exact
capability-bucket certificates. It is separate from generation and review.

### Contextual selector

Retrieves candidates, performs hard filtering, resolves matching certificates,
constructs the Pareto frontier, calculates replayable utility, applies the job
policy, and returns a champion, shadow challenger, fallback, qualification
request, blocker, or abstention.

### Autonomous intelligence services

The planner compiles semantic needs and pass proposals. The retrieval analyst
resolves cited evidence. The prompt composer creates engine-native prompt
packages. Router advice explains candidates but does not calculate authority.
VLM and audio critics emit scoped observations. The report writer summarizes
only cited records. All outputs are schema-constrained.

### Policy and tool gateway

The validator resolves every ID and hash. The gateway authorizes allowlisted
actions and owns credentials. The policy engine owns execution admission,
learning eligibility, certificate, promotion, suspension, and revocation
decisions.

## Data stores

- Append-only event store: lifecycle, qualification, execution, QA, selection,
  learning, drift, and policy events.
- Source-claim store: original archive fields and immutable citations.
- Registry projections: current asset, lifecycle, availability, compatibility,
  bundle, certificate, champion, and role-stack views.
- Evidence store: benchmark and per-use structured records.
- Object store: models, input fixtures, generated media, logs, comparisons, and
  reports addressed by content hash.
- Feature store: versioned selection features derived from evidence snapshots.
- Retrieval index: structured, lexical, and vector views with authority,
  freshness, conflict, and negative-evidence metadata.

SQLite may host single-node events and projections. PostgreSQL becomes the
multi-executor target. Object storage remains content-addressed. A cache is
never authoritative.

## APIs

Representative versioned endpoints:

- GET /v1/model-library/activation-gate
- POST /v1/model-library/activation-gate/evaluate
- POST /v1/model-sources/admit
- POST /v1/model-sources/reconcile
- GET /v1/model-assets/{asset_id}
- POST /v1/model-assets/{asset_id}/inspect
- POST /v1/model-bundles/compile
- POST /v1/model-qualification/jobs
- GET /v1/model-qualification/jobs/{job_id}
- POST /v1/model-selection/requests
- GET /v1/model-selection/decisions/{decision_id}
- POST /v1/model-observations
- GET /v1/model-reports/{subject_id}
- POST /v1/model-certificates/decisions
- POST /v1/model-drift/events
- POST /v1/autonomy/retrieve
- POST /v1/autonomy/proposals
- POST /v1/autonomy/tool-actions

All mutation endpoints require idempotency, actor, correlation, causation,
schema version, registry snapshot, and authorization policy bindings.
Every model-source, asset, bundle, qualification, selector, certificate, RAG,
and App runtime mutation endpoint must reject requests while the model-library
activation gate is not active for that exact phase.

## Candidate retrieval at scale

The LLM does not scan the library. A deterministic query compiler maps the
selection context to:

1. lifecycle, installed-location, engine, asset type, pass-intent, target,
   control, mask, certificate, resource, and freshness filters;
2. compatibility graph joins and bundle construction;
3. lexical and embedding retrieval for source claims, failure notes, and
   contextual similarity;
4. top-K empirically eligible bundles plus negative evidence and exclusions.

Approximate nearest-neighbor search may improve discovery latency, but it cannot
override structured hard constraints. Registry snapshot hashes make retrieval
and decisions replayable.

## Evidence ranking

Metric distributions retain count, mean, quantiles, dispersion, confidence
intervals, serious-failure rate, missingness, reviewer version, and evidence
age. Benefits use lower confidence bounds and harms use upper confidence bounds.
Sparse evidence is therefore conservative.

The job policy chooses weights for applicable dimensions. Identity-sensitive
passes heavily weight identity and morphology preservation. Regional passes
weight target effect, protected drift, mask leakage, seams, and whole-image
regression. Video adds temporal identity and transition continuity. Audio adds
event accuracy, intelligibility, voice identity, artifacts, loudness, and sync.

The selector retains the full metric vector and Pareto set in its decision.
Weights and normalization are registry versions, not free-form LLM outputs.

## Exploration

Qualification mode can use expected information value, Bayesian uncertainty,
or contextual bandit methods to choose tests. Shadow mode can compare a
challenger against the champion without changing production. Production mode
does not select an uncertified model for a required pass.

Exploration budgets, eligible pools, blinding, early stopping, and learning
eligibility are separate policies. Results do not promote from one sample.

## Evidence feedback

Each run records bundle-level evidence. Component-level learning requires an
attribution experiment. A batch job:

1. validates terminal QA and lineage;
2. rejects corrupted, duplicated, confounded, stale, or leakage-prone records;
3. partitions qualification, production, shadow, and holdout evidence;
4. recalculates profiles and features;
5. detects drift and significant changes;
6. emits a new evidence snapshot and report;
7. requests, but does not self-approve, lifecycle or certificate changes.

## Failure handling

- Missing hash or asset: block or enqueue acquisition.
- Wrong engine or architecture: exclude before ranking.
- Unknown interaction: keep candidate-only and enqueue comparison.
- Load failure or corruption: record failure and suspend affected runtime scope.
- OOM: invalidate or narrow the hardware envelope, not necessarily the model.
- QA failure: preserve accepted parent and record the failed bundle/context.
- Reviewer disagreement: retain both observations and apply calibration policy.
- No certified candidate: fallback through a new decision, qualification, or
  abstention.
- Drift: suspend affected certificate and route to a current rollback champion.
- Store or queue interruption: reconstruct from events and reconcile artifacts
  before resuming.

## Security and trust

Archive paths, CSV cells, descriptions, tags, prompts, model-card text, source
URLs, and model binaries are untrusted inputs. Admission protects against path
traversal, decompression bombs, malformed rows, formula injection, unsafe model
formats, remote-code loaders, and prompt injection. External text is never
interpreted as tool instructions.

Inference services have no arbitrary filesystem, shell, Git, cloud, credential,
or promotion authority. The gateway uses named allowlists and records denied
actions. Registry writes, certificate decisions, and artifact promotion require
deterministic policy and authorized state transitions.

## Growth path

Revisit SQLite, local vector search, and single-heavy-GPU scheduling when
concurrent executors, millions of observations, or multiple runtime pools make
them the measured bottleneck. PostgreSQL, a dedicated vector index, and a
distributed queue are target evolutions, not initial prerequisites.
