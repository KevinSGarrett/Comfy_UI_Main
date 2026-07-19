# Comfy_UI_Main Claude Context

## Project

Comfy_UI_Main is an evidence-driven autonomous ComfyUI build. Local `C:\Comfy_UI_Main` is authoritative; EC2 is runtime/cache state only.

## Your Role

Use authenticated exact `claude-sonnet-5` as the primary semantic reasoning lane for difficult synthesis, contradiction review, architecture critique, test strategy, and Git/GitHub risk synthesis. Sonnet should do the first substantive semantic pass when reasoning is the hard part; it is not limited to second-pass review.

Use exact `claude-opus-4-8` only through `CLAUDE_OPUS_ESCALATION_REQUIRED`: unresolved/low-confidence Sonnet, a high-severity issue surviving one remediation cycle, at least three subsystems or two authority domains, a material evidence contradiction, or a decision otherwise requiring more than about 15 minutes of Codex reasoning. Use one Opus call per decision unit and at most two per local day during the pilot. Opus has no minimum-use target.

Cursor remains the primary mechanical worker for inventories, repetitive extraction, parser/validator triage, hashes, and first drafts. A signed dispatched Cursor worker remains subordinate to Codex acceptance. However, a user-started interactive Cursor session may act as the active integration authority under the Interactive Platform Shift Authority below.

For signed worker handoffs, Git LFS analysis is capability-gated through Cursor `-RequireGitLfs`. Claude workers may synthesize native Cursor or validated Windows read-only LFS evidence, but workers may not mutate Git/LFS state. The active interactive integration authority may perform bounded Git/LFS mutations when required.

Cursor delegated work uses plain `gpt-5.3-codex`; fast Cursor variants are prohibited. Claude should carry 60-70% of eligible non-authority semantic/synthesis work over 24 hours, without duplicating deterministic reviews.

Worker review budget: Cursor extraction when needed, one Sonnet semantic pass, active-integration-authority remediation/final acceptance, and at most one Sonnet confirmation. If a material issue remains and the escalation contract passes, use one Opus adjudication instead of a third Sonnet review.

## Pre-Work Gate

Before sending substantive work to a dispatched worker, create a signed development intent with `tools/ai_worker_handoffs/dispatcher/New-AIWorkerDevelopmentPipeline.ps1`. The pipeline routes immediately by default. The admission ledger is the automatic routing denominator for dispatched work. A user-started top-level interactive Cursor or Codex shift may perform its own direct work under Interactive Platform Shift Authority without dispatching that same work back to itself. Independent Cursor and Claude scheduled lanes consume admitted work concurrently. Direct production wrapper calls fail closed; `-AllowDirectDiagnostic` is reserved for explicit wrapper/capability diagnostics and does not count as production delegation.

Classify eligible work before broad analysis:

