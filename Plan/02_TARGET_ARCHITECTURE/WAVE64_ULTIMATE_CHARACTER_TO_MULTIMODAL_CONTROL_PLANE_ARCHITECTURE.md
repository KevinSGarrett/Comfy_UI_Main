# Wave64 Ultimate Character-to-Multimodal Control-Plane Architecture

## Component boundary

```text
Operator / App Mode
        |
        v
Request + Package API
        |
        v
Planner proposal -> deterministic validator -> pass-DAG compiler
                                           |
                                           v
                          Engine/Model Capability Router
                                           |
                     +---------------------+--------------------+
                     |                     |                    |
                 ComfyUI adapter      MaskFactory adapter   Media adapters
                     |                     |                    |
                     +---------------------+--------------------+
                                           |
                                           v
                               Artifacts + deterministic QA
                                           |
                                           v
                                independent VLM observation
                                           |
                                           v
                                deterministic policy engine
                                           |
                             accept | repair | block | rollback

All transitions -> append-only event store -> projections/search/audit UI
```

## Service responsibilities

| Component | Owns | Must not own |
|---|---|---|
| Operator/App Mode | intent, selection, comparison, cancellation, authorized acceptance | raw graph mutation, credentials, autonomous policy |
| Planner | structured proposals and hypotheses | registry truth, execution, promotion |
| Validator/compiler | schema, IDs, compatibility, DAG, state transitions | subjective quality claims |
| Capability router | eligible/ranked execution stacks | invented models, silent fallback |
| Resource scheduler | queues, VRAM/RAM/storage/cost, cache affinity | quality promotion |
| ComfyUI adapter | validate/submit/monitor/reconcile/fetch | durable project state |
| MaskFactory adapter | package/live-draft access, binding validation | gold mutation, truth escalation |
| Deterministic QA | geometry, hashes, masks, timing, format, metrics | unsupported subjective inference |
| VLM reviewer | evidence-bound observations | hard-gate override, tool execution |
| Policy engine | accept/repair/block/rollback from authorized inputs | free-form generation |
| Event store | immutable history and query projections | media bytes as untracked blobs |

## ComfyUI execution adapter

The public local adapter uses `POST /prompt`, WebSocket telemetry filtered by `prompt_id`, terminal `execution_success`/`execution_error`/`execution_interrupted` events, `/history/{prompt_id}`, and `/view`. It connects telemetry before submission and reconciles history after disconnect/restart. The `executed` WebSocket message is node UI data, not a whole-run terminal signal.

The official CLI may be used for supported conversion, validation, node/model inspection, workflow composition, job watching, and cancellation. Project logic remains adapter-neutral because CLI availability and newer job endpoints must be feature-probed against the pinned runtime. First-party Local MCP remains a future adapter, not a dependency.

Every production custom node must be API-compatible. Browser-only extensions and nodes requiring direct client/server interaction are rejected from headless lanes. Workflow locks bind UI workflow hash, submitted API graph hash, ComfyUI/frontend revisions, custom-node versions/commits, Python environment, model hashes, assets, and feature probes.

## Storage

- SQLite/WAL: prototype domain events, idempotency records, projections, queue state, package indexes, QA decisions.
- Content-addressed artifact store: media, masks, controls, prompts, workflows, logs, reports, and manifests.
- Registry files in Git: schema versions, workflow/module entries, model capability cards, execution stacks, compatibility and promotion state.
- Model bytes outside Git: local/S3/EC2 cache with exact hashes.

Events are committed before externally visible state advances. Submissions use deterministic idempotency keys. Reconciliation may rediscover a ComfyUI result but may not duplicate promotion or overwrite artifacts.

## State machine

```text
created -> proposed -> validated -> ready -> submitted -> running
   |          |           |          |          |          |
   |          v           v          v          v          v
   |       rejected    blocked    cancelled   failed    qa_pending
   |                                                    /    |     \
   |                                               accepted repair blocked
   |                                                    |      |
   +----------------------------------------------------+      v
                                                            ready

accepted -> promoted | retained_as_parent | rolled_back
```

No state transition is accepted merely because an LLM emitted the matching word. The policy engine validates the transition, evidence, hashes, and authority.

## Reliability and scaling

- One active GPU-heavy pass per 8 GiB local GPU unless measured concurrency proves safety.
- CPU and lightweight validation may run concurrently within bounded queues.
- Model/cache affinity influences ranking only after hard quality eligibility.
- Backpressure is explicit; queue depth never causes silent quality fallback.
- Every pass has timeout, heartbeat, cancellation, retry budget, and recovery strategy.
- GPU runtime windows bind owner, TTL, watchdog, cost budget, and final stopped-state evidence.
- Multi-executor scaling requires PostgreSQL/advisory locks or another transactional coordinator and shared content-addressed storage.

## Security boundary

Inference servers receive no shell, filesystem, Git, AWS, Jira, MaskFactory gold, or promotion credentials. The tool gateway validates allowlisted operations and path containment. Model servers do not fetch arbitrary remote URLs. Captions, metadata, workflow notes, and visible text are untrusted data. Model/runtime revisions and hashes are pinned; remote code and mutable runtime LoRA loading are disabled unless separately admitted and tested.
