# AI Worker Dispatcher Policy

Status: active
Date: 2026-07-15

## Purpose

The local dispatcher moves eligible work to Cursor and Claude subscriptions before Codex Desktop performs the worker-suitable reasoning. It is a queue and isolation mechanism, not project authority.

Queue root:

`C:\Users\kevin\.codex\ai_worker_dispatcher`

## Contract

- Every substantive unit begins as a signed `ai_worker_task_intent`. The admission ledger, not a manually supplied denominator, records whether work was eligible, routed, deterministic, or Codex-only with an exact authority reason.
- Requests are created with `New-AIWorkerDispatchRequest.ps1` from committed, hash-bound files.
- Requests and controls are HMAC-SHA256 authenticated with a per-user DPAPI-protected key and current-user/SYSTEM ACLs. A SHA sidecar remains diagnostic only.
- Each request pins an exact Git commit and routing lane.
- The dispatcher creates a detached registered worktree under its own runtime root.
- Cursor and Claude use independent lane tasks and locks, so they run concurrently across decision units while each subscription remains serialized internally.
- Requests have idempotency keys, priority, TTL, dependency order, bounded retry/backoff, cancellation, supersession, stale-scope rejection, and dead-letter handling.
- Read-only worktrees are removed after worker artifacts are copied into the completed packet.
- Guarded Cursor implementation worktrees remain available for Codex diff and test review.
- Completed packets start at `PENDING_CODEX_REVIEW`; Codex records adoption explicitly.
- The dispatcher never stages, commits, pushes, merges, opens PRs, starts AWS resources, mutates Jira, promotes masks, changes Items/Tracker status, or makes final acceptance decisions.

## Cursor Implementation

Cursor uses plain `gpt-5.3-codex` only. Agent mode requires exact allowed repository-relative paths and exact declared host validators. Cursor edits but does not run project tests, generators, package managers, or validators; `Invoke-AIWorkerCommandBroker.ps1` executes allowlisted validators afterward in a credential-scrubbed process. Protected authority paths and mutation commands are rejected before queueing. The wrapper and dispatcher reject changes outside allowed paths. Codex owns final diff review, commit, PR, and merge.

## Claude Review

Sonnet 5 is the primary semantic lane and performs the first substantive architecture, contradiction, or risk synthesis. High-assurance implementation automatically follows Sonnet preflight, Cursor implementation plus host validation, and one Sonnet residual-risk review over the hash-bound diff excerpt. Claude is read-only. Opus 4.8 remains subject to the same-decision escalation record and daily ceiling; it has no usage target.

## Scheduling

`Install-AIWorkerDispatcherTask.ps1` installs independent admission, Cursor, Claude, deterministic health, read-only EC2 safety, and worktree-lifecycle tasks. Healthy cycles launch no model and create no Codex work. Actionable local exceptions are signed into the exception inbox for the reduced Codex authority sweep.

## Qualification

`Measure-AIWorkerQualification.ps1` reports high confidence only when all conditions pass:

- at least 25 substantive handoffs;
- at least 85% useful completion;
- at least 80% adopted output among reviewed results;
- at least 95% scope compliance;
- worker routing on at least 90% of eligible work;
- at least 75% first-pass success, no more than 10% dead letters, and no unresolved critical defects;
- two directly measured five-hour periods with at least 50% lower Codex burn;
- two directly measured 24-hour/weekly-rate periods with at least 50% lower Codex burn.

Cursor/Claude subscription utilization and proxy token counts are diagnostic only. They cannot prove Codex reduction.
