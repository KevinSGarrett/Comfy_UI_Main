# Wave64 Second-Pass Autonomous Workflow and Model Intelligence Assurance Audit

Updated: 2026-07-16 America/Chicago

## Verdict

The strategic baseline is comprehensive and directionally correct. The second
pass closes the highest-risk planning-contract gaps, but it does not claim a
production controller, qualified model library, active self-hosted LLM/VLM,
or certified end-to-end character-to-AV runtime. The truthful state is:

- architecture baseline: complete;
- phase-safe model-library planning and core runtime contract hardening:
  substantially complete;
- canonical migration of every overlapping Rows149-220 record: still open;
- controller, durable event runtime, scheduler, adapters, App/controller UI,
  empirical model qualification, and full release certification: not built.

## Findings closed in this pass

1. The former combined staging-and-qualification state is replaced with an
   ordered ladder: none, staging, qualification, shadow selection, production
   selection. Each state has an exact permission ceiling and one append-only
   transition decision. Download completion can authorize staging only.
2. Expected download scope, download completion, binary inventory
   verification, main-task acknowledgement, and phase transition now have
   strict record contracts. Quarantined assets count as accounted but remain
   runtime-ineligible; missing, hash-pending, or unresolved assets fail closed.
3. The gate is scoped only to the Rows221-260 Model Intelligence program. It
   does not cancel or stall the separately governed FLUX.2 proof lane or the
   MaskFactory task.
4. Model selection now binds typed target/protected contracts, MaskFactory
   ownership, person index, ontology, coordinate transforms, certificate
   requirements, Mode-B draft ceilings, and no-write-gold invariants.
5. Production selection decisions must resolve to an evaluated, eligible,
   certificate-covered, hash-bound bundle on the Pareto frontier. Capability
   certificates, policy decisions, and tool actions receive cross-field gates
   and semantic validators.
6. The ranking policy freezes a replayable numeric v1 baseline: feature
   normalization, confidence methods, weights, missing-data rules, production
   thresholds, tie branching, abstention, assignment probability, and holdout
   controls. It remains subject to versioned empirical recalibration.
7. Every autonomous role remains explicitly inactive until an exact stack,
   role certificate, shadow evidence, tool policy, model-library phase ceiling,
   and separate activation decision all pass. Roles retain no direct execution,
   registry, certificate, credential, or promotion authority.
8. The ComfyUI boundary now has strict contracts for runtime locks, workflow
   releases, idempotent submissions, receipts, safe artifact locators,
   reconciliation, worker leases/fencing, typed event payload envelopes, and
   aggregate transitions.

## ComfyUI runtime truth

ComfyUI is the execution engine, not the durable autonomous authority. Its
queue/history and WebSocket stream are observations that may disappear or
disconnect. The external controller must use an append-only event store,
transactional outbox, unique idempotency keys, runtime leases with fencing,
content-addressed artifact registration, and post-disconnect reconciliation.
An ambiguous submission cannot fail over to another host or promote.

App Mode remains a thin workflow launcher and result surface. Character
Library, multi-workflow DAG state, QA, repair, recovery, model reports, and
route explanations belong to a separate durable controller console or a
purpose-built frontend extension.

Official references:

- https://docs.comfy.org/development/comfyui-server/comms_routes
- https://docs.comfy.org/development/comfyui-server/comms_messages
- https://docs.comfy.org/specs/workflow_json
- https://docs.comfy.org/interface/app-mode
- https://docs.comfy.org/interface/features/subgraph

## Remaining release-critical implementation work

1. Migrate every existing Rows149-220 consumer from its legacy RecordRef form
   to the now-published canonical immutable-reference/deprecation crosswalk.
2. Make `model_execution_bundle` the sole selectable execution unit and bind
   every multimodal route decision to its contextual selection decision.
3. Migrate legacy combined pass records to the now-published separate pass
   specification, execution attempt, diagnosis/repair hypothesis, QA
   evaluation, and promotion/revocation schemas.
4. Replace remaining authority-bearing open payloads with typed schemas and
   semantic validators for DAG acyclicity, ownership, contact reciprocity,
   temporal ordering, certificate freshness, and scope containment.
5. Mark the legacy static orchestrator compiler non-authoritative and prevent
   App or production entrypoints from invoking it.
6. Implement the controller kernel, SQLite-equivalent event store, outbox,
   CAS, fake ComfyUI adapter, restart/cancellation/fault-injection tests, then a
   no-model real-runtime smoke when authorized.
7. Implement Character/Scene/Shot publishers, MaskFactory Mode A adapter,
   single- then two-character image slices, video/audio/AV clocks and repair,
   and finally the operator surfaces.
8. Only after the user reports all intended models downloaded: reconcile the
   frozen scope, enter staging, then advance through separately evidenced
   qualification, shadow, and production phases.

No runtime completion is inferred from this audit or its passing static tests.