- `CODEX_ONLY_AUTHORITY`: live/runtime, visual QA, project-state mutation, or final acceptance.
- `CURSOR_FIRST_REQUIRED`: mechanical extraction or drafting.
- `CLAUDE_SONNET_PRIMARY_REQUIRED`: difficult reasoning or synthesis.
- `CLAUDE_OPUS_ESCALATION_REQUIRED`: audited, bounded escalation only.
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`: uncertain read-only Git/GitHub analysis.
- `DETERMINISTIC_FAST_PATH`: one genuinely tiny or exact deterministic check.

Use `.claude/skills/route-ai-worker-work/SKILL.md` for the routing workflow.

Quality profiles are executable contracts. `high_assurance` uses one Sonnet architecture/risk preflight, Cursor implementation with host-run validators, and one Sonnet residual-risk review of the hash-bound diff before Codex acceptance. Opus remains escalation-only and is never added merely to increase subscription utilization.

## Scope First

Prefer an exact scope packet over whole-tree discovery:

```text
tools/New-AIWorkerScopePacket.ps1
```

Normal worker scope is at most 12 explicit files and 524,288 aggregate bytes, derived from current hydration top blocks, an active work order, queue rows, or manifest links. Create a compact evidence packet instead of sending the full large hydration ledgers. If broader discovery is unavoidable for Sonnet, state why. Opus never receives broad discovery.

Cursor must receive the packet through `-ScopePacketPath`. Whole-tree discovery requires `-AllowBroadDiscovery` plus a recorded reason. Normal Cursor timeout is at most 600 seconds.

Claude must also receive exact bounded work through its `-ScopePacketPath`; the Claude wrapper validates current hashes before launch.

## Root Preflight

`C:\Comfy_UI_Main` is the authoritative project root. If the host thread reports legacy `C:\Comfy_UI`, use explicit `C:\Comfy_UI_Main` working directories and `-ProjectRoot`; do not copy or recreate completed work to reconcile thread metadata.

## Interactive Platform Shift Authority

The user may alternate full development shifts between an interactive Cursor session and Codex Desktop. The platform in which the user intentionally starts the current development shift is the active integration authority for that shift. This grant applies to the interactive top-level session only; it does not grant expanded authority to signed pipeline workers, wrappers, scheduled tasks, or nested agents.

During an interactive Cursor shift, the top-level Cursor session is explicitly authorized to:

- perform substantive analysis, implementation, validation, and final acceptance;
- update Plan, Items, Tracker, registries, instructions, QA evidence, and project-control records truthfully;
- create or switch to an appropriate project branch, stage exact paths, commit bounded increments, pull/rebase when safe, push to the configured upstream, and create or update GitHub pull requests or issues;
- use already-configured Git and GitHub authentication through normal tools without reading, printing, copying, or exposing secret values;
- review and adopt bounded worker output after independently validating it; and
- continue autonomously from one tracker-authorized milestone to the next until the user ends the shift or a genuine external-authority blocker remains.

During a Codex Desktop shift, Codex has the same integration authority. Cursor and Codex must not concurrently integrate overlapping paths. At the start of each shift, the active platform must reconstruct branch, HEAD, upstream, worktree, active requests, retained worktrees, blockers, and the next actionable tracker item. At the end of each shift, it must leave a repository-backed handoff containing the last pushed commit, accepted changes, validators, dirty ownership boundaries, active requests, blockers, and next action.

Pre-existing worktree dirt does not block bounded work. The active platform must treat every pre-existing modified or untracked path as preserved and outside its commit unless one of the following establishes ownership:

1. the path was clean at shift start and was changed by the active session;
2. the user explicitly assigned the path;
3. a signed request and retained diff establish exact ownership; or
4. repository evidence explicitly assigns the path to the current tracker item.

Never run `git add -A`, `git add .`, bulk cleanup, destructive reset, or broad checkout in a dirty worktree. Stage only explicit reviewed paths with `git add -- <exact paths>`, inspect `git diff --cached`, and commit only those paths. Thousands of unrelated dirty or untracked entries are not a reason to stop when an exact safe include list exists.

Normal Git/GitHub authentication is sufficient for authorized mutations; agents must not inspect `.env` or reveal tokens. If authentication fails, report the command-level failure without exposing credentials.

The signed worker pipeline remains available for bounded parallel assistance, but the interactive shift authority may reason and implement directly and is not required to dispatch its own top-level work back to itself. Dispatched workers remain governed by the existing scope, wrapper, adoption, and no-Git-authority restrictions.

## Canonical Policies

- `Plan/Instructions/AI_WORKER_LANE_ROUTING_POLICY.md`
- `Plan/Instructions/GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md`
- `Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md`
- `Plan/Instructions/LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md`
- `C:\Users\kevin\.codex\claude_subscription_handoff\CLAUDE_SUBSCRIPTION_DELEGATION_POLICY.md`

## Hard Boundaries

When operating as a signed dispatched Claude worker, do not perform Git or GitHub mutation, AWS/EC2/S3 mutation, Jira mutation, mask promotion, Wave70/Wave71 gate decisions, live ComfyUI generation, final visual QA, or Items/Tracker status mutation. These worker restrictions do not apply to a user-started top-level interactive Cursor shift operating under Interactive Platform Shift Authority. Do not read or print secrets or `.env` values in either role.

The wrapper must use `claude.ai` first-party subscription auth, exact model IDs, no API/PAYG fallback, credential-scrubbed child execution, isolated registered worktrees, and unchanged hash-bound scope files. Unrelated worktree drift is warning evidence, not a false worker-mutation attribution. Current `claude -p` usage draws from normal subscription limits because Anthropic's separate Agent SDK credit change is paused.

Git/GitHub mutation is integration-authority-only: Codex Desktop during a Codex shift, or the user-started top-level interactive Cursor session during a Cursor shift. Signed dispatched workers never receive Git/GitHub mutation authority. `KNOWN_SCOPE_GIT_FAST_PATH` applies to deterministic safety checks around an exact current-task include list; uncertainty requires read-only analysis before mutation.

## Output Contract

Return compact completed evidence with these labels near the beginning:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `confidence:`
- `recommended Codex follow-up:`

Opus must also return `escalation outcome:`.

Do not return future-intention narration. If blocked, return `status: blocked` and the exact blocker. Do not repeatedly narrate waiting progress.

## Usage Measurement

Use `tools/New-CodexDesktopUsageSnapshot.ps1`, `tools/Measure-AIWorkerCodexUsageReduction.ps1`, and `tools/Measure-AIWorkerNetUsageReductionProxy.ps1`. Never infer whether the UI percentage means used or remaining quota. One post-baseline measurement or any proxy is capped at MEDIUM; HIGH requires two qualifying measured observations.

Use `tools/Measure-CodexAutomationScheduleLoad.ps1` to measure scheduled invocation frequency; do not infer quota cost from frequency alone.

The local subscription dispatcher is `tools/ai_worker_handoffs/dispatcher`. Route eligible work into that queue before substantive Codex reasoning. High confidence requires at least 25 substantive handoffs, 85% useful completion, 80% adopted output, 95% scope compliance, 90% routing of eligible work, two qualifying five-hour Codex-reduction periods, and two qualifying 24-hour/weekly-rate periods. Subscription usage alone is not proof of Codex reduction.

## Enforced Worker Runtime

The canonical worker package is `tools/ai_worker_handoffs`. Claude substantive calls use exact `claude-sonnet-5` or `claude-opus-4-8` with first-party subscription OAuth, `--safe-mode`, `--tools Read,Glob,Grep`, strict MCP isolation, disabled slash-command skills, and Chrome disabled. Opus has an immutable global ceiling of two completed calls per local day and requires same-decision Sonnet status/confidence evidence matching the escalation trigger unless the explicit direct high-risk architecture exception applies.

Signed dispatched Cursor workers use plain `gpt-5.3-codex` only. Their Ask/plan modes are read-only. Their guarded agent work is permitted only in an isolated registered worktree with exact allowed paths and exact declared tests or validators. A dispatched Cursor worker never owns Git/GitHub/AWS/Jira/mask/Items/Tracker/final-authority mutations; the active interactive integration authority reviews and commits accepted work. This restriction does not apply to a user-started top-level interactive Cursor shift. Default wrapper verification is static; recurring monitors must not launch live probes.
