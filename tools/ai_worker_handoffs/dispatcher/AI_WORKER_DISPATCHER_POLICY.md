# AI Worker Dispatcher Policy

Status: active
Date: 2026-07-15

## Purpose

The local dispatcher moves eligible work to Cursor and Claude subscriptions before Codex Desktop performs the worker-suitable reasoning. It is a queue and isolation mechanism, not project authority.

Queue root:

`C:\Users\kevin\.codex\ai_worker_dispatcher`

## Contract

- Requests are created with `New-AIWorkerDispatchRequest.ps1` from committed, hash-bound files.
- Each request pins an exact Git commit and routing lane.
- The dispatcher creates a detached registered worktree under its own runtime root.
- Cursor and Claude lane locks queue for a bounded interval instead of failing immediately.
- Read-only worktrees are removed after worker artifacts are copied into the completed packet.
- Guarded Cursor implementation worktrees remain available for Codex diff and test review.
- Completed packets start at `PENDING_CODEX_REVIEW`; Codex records adoption explicitly.
- The dispatcher never stages, commits, pushes, merges, opens PRs, starts AWS resources, mutates Jira, promotes masks, changes Items/Tracker status, or makes final acceptance decisions.

## Cursor Implementation

Cursor uses plain `gpt-5.3-codex` only. Agent mode requires exact allowed repository-relative paths and exact declared test or validator commands. Protected authority paths and mutation commands are rejected before queueing. The wrapper rejects changes outside the allowed paths. Codex owns final diff review, validation, commit, PR, and merge.

## Claude Review

Sonnet 5 is the primary semantic lane and performs the first substantive architecture, contradiction, or risk synthesis. Claude is read-only. Opus 4.8 remains subject to the same-decision escalation record and daily ceiling; it has no usage target.

## Scheduling

`Install-AIWorkerDispatcherTask.ps1` installs one local non-Codex scheduled task that invokes `Invoke-AIWorkerDispatcher.ps1 -Once`. It launches subscription workers only when a bounded request exists. It does not wake a Codex thread.

## Qualification

`Measure-AIWorkerQualification.ps1` reports high confidence only when all conditions pass:

- at least 25 substantive handoffs;
- at least 85% useful completion;
- at least 80% adopted output among reviewed results;
- at least 95% scope compliance;
- worker routing on at least 90% of eligible work;
- two directly measured five-hour periods with at least 50% lower Codex burn;
- two directly measured 24-hour/weekly-rate periods with at least 50% lower Codex burn.

Cursor/Claude subscription utilization and proxy token counts are diagnostic only. They cannot prove Codex reduction.
