# Codex Automation Exception Migration Strategy

Status: implementation ready; schedule migration requires live-task canaries
Date: 2026-07-15

## Goal

Reduce routine Codex Desktop automation invocations from about 57 per day to roughly 10-15 while preserving every final-authority and EC2 safety boundary. Local deterministic services perform healthy checks; Codex runs only for actionable exceptions, final judgment, or mutation authority.

## Local Services

- admission router every minute;
- independent Cursor and Claude lane runners every minute, idle when queues are empty;
- worker/package/queue/qualification health every four hours;
- approved-instance EC2 disposition read-only every 15 minutes;
- retained worktree lifecycle every hour.

All local records are external to Git under `C:\Users\kevin\.codex\ai_worker_dispatcher`. Healthy cycles do not launch Cursor, Claude, or Codex. Exceptions are HMAC-signed into `alerts`; `Invoke-AIWorkerExceptionInbox.ps1` is the bounded entry point for Codex sweeps.

## Guarded Codex Schedule Target

After local task canaries pass:

- combined worker monitor: pause; local health owns deterministic checks;
- EC2 Codex sentinel: reduce from hourly to every six hours, retaining local 15-minute read-only checks and all AWS-side watchdog/emergency controls;
- anti-loop supervisor: reduce from every two hours to every six hours after its deterministic snapshot is local;
- milestone auditor: reduce from every six hours to daily unless an exception or real row transition occurs;
- stale-session cleanup: reduce from every three hours to daily;
- retain daily fleet, artifact, cost, and weekly audits.

Do not migrate a schedule until the corresponding local task has two successful canaries and its exception inbox behavior is verified. Roll back a migration if an actionable exception remains unseen beyond the prior Codex interval, local task failure persists for two cycles, or EC2 state cannot be read.

## Quality And Speed Safeguards

- routing events count every eligible task, including Codex-only reasons;
- independent lanes remove global queue blocking;
- high-assurance dependency graphs start architecture and risk work early;
- host validators fail fast before Codex review;
- compact diff packets reduce rereading and context rebuild;
- compatible units remain batched three to five per protected PR;
- qualification includes latency, first-pass success, adoption, scope, dead letters, critical defects, and direct Codex usage windows.

Schedule frequency is not a token estimate. The 50% claim remains `NOT_YET_QUALIFIED` until two five-hour and two 24-hour/weekly-rate matched windows pass.
