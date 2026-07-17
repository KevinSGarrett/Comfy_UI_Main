# Wave64 Hyperreal Video, Audio/AV, and Operator Application Control Architecture

Updated: 2026-07-16 America/Chicago

## Service boundaries

The controller owns durable intent, aggregate versions, commands, events,
projections, schedules, model decisions, artifact lineage, QA, repair, and
promotion transactions. ComfyUI workers execute immutable workflow releases.
Audio tools execute immutable stem/mix jobs. The browser owns no durable truth.

Core services:

- Project, Character, Scene, Shot, and Timeline service;
- Planner and strict proposal validator;
- exact-bundle model router;
- workflow compiler and release resolver;
- scheduler, lease/fencing, and worker adapter;
- artifact/CAS and media metadata service;
- video frame/track/flow analyzer;
- audio event/source/stem/mix service;
- QA/critic and calibration service;
- diagnosis and repair service;
- promotion/revocation service;
- query projection and notification service;
- policy, role, audit, and credential broker.

## Command and query boundary

Browser commands carry actor, role, target immutable references, parameter
schema/hash, expected aggregate version, idempotency key, authorization, and
confirmation level. They go only to the controller. Browser queries read
projections or explicit authoritative snapshots. WebSocket/SSE events update
views but never become durable authority. Reconnection uses event sequence and
projection version; stale views visibly enter catching-up or reconciling state.

## ComfyUI boundary

The adapter binds a runtime lock, workflow release, exact bundle, lease/fencing
token, deterministic prompt UUID, idempotency key, API body hash, output
namespace, and receipt. It reconciles queue/history/files/CAS after disconnect.
Native ComfyUI queue and history remain volatile observations. App Mode is used
for selected single-workflow controls and outputs. Subgraphs package stable
within-workflow clusters, not the external pass DAG.

## Media stores

- Append-only event store for decisions and transitions.
- Relational projections for projects, timelines, runs, QA, models, and workers.
- Content-addressed artifact store for immutable media and evidence.
- Search index for model reports, character knowledge, assets, and run evidence.
- Secret store isolated from browser payloads and logs.

## API groups

- `/v1/projects`, `/characters`, `/scenes`, `/shots`, `/timelines`;
- `/v1/runs`, `/passes`, `/attempts`, `/commands`, `/events`;
- `/v1/artifacts`, `/lineage`, `/comparisons`, `/repairs`, `/promotions`;
- `/v1/models`, `/bundles`, `/certificates`, `/benchmarks`, `/explanations`;
- `/v1/video`, `/audio`, `/av`, `/qa`;
- `/v1/workers`, `/leases`, `/queues`, `/incidents`, `/reconciliation`;
- `/v1/policies`, `/roles`, `/audit`, `/health`.

Every mutating route is a typed command. Direct CRUD over authority tables is
forbidden. Long operations return accepted command IDs and are observed through
projections/events.

## Application surfaces

### Controller console

Required for cross-workflow state, timelines, runs, comparisons, repairs, model
reports, runtime operations, and audit. It is the primary application.

### ComfyUI App Mode

Required for focused workflow launchers such as Character calibration, Mask
inspection, image preview, video span preview, voice preview, and audio event
preview. Each launcher receives controller-issued immutable inputs and returns
unpromoted artifacts/receipts.

### Optional frontend extension

Provides controller health, artifact deep links, workflow-release identity,
node/subgraph diagnostics, and navigation back to the controller. It never
duplicates the controller's database or promotion logic.

## Reliability

- optimistic aggregate concurrency;
- transactional outbox;
- at-least-once delivery with idempotent consumers;
- monotonically increasing worker fencing tokens;
- content hashes before artifact registration;
- exactly-once promotion transaction by artifact/scope/policy revision;
- ambiguous submissions block failover and promotion until reconciliation;
- projections may lag but display their freshness;
- operator input is preserved across validation and infrastructure failures.

## Performance tiers

- metadata/query interactions: target p95 below 300 ms locally;
- command acceptance: target p95 below 500 ms locally;
- live progress propagation: target p95 below 1 s;
- synchronized comparison seek: target p95 below 250 ms for proxies;
- timeline with 10,000 events: virtualized and interactable at 60 Hz target;
- full-resolution media is proxied; originals remain immutable and on demand;
- preview and final render queues are separate resource classes.

These are initial design targets and require measured revision.

## Deployment

Run the controller, event/projection store, CAS index, and web UI locally by
default. Local and EC2 ComfyUI/audio workers register through explicit runtime
locks and leases. Credentials stay server-side. Offline operation preserves
local projects and queues commands only when policy permits; it never pretends a
remote worker is available.
