# AI Worker Development Acceleration And Quality Strategy

Status: active productionization authority
Date: 2026-07-15
Owner: Codex Desktop final authority with Cursor and Claude subscription workers

## Outcomes

The worker system must improve four outcomes together:

1. reduce Codex Desktop five-hour and weekly consumption by at least 50%;
2. shorten elapsed development time and increase compatible parallel work;
3. improve implementation correctness, evidence integrity, and defect detection;
4. improve maintainability, runtime fidelity, visual quality, and user-facing quality without creating review ceremony.

Subscription utilization is not itself success. The system is successful only when worker output is useful, adopted, scope-compliant, faster than the prior path, and associated with equal or better defect and regression outcomes.

## Operating Architecture

The production control plane has independent services:

- deterministic admission converts a structured task intent into a route decision before substantive Codex reasoning;
- the Cursor lane runs mechanical extraction, implementation, test drafts, and failure triage in isolated worktrees;
- the Claude lane runs Sonnet architecture, semantic specification, contradiction analysis, test strategy, and bounded high-risk review;
- deterministic validation runs outside the model after implementation;
- Codex reviews a compact result packet and retains every final-authority action;
- local monitors measure queue health, worker quality, Codex reduction, and safe runtime state without waking Codex on healthy cycles.

Cursor and Claude lanes run concurrently. Each lane is serialized internally to protect subscription sessions. A long Cursor implementation must not prevent Sonnet from completing architecture work for another unit.

## Work Decomposition For Speed

Tasks should be decomposed into decision units that can complete independently and merge in batches of three to five compatible units. Use these stages only when they add value:

1. deterministic context shortlist;
2. Sonnet semantic or architecture pass for medium/high semantic risk;
3. Cursor implementation and test draft;
4. host-controlled validators;
5. targeted Sonnet review only for material residual semantic risk;
6. compact Codex final review and authority action.

Low-risk mechanical changes normally skip Sonnet. High-risk changes start with Sonnet. A routine clean unit never receives Cursor review, Sonnet review, and Opus review merely for ceremony.

## Accuracy Controls

Every worker task carries:

- exact base commit and file hashes;
- risk class and quality profile;
- explicit behavior and non-goal contract;
- exact allowed write paths;
- host-run validator commands;
- regression and failure-mode expectations;
- evidence and provenance requirements;
- freshness deadline, retry ceiling, and idempotency key.

Workers must distinguish observed facts, inference, recommendation, and blocker. Unknown authority, missing runtime evidence, or failed transforms remain fail-closed. Completed blockers are useful diagnosis but never implementation success.

## Quality Controls

Quality profiles are defined in `Plan/10_REGISTRIES/ai_worker_development_quality_profiles.json`.

- `fast_low_risk`: Cursor-first, at least one deterministic validator, no routine semantic review.
- `balanced_default`: Cursor plus two validators; Sonnet is used when semantic or cross-module risk exists.
- `high_assurance`: Sonnet architecture first, Cursor implementation, at least three validators, and targeted Sonnet residual-risk review before Codex final authority.

Acceptance contracts cover correctness, regressions, maintainability, performance, security, evidence integrity, user experience, and runtime fidelity as applicable. Visual QA, live generation, masks, AWS mutation, Jira mutation, Git/GitHub mutation, and Items/Tracker status remain Codex-only.

## Feedback And Continuous Improvement

The system records route decisions, queue time, worker duration, retry count, validator results, adoption, changed paths, defects found during Codex review, post-merge regressions, and measured Codex usage. Routing profiles are adjusted from evidence:

- low adoption routes become narrower or move to another worker;
- repeated Cursor semantic defects trigger Sonnet-first routing for that task family;
- repeated Sonnet over-analysis moves deterministic units back to Cursor or a fast path;
- validators that catch real defects gain weight; low-signal duplicate checks are removed;
- partial adoption is measured separately from full adoption;
- blocked diagnosis, implementation success, and certification success remain separate metrics.

## Queue And Lifecycle

Requests are DPAPI/HMAC authenticated and stored under a current-user ACL. The idempotency key prevents duplicate active work. Requests have priority, TTL, attempt ceiling, dependency list, freshness policy, and cancellation/supersession controls. Transient failures use bounded backoff; exhausted or invalid work moves to dead letter.

Read-only worktrees are removed after artifact capture. Implementation worktrees remain only while pending Codex review. Adoption, rejection, cancellation, or expiry invokes guarded cleanup. No worker may stage, commit, push, merge, or alter repository authority state.

## Development Performance Metrics

Measure at least:

- task lead time and active Codex minutes;
- queue wait and worker runtime by lane;
- first-pass validator success;
- retry and dead-letter rate;
- full, partial, and rejected adoption rates;
- defects found before merge and regressions after merge;
- scope compliance and duplicate suppression;
- semantic review precision: material findings divided by substantive reviews;
- time from task intent to Codex-ready packet;
- measured five-hour and 24-hour/weekly-rate Codex reduction.

