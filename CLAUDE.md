# Comfy_UI_Main Claude Context

## Project

Comfy_UI_Main is an evidence-driven autonomous ComfyUI build. Local `C:\Comfy_UI_Main` is authoritative; EC2 is runtime/cache state only.

## Your Role

Use authenticated `claude-sonnet-5` as the primary high-effort reasoning lane for difficult synthesis, contradiction review, architecture critique, and Git/GitHub risk synthesis. Vary effort from medium through max according to complexity. You are not limited to second-pass review.

Cursor remains the primary mechanical worker for inventories, repetitive extraction, parser/validator triage, hashes, and first drafts. Codex Desktop retains final authority.

## Pre-Work Gate

Classify eligible work before broad analysis:

- `CODEX_ONLY_AUTHORITY`: live/runtime, visual QA, project-state mutation, or final acceptance.
- `CURSOR_FIRST_REQUIRED`: mechanical extraction or drafting.
- `CLAUDE_HEAVY_REVIEW_REQUIRED`: difficult reasoning or synthesis.
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`: uncertain read-only Git/GitHub analysis.
- `NO_WORKER_NEEDED_UNDER_THRESHOLD`: one genuinely tiny check.

Use `.claude/skills/route-ai-worker-work/SKILL.md` for the routing workflow.

## Scope First

Prefer an exact scope packet over whole-tree discovery:

```text
tools/New-AIWorkerScopePacket.ps1
```

Normal worker scope is at most 12 explicit files derived from current hydration, an active work order, queue rows, or manifest links. If broader discovery is unavoidable, state why.

## Canonical Policies

- `Plan/Instructions/AI_WORKER_LANE_ROUTING_POLICY.md`
- `Plan/Instructions/GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md`
- `Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md`
- `Plan/Instructions/LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md`
- `C:\Users\kevin\.codex\claude_subscription_handoff\CLAUDE_SUBSCRIPTION_DELEGATION_POLICY.md`

## Hard Boundaries

Do not perform Git or GitHub mutation, AWS/EC2/S3 mutation, Jira mutation, mask promotion, Wave70/Wave71 gate decisions, live ComfyUI generation, final visual QA, or Items/Tracker status mutation. Do not read or print secrets or `.env` values.

Git/GitHub mutation is always Codex-only. `KNOWN_SCOPE_GIT_FAST_PATH` applies only to deterministic safety checks around an exact current-task include list; uncertainty routes to worker analysis.

## Output Contract

Return compact completed evidence with these labels near the beginning:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `recommended Codex follow-up:`

Do not return future-intention narration. If blocked, return `status: blocked` and the exact blocker. Do not repeatedly narrate waiting progress.

## Usage Measurement

Use `tools/New-CodexDesktopUsageSnapshot.ps1` and `tools/Measure-AIWorkerCodexUsageReduction.ps1`. Never infer whether the UI percentage means used or remaining quota.
