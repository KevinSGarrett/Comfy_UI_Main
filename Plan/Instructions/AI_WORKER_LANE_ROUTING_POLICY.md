# AI Worker Lane Routing Policy

Updated: 2026-07-09

This policy defines how Codex Desktop, Cursor CLI, and Claude Code subscription work together for Comfy_UI_Main.

## Objective

Reduce Codex Desktop usage by moving bounded worker tasks to Cursor, high-effort synthesis tasks to Claude Code subscription, and read-only Git/GitHub investigation to worker-analysis lanes while keeping Codex as final project authority.

Target outcome: reduce active Codex Desktop usage by at least 50% for this 24/7 autonomous ComfyUI build. Cursor and Claude are not extra project managers; they are worker lanes that absorb work Codex Desktop would otherwise spend long turns doing.

Current usage baseline:

```text
C:\Comfy_UI_Main\runtime_artifacts\agent_handoffs\ai_worker_rollout\CODEX_DESKTOP_USAGE_BOOKMARK_20260709T150020-0500.json
```

The bookmarked Codex Desktop weekly usage is `78%` with a weekly reset on `2026-07-15`. Worker delegation should be evaluated against the explicit target of reducing Codex Desktop usage by at least 50%.

## Shared Project Boundaries

All worker routing must also respect:

```text
C:\Comfy_UI_Main\Plan\Instructions\AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md
C:\Comfy_UI_Main\Plan\Instructions\JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md
```

Local `C:\Comfy_UI_Main` is the authoritative execution ledger. EC2 `/home/ubuntu/Comfy_UI_Main` is runtime/cache state only and must not be used to reopen completed work.

Do not count worker handoffs, hydration, proof-log, tracker, manifest, index, Git, or audit updates as real progress unless they directly follow a concrete ComfyUI runtime/orchestration/QA artifact. The selected-inpaint runtime/orchestration path remains the active local-first work lane unless the user explicitly selects another lane.

Workers and worker-health monitors must not rerun completed fallback/base/Canny/local-smoke proofs from stale EC2 or old ledger state.

## Usage Reduction Rule

Before Codex Desktop performs any broad local scan, repetitive evidence extraction, first-pass helper/script drafting, long contradiction review, or high-effort strategy synthesis, it should ask:

```text
Can Cursor or Claude produce compact evidence for this while Codex waits?
```

If yes, route the work out:

- Cursor first for mechanical local work, inventories, path/hash/file summaries, validator triage, and bounded first drafts.
- Claude subscription for hard synthesis, contradiction review, architecture/routing critique, or high-effort Sonnet review.
- Git/GitHub worker analysis for read-only repository, CI, PR, issue, dirty-worktree, and checkpoint-boundary investigation above threshold.

Codex should then review the compact result, make final decisions, apply any final patches, and validate. Codex should not live-tail worker output or redo the worker task unless the worker handoff is incomplete or unsafe.

Worker delegation does not replace progress. A worker handoff counts only when it returns compact evidence that advances a concrete ComfyUI runtime/orchestration/QA task or materially reduces Codex active reasoning.

## Lane 1: Codex Desktop Final Authority

Codex owns:

- final project decisions and user-facing summaries;
- visual QA and final image/video judgment;
- Git checkpoint, add, commit, push, reset, checkout, restore, clean, merge, rebase, and branch decisions;
- GitHub PR, issue, label, release, workflow, and project mutation decisions;
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

## Lane 4: Git/GitHub Worker Analysis

Use `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED` when Git or GitHub investigation exceeds a tiny check but does not itself require mutation authority.

This lane delegates read-only analysis and draft preparation only. Codex remains the only executor for any Git or GitHub mutation.

Use Cursor first for:

- `git status`, `git diff --stat`, and `git diff --name-only` summaries;
- dirty-worktree grouping and checkpoint candidate lists;
- identifying unrelated or user-owned dirty files;
- read-only CI/log extraction;
- PR or issue comment inventory;
- draft commit messages, PR bodies, release notes, and checkpoint summaries;
- identifying whether Git/GitHub state blocks concrete ComfyUI progress.

Use Claude for:

- checkpoint-boundary risk review;
- branch/PR strategy;
- contradiction review across local evidence, Git state, GitHub Actions, and project policy;
- deciding whether Git/GitHub state is a true blocker after Cursor extraction.

For GitHub PR, issue, comment, label, reaction, review, release, and metadata reads, prefer the connected GitHub app/connector when available. Use local `gh` mainly for current-branch PR discovery, GitHub Actions logs, and local checkout correlation.

Reference:

```text
C:\Comfy_UI_Main\Plan\Instructions\GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md
```

## Routing Order