High confidence requires the existing 25-handoff, completion, adoption, scope, routing, and direct-measurement thresholds plus no unresolved critical regression trend.

## ComfyUI Delivery Playbooks

### Workflow and custom-node implementation

Sonnet defines node contracts, tensor/image dimensions, fallback behavior, and failure modes when semantics are uncertain. Cursor drafts workflow JSON, adapters, validators, and tests in exact paths. Host checks parse JSON, validate schemas, verify node names against declared runtime requirements, and run focused regressions. Codex owns live ComfyUI execution and visual acceptance.

### Model and asset acquisition

Cursor performs exact registry, hash, placement, and workflow-reference extraction. Sonnet resolves compatibility or licensing contradictions. Codex retains browser/AWS/live authority. Every lane reuses exact local/Main/legacy/S3 hashes before network acquisition, records immutable model revision and configuration, and treats download as incomplete until runtime visibility and modality QA pass.

### Runtime orchestration

Cursor drafts local run packages, smoke validators, pullback manifests, and failure extraction. Sonnet reviews cross-system orchestration risk before a new architecture or high-risk runtime. Codex alone authorizes EC2/S3 mutation, posts live prompts, inspects generated media, and closes runtime windows. Stale EC2 project state never overrides local authority.

### Media and Mask Factory quality

Deterministic tools own dimensions, frame/sample counts, hashes, timing, codecs, mask topology metrics, and schema checks. Sonnet may review semantic contracts and evidence contradictions. Codex owns image/video/audio perceptual judgment, mask authority, promotion, and certification. Candidate masks, model judgments, and technical metrics never impersonate gold or human authority.

### Evidence and project controls

Workers create implementation-adjacent evidence only. They do not mutate Items/Tracker status, Jira, hydration authority, or final certification. Codex batches minimal reconciliation after real executable outcomes. Repeated evidence-only or bookkeeping-only work is excluded from delivery throughput.

## Accuracy Engineering

- Require deterministic reproduction data: exact commit, model/file hashes, seeds, configuration, input identity, transforms, and environment where applicable.
- Prefer property, contract, golden, and failure-injection tests over duplicated happy-path reviews.
- Detect flaky validators by repeated-result disagreement and remove them from qualification until repaired.
- Record defect provenance: worker-found, host-validator-found, Codex-review-found, CI-found, runtime-found, or post-merge.
- Escalate a task family to Sonnet-first when Cursor repeatedly misses semantic defects; return it to Cursor-first after measured recovery.
- Reject stale dependency results when scoped source changes, even when the request itself remains signed.
- Keep claims proportional: local parse, package smoke, runtime proof, perceptual QA, and certification are separate gates.

## Quality Engineering

- Maintainability: match existing project patterns, bound abstractions, and reject unrelated refactors.
- Performance: include latency, memory/VRAM, startup, frame/sample throughput, and artifact-size budgets when relevant.
- Reliability: test timeout, cancellation, retry, partial artifact, missing model, unavailable route, and cleanup behavior.
- Security: scrub credentials, prohibit authority commands, HMAC-sign control-plane records, and post-check all worker/validator changes.
- User experience: reserve model review for semantics; use direct Codex visual/playback review for the actual product experience.
- Review economy: one meaningful review per risk, no third-review ceremony, and no Opus call for utilization optics.

## Speed Engineering

- Start independent decision units concurrently across Cursor and Claude lanes.
- Place semantic preflight ahead of implementation only when it prevents rework.
- Use dependency packets instead of repeating repository discovery.
- Cache unchanged scope packets and suppress identical active requests by idempotency key.
- Fail fast on stale scope, protected paths, invalid acceptance contracts, or missing validators before a subscription call.
- Keep worker output compact enough for Codex to decide from changed paths, diff excerpt/hash, validators, blockers, and recommendation.
- Batch three to five compatible accepted units per protected PR so CI and checkpoint overhead do not erase worker gains.

## Automation Reduction

Healthy deterministic checks run locally. Codex automations become exception and authority handlers:

- worker health is local and wakes Codex only for repeated failures or scope violations;
- EC2 state is checked locally and read-only; Codex retains start/stop authority and handles alerts;
- delivery and sequence snapshots run locally first; Sonnet handles non-authority synthesis; Codex receives only actionable final-authority findings;
- stale task-session cleanup remains app-owned but should run no more often than necessary;
- no monitor creates recurring evidence when nothing materially changed.

## Qualification Boundary

Until production handoffs and matched usage windows pass the thresholds, report `NOT_YET_QUALIFIED`. Do not infer a 50% reduction from Cursor tokens, Claude plan utilization, scheduled-task frequency, or proxy estimates.
