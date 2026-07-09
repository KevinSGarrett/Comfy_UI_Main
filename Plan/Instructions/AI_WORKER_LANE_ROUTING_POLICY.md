# AI Worker Lane Routing Policy

Updated: 2026-07-09

This policy defines how Codex Desktop, Cursor CLI, and Claude Code subscription work together for Comfy_UI_Main.

## Objective

Reduce Codex Desktop usage by moving bounded worker tasks to Cursor and high-effort synthesis tasks to Claude Code subscription while keeping Codex as final project authority.

Current usage baseline:

```text
C:\Comfy_UI_Main\runtime_artifacts\agent_handoffs\ai_worker_rollout\CODEX_DESKTOP_USAGE_BOOKMARK_20260709T150020-0500.json
```

The bookmarked Codex Desktop weekly usage is `78%` with a weekly reset on `2026-07-15`. Worker delegation should be evaluated against the explicit target of reducing Codex Desktop usage by at least 50%.

## Shared Project Boundaries

All worker routing must also respect:

```text
C:\Comfy_UI_Main\Plan\Instructions\AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md
C:\Comfy_UI_Main\Plan\Instructions\JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md
```

Local `C:\Comfy_UI_Main` is the authoritative execution ledger. EC2 `/home/ubuntu/Comfy_UI_Main` is runtime/cache state only and must not be used to reopen completed work.

Do not count worker handoffs, hydration, proof-log, tracker, manifest, index, Git, or audit updates as real progress unless they directly follow a concrete ComfyUI runtime/orchestration/QA artifact. The selected-inpaint runtime/orchestration path remains the active local-first work lane unless the user explicitly selects another lane.

Workers and worker-health monitors must not rerun completed fallback/base/Canny/local-smoke proofs from stale EC2 or old ledger state.

## Lane 1: Codex Desktop Final Authority

Codex owns:

- final project decisions and user-facing summaries;
- visual QA and final image/video judgment;
- Git checkpoint, commit, push, reset, checkout, and branch decisions;
- AWS, EC2, S3, live runtime, and ComfyUI generation decisions;
- mask promotion, Wave70 hard gates, Wave71+ activation, and Jira mutation;
- Items/Tracker status mutation.

Codex should not spend long active turns doing broad mechanical scans when Cursor or Claude can produce compact evidence.

## Lane 2: Cursor First Worker

Cursor is the default first worker for:

- broad local inventories;
- evidence extraction from many files;
- parser and validator triage;
- helper or script first drafts in narrow scopes;
- bookmark-resume diagnosis;
- repetitive file/path/hash summaries.

Use:

```text
C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1
```

Default read-only mode is `ask`. Use `plan` only after `ask` is insufficient. Incomplete promise-style output is not evidence.

## Lane 3: Claude Code Subscription

Claude subscription is the high-effort Sonnet lane for:

- difficult strategy synthesis;
- contradiction review across plans and policies;
- architecture or routing critique;
- second-pass review after Cursor extraction;
- heavy reasoning tasks that would otherwise consume a long Codex Desktop turn.

Use:

```text
C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1
```

The wrapper must verify:

- `loggedIn: true`
- `authMethod: claude.ai`
- `apiProvider: firstParty`
- no `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or `ANTHROPIC_BASE_URL` environment fallback

Default model is `sonnet`. Use `--Effort medium` for routine synthesis, `--Effort high` for difficult review, and `--Effort xhigh` or `--Effort max` only for unusually heavy work.

## Routing Order

1. If the task involves final authority, live runtime, masks, Git, Jira, S3, EC2, or visual QA, keep it in Codex.
2. If the task is mechanical local reading, inventory, triage, or drafting, send it to Cursor first.
3. If the task is hard synthesis or strategy review, use Claude subscription after Cursor extraction or as the primary heavy-review lane.
4. Codex reviews compact worker evidence and decides the final action.

## Mandatory Pre-Work Delegation Gate

Before Codex starts any broad scan, audit, helper draft, multi-file diagnosis, evidence extraction, or strategy review, it must classify the work with exactly one gate:

- `CODEX_ONLY_AUTHORITY`
- `CURSOR_FIRST_REQUIRED`
- `CLAUDE_HEAVY_REVIEW_REQUIRED`
- `NO_WORKER_NEEDED_UNDER_THRESHOLD`

If Codex selects `CODEX_ONLY_AUTHORITY`, it must record the authority reason, such as visual QA, Git, EC2, S3, Jira, masks, Wave70/Wave71 gates, Items/Tracker status mutation, or final acceptance.

If Codex selects `NO_WORKER_NEEDED_UNDER_THRESHOLD`, it must keep the work under the thresholds below. If the work grows past threshold, Codex must stop and create a worker handoff.

## Budget Thresholds

Use these thresholds as hard routing triggers:

- More than 10 files to inspect: `CURSOR_FIRST_REQUIRED`.
- More than one major tree to inspect: `CURSOR_FIRST_REQUIRED`.
- More than one broad `rg` or inventory pass: `CURSOR_FIRST_REQUIRED`.
- More than one validator or parser triage pass: `CURSOR_FIRST_REQUIRED`.
- More than 3 minutes of active Codex reasoning expected: use Cursor or Claude.
- Helper/script first draft in a narrow local scope: Cursor first unless final authority blocks delegation.
- Strategy/contradiction review, broad synthesis, or architecture/routing critique: `CLAUDE_HEAVY_REVIEW_REQUIRED` unless it includes final authority.
- Failed or incomplete worker output: retry once with a narrower work order before Codex absorbs the task.

Codex may bypass these triggers only when the task is explicitly in final authority scope, and the bypass reason must be recorded.

## Fallback Rules

If Cursor is unavailable or returns incomplete output, Codex should narrow and retry once before doing the work directly.

If Claude subscription auth is missing, expired, non-`claude.ai`, or API-key fallback risk is present, Codex must route the work to Cursor or record `CLAUDE_SUBSCRIPTION_UNAVAILABLE`.

When Codex performs fallback work directly, it must record:

- original worker gate;
- worker failure reason;
- narrower retry attempted yes/no;
- why direct Codex work was necessary.

## Monitor Scoring

The combined AI worker monitor must score each audit window with:

- worker-eligible tasks detected;
- worker handoffs attempted;
- successful compact handoffs;
- incomplete or failed handoffs;
- Codex fallback cases;
- direct-Codex violations where eligible work was done without a worker handoff;
- estimated Codex work avoided;
- usage reduction confidence.

Usage reduction confidence should be reported as:

- `LOW`: less than 40% estimated reduction or repeated direct-Codex violations.
- `MEDIUM`: 40-60% estimated reduction with some worker success and limited fallback.
- `HIGH`: 60%+ estimated reduction with successful worker-first behavior and no major violations.
- `PROVEN`: multiple consecutive audit windows show 50%+ estimated reduction and worker outputs are used in practice.

## Output Contract

Worker handoffs must return:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `recommended Codex follow-up:`

Codex should retry narrower or classify the lane as unavailable when the output is incomplete.

Worker-health audits must finish with parseable final JSON. A stale `IN_PROGRESS` stub is acceptable only when a newer final audit supersedes it; otherwise it is a monitor defect, not project progress.

## Forbidden Delegation

Do not delegate these final decisions to Cursor or Claude:

- live EC2 start/stop;
- S3 upload;
- ComfyUI generation;
- Git mutation;
- Jira mutation;
- mask promotion or Wave70 hard gates;
- Wave71+ activation;
- final visual QA approval;
- Items/Tracker status mutation.
