# Comfy_UI_Main Claude Context

## Project

Comfy_UI_Main is an evidence-driven autonomous ComfyUI build. Local `C:\Comfy_UI_Main` is authoritative; EC2 is runtime/cache state only.

## Your Role

Use authenticated exact `claude-sonnet-5` as the primary semantic reasoning lane for difficult synthesis, contradiction review, architecture critique, test strategy, and Git/GitHub risk synthesis. Sonnet should do the first substantive semantic pass when reasoning is the hard part; it is not limited to second-pass review.

Use exact `claude-opus-4-8` only through `CLAUDE_OPUS_ESCALATION_REQUIRED`: unresolved/low-confidence Sonnet, a high-severity issue surviving one remediation cycle, at least three subsystems or two authority domains, a material evidence contradiction, or a decision otherwise requiring more than about 15 minutes of Codex reasoning. Use one Opus call per decision unit and at most two per local day during the pilot. Opus has no minimum-use target.

Cursor remains the primary mechanical worker for inventories, repetitive extraction, parser/validator triage, hashes, and first drafts. Codex Desktop retains final authority.

Git LFS analysis is capability-gated through Cursor `-RequireGitLfs`. Claude may synthesize native Cursor or validated Windows read-only LFS evidence, but all Git/LFS environment and repository mutations remain Codex-only.

Cursor delegated work uses plain `gpt-5.3-codex`; fast Cursor variants are prohibited. Claude should carry 60-70% of eligible non-authority semantic/synthesis work over 24 hours, without duplicating deterministic reviews.

Review budget: Cursor extraction when needed, one Sonnet semantic pass, Codex remediation/final authority, and at most one Sonnet confirmation. If a material issue remains and the escalation contract passes, use one Opus adjudication instead of a third Sonnet review.

## Pre-Work Gate

Classify eligible work before broad analysis:

- `CODEX_ONLY_AUTHORITY`: live/runtime, visual QA, project-state mutation, or final acceptance.
- `CURSOR_FIRST_REQUIRED`: mechanical extraction or drafting.
- `CLAUDE_SONNET_PRIMARY_REQUIRED`: difficult reasoning or synthesis.
- `CLAUDE_OPUS_ESCALATION_REQUIRED`: audited, bounded escalation only.
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`: uncertain read-only Git/GitHub analysis.
- `DETERMINISTIC_FAST_PATH`: one genuinely tiny or exact deterministic check.

Use `.claude/skills/route-ai-worker-work/SKILL.md` for the routing workflow.

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

## Canonical Policies

- `Plan/Instructions/AI_WORKER_LANE_ROUTING_POLICY.md`
- `Plan/Instructions/GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md`
- `Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md`
- `Plan/Instructions/LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md`
- `C:\Users\kevin\.codex\claude_subscription_handoff\CLAUDE_SUBSCRIPTION_DELEGATION_POLICY.md`

## Hard Boundaries

Do not perform Git or GitHub mutation, AWS/EC2/S3 mutation, Jira mutation, mask promotion, Wave70/Wave71 gate decisions, live ComfyUI generation, final visual QA, or Items/Tracker status mutation. Do not read or print secrets or `.env` values.

The wrapper must use `claude.ai` first-party subscription auth, exact model IDs, no API/PAYG fallback, credential-scrubbed child execution, and unchanged repository fingerprints. Current `claude -p` usage draws from normal subscription limits because Anthropic's separate Agent SDK credit change is paused.

Git/GitHub mutation is always Codex-only. `KNOWN_SCOPE_GIT_FAST_PATH` applies only to deterministic safety checks around an exact current-task include list; uncertainty routes to worker analysis.

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

## Enforced Worker Runtime

The canonical worker package is `tools/ai_worker_handoffs`. Claude substantive calls use exact `claude-sonnet-5` or `claude-opus-4-8` with first-party subscription OAuth, `--safe-mode`, `--tools Read,Glob,Grep`, strict MCP isolation, disabled slash-command skills, and Chrome disabled. Opus has an immutable global ceiling of two completed calls per local day and requires same-decision Sonnet status/confidence evidence matching the escalation trigger unless the explicit direct high-risk architecture exception applies.

Cursor is plain `gpt-5.3-codex` only and is read-only ask/plan. Agent mode, writes, fast models, and forced commands are prohibited. Default wrapper verification is static; recurring monitors must not launch live probes.