1. If the task involves final authority, live runtime, masks, Git/GitHub mutation, Jira, S3, EC2, or visual QA, keep final execution in Codex.
2. If the task is Git/GitHub read-only analysis above threshold, use `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
3. If the task is mechanical local reading, inventory, triage, or drafting, send it to Cursor first.
4. If the task is hard synthesis or strategy review, use Claude subscription after Cursor extraction or as the primary heavy-review lane.
5. Codex reviews compact worker evidence and decides the final action.

## Mandatory Pre-Work Delegation Gate

Before Codex starts any broad scan, audit, helper draft, multi-file diagnosis, evidence extraction, strategy review, or Git/GitHub investigation above a tiny check, it must classify the work with exactly one gate:

- `CODEX_ONLY_AUTHORITY`
- `CURSOR_FIRST_REQUIRED`
- `CLAUDE_HEAVY_REVIEW_REQUIRED`
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
- `NO_WORKER_NEEDED_UNDER_THRESHOLD`

If Codex selects `CODEX_ONLY_AUTHORITY`, it must record the authority reason, such as visual QA, Git/GitHub mutation, EC2, S3, Jira, masks, Wave70/Wave71 gates, Items/Tracker status mutation, or final acceptance.

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
- More than 5 changed files in Git status: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- More than one Git/GitHub failure source: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- CI/log review beyond a tiny bounded read: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- Unclear checkpoint boundary, PR review inventory, branch/upstream divergence analysis, or GitHub Actions diagnosis likely to take more than 3 minutes: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- Failed or incomplete worker output: retry once with a narrower work order before Codex absorbs the task.

Codex may bypass these triggers only when the task is explicitly in final authority scope, and the bypass reason must be recorded.

## Fallback Rules

If Cursor is unavailable or returns incomplete output, Codex should narrow and retry once before doing the work directly.

If Claude subscription auth is missing, expired, non-`claude.ai`, or API-key fallback risk is present, Codex must route the work to Cursor or record `CLAUDE_SUBSCRIPTION_UNAVAILABLE`.

If Git/GitHub worker analysis is incomplete, Codex should narrow the work order to one of: dirty-worktree grouping, CI failure extraction, PR comment inventory, checkpoint-boundary synthesis, or branch/upstream state summary. Codex may absorb the work only after one narrow retry or when the Git/GitHub decision is urgent final authority.

When Codex performs fallback work directly, it must record:

- original worker gate;
- worker failure reason;
- narrower retry attempted yes/no;
- why direct Codex work was necessary.

## Delegation Adoption Recovery Mode

Use `DELEGATION_ADOPTION_RECOVERY_MODE` when the combined worker monitor reports `usage_reduction_confidence=LOW`, estimated usage reduction below 40%, no useful Cursor/Claude/GitHub worker-analysis handoff in the last 4 hours, or repeated `AI_WORKER_DELEGATION_DRIFT`.

While this mode is active, Codex must not wait passively for behavior to improve. The next worker-eligible task must be delegated before Codex absorbs it, unless it is clearly final authority.

Temporary tightened triggers:

- More than 3 files to inspect: Cursor first.
- More than one script/helper to inspect or patch-plan: Cursor first.
- Any QA helper failure or long validation-result interpretation: Cursor first for extraction, then Codex final judgment.
- Any dirty-worktree grouping, checkpoint-boundary review, GitHub warning analysis, CI/log read, PR/comment inventory, or branch/upstream ambiguity: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- More than 2 minutes of active strategy or contradiction reasoning: Claude subscription when auth is healthy.
- Any incomplete worker output: one narrower retry is required before direct Codex fallback.

Claude adoption floor: if the latest monitor window shows zero useful Claude handoffs while Claude subscription auth is healthy, the next eligible high-effort synthesis, contradiction review, routing critique, checkpoint-risk synthesis, or strategy review expected to take more than 2 minutes must use `CLAUDE_HEAVY_REVIEW_REQUIRED` before Codex absorbs it. Do not route mechanical extraction, final authority, live runtime, visual QA, Git/GitHub mutation, AWS, Jira, masks, or tracker mutation to Claude.

Cursor friction retry discipline: if Cursor fails because of wrapper invocation, parser, environment, or lock friction, retry once with the smallest safe work order: ask mode, supplied file/status list, no worker-side broad Git discovery, no file edits, no mutation authority, and PowerShell execution-policy bypass only for the child wrapper process when needed. If the retry fails, classify `CURSOR_WRAPPER_FRICTION_COMPACT_FALLBACK`, record the failure evidence, and fall back compactly instead of live-tailing or absorbing a long task silently.

Exit recovery mode only after at least two useful compact worker handoffs occur in real project work, or after one audit window reports `usage_reduction_confidence=MEDIUM` or better with no direct-Codex worker-lane violations.

The monitor should classify continued direct Codex analysis during recovery mode as `AI_WORKER_DELEGATION_DRIFT`.

## Monitor Scoring

The combined AI worker monitor must score each audit window with:

- worker-eligible tasks detected;
- worker handoffs attempted;
- successful compact handoffs;
- incomplete or failed handoffs;
- Codex fallback cases;
- direct-Codex violations where eligible work was done without a worker handoff;
- Git/GitHub worker-analysis tasks detected;
- Git/GitHub analysis handoffs attempted;
- Git/GitHub direct-Codex analysis violations;
- worker mutation attempts detected;
- `git_github_worker_analysis_tasks_detected`
- `git_github_analysis_handoffs_attempted`
- `git_github_direct_codex_analysis_violations`
- `git_github_worker_mutation_attempts_detected`
- `git_github_connector_first_compliance`
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

Git/GitHub worker-analysis handoffs must additionally return:

- `git_github_scope:`
- `commands_run_read_only:`
- `changed_files_grouped:`
- `risks:`
- `recommended_codex_commands:`
- `mutation_boundary: Codex-only`

Codex should retry narrower or classify the lane as unavailable when the output is incomplete.

Worker-health audits must finish with parseable final JSON. A stale `IN_PROGRESS` stub is acceptable only when a newer final audit supersedes it; otherwise it is a monitor defect, not project progress.

## Forbidden Delegation

Do not delegate these final decisions to Cursor or Claude:

- live EC2 start/stop;
- S3 upload;
- ComfyUI generation;
- Git mutation;
- GitHub mutation;
- Jira mutation;
- mask promotion or Wave70 hard gates;
- Wave71+ activation;
- final visual QA approval;
- Items/Tracker status mutation.
