# Automation Cron Fleet Supervision Strategy

Updated: 2026-07-09

This protocol defines the Comfy_UI_Main scheduled automation fleet posture while the main Codex session advances the ComfyUI project autonomously.

All automation routing must also follow:

```text
C:\Comfy_UI_Main\Plan\Instructions\AI_WORKER_LANE_ROUTING_POLICY.md
```

## Local Source Of Truth And EC2 Stale Workspace Guard

All cron jobs must read `C:\Comfy_UI_Main\Plan\Instructions\LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md` before steering runtime, EC2, S3, deploy-bundle, artifact pullback, Items, Tracker, or hydration work.

The local workspace `C:\Comfy_UI_Main` is the authoritative execution ledger. The EC2 copy `/home/ubuntu/Comfy_UI_Main` is runtime/cache state only and must not be used to select current work, resurrect queued rows, or override local completion evidence.

Verified 2026-07-09 finding: approved EC2 instance `i-0560bf8d143f93bb1` was inspected and stopped; ComfyUI auto-started but was idle (`queue_running=[]`, `queue_pending=[]`, current history count `0`), no generation was launched, and the EC2 project copy had only older 2026-07-07 runtime artifacts plus a stale three-lane queue where Canny could appear queued. Local `C:\Comfy_UI_Main` had newer 2026-07-09 selected-inpaint readiness evidence and the current nine-lane queue.

Use these classifications when relevant: `LOCAL_SOURCE_OF_TRUTH_ACTIVE`, `EC2_WORKSPACE_STALE_NOT_AUTHORITY`, `NO_RERUN_COMPLETED_EC2_PROOF`, `SELECTED_INPAINT_TARGET_RUNTIME_NOT_DUPLICATE`, and `BLOCKED_EC2_STALE_QUEUE_SOURCE`.

Do not rerun completed EC2/local work as new work: low-risk fallback first runtime proof, RealVisXL base smoke/proof and prior certification sample runs, baseline/Canny v4 target-runtime smoke proof, or the 2026-07-09 active-lane local package smoke/visual QA matrix. Still-open selected-inpaint work is not duplicate only when intentionally selected and live gates pass: deploy-bundle rebuild/revalidation, S3 publish proof, EC2 input/model install hash proof, selected target-runtime proof, and final certification.

## Primary Objective

The fleet exists to keep the main session making concrete ComfyUI progress. Cron jobs must not become a parallel bookkeeping project.

Cron jobs are supervisors, not parallel project managers. Their default behavior is to observe, classify, and write compact external audits without interrupting the main session.

Main-session interruption is allowed only when the finding is blocking or safety-critical:
- EC2/GPU spend risk, expired runtime window, or unsafe running instance;
- main session classified as `LOOPING_BOOKKEEPING` or equivalent repeated non-progress;
- missing, paused, broken, or non-finalizing automation that affects safety/progress;
- sequence drift that would activate deferred waves or repeat completed work;
- repo/deploy/live-gate defect that the main session is about to violate;
- worker-lane failure that is causing Codex Desktop to absorb long delegated tasks.

Routine QA gaps, consistency findings, stale-but-superseded audit stubs, Jira control-plane notes, and non-blocking ledger mismatches should be written to external audit/evidence only. They should not message or redirect the main session unless they become blocking.

Concrete progress means one of:
- selected inpaint/runtime lane implementation or workflow wiring;
- deploy-bundle rebuild/revalidation planning or proof;
- S3 publish readiness or dry-run proof for selected runtime assets;
- input/model install proof;
- local ComfyUI object_info or runtime readiness proof;
- generated artifact QA when live gates allow it;
- narrow validator/helper work that directly unblocks runtime/QA/cost safety.

Hydration, proof-log, tracker, manifest, index, Git, or audit updates do not count as progress unless they follow a concrete ComfyUI runtime/orchestration/QA artifact.

## Codex Desktop Usage Reduction

The Cursor and Claude subscription lanes exist to reduce Codex Desktop usage so the autonomous ComfyUI build can run longer without exhausting weekly limits.

Expected reduction target: at least 50% less active Codex Desktop time for broad local scanning, repetitive evidence extraction, first-pass helper/script drafting, long contradiction review, and high-effort synthesis.

Cron jobs should reinforce this division:
- Use Cursor-first for broad mechanical local reads, inventories, parser/validator triage, file/path/hash summaries, and first-pass drafts.
- Use Claude subscription for high-effort Sonnet synthesis, contradiction review, or strategy critique after Cursor extraction or when synthesis is the main task.
- Keep Codex Desktop on final authority: project steering, live runtime decisions, visual QA, Git/AWS/S3/Jira/mask authority, final validation, and user-facing conclusions.

A cron audit should classify `CODEX_USAGE_DRIFT` only when the main session repeatedly performs long worker-suitable scans or synthesis directly in Codex while worker lanes are healthy. The first correction should be a compact recommendation to delegate the next suitable task, not a broad interruption or new bookkeeping task.

## Worker Lane Policy

Use four explicit lanes:

1. Codex-only
   - final authority for runtime, mask, Git, Jira, AWS, EC2, S3, and visual QA decisions
   - any gated action or project-state mutation
2. Cursor-first
   - broad inventories
   - read-only evidence extraction
   - helper/script first drafts
   - parser/validator triage
   - bookmark/task split diagnosis
3. Claude subscription
   - high-effort Sonnet synthesis after Cursor extraction
   - long contradiction review
   - difficult strategy critique when no live authority is required
   - heavy reasoning tasks that would otherwise consume a long Codex Desktop turn
4. Git/GitHub worker analysis
   - read-only dirty-worktree, diff, CI, PR, issue, and branch-state investigation
   - Cursor first for mechanical extraction
   - Claude for checkpoint, branch, PR, or push-risk synthesis
   - Codex-only for all Git and GitHub mutations

Claude Desktop/subscription is available through:

```text
C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1
```

Use the Claude subscription lane only when `Test-ClaudeSubscriptionHandoff.ps1` passes or the latest successful probe is fresh. It must use `claude.ai` subscription auth and must not fall back to Anthropic API keys or Console PAYG billing.

## Mandatory Pre-Work Delegation Gate

Before any cron job performs a broad scan, audit, helper draft, multi-file diagnosis, evidence extraction, or strategy review, it must apply the gate from `AI_WORKER_LANE_ROUTING_POLICY.md`:

- `CODEX_ONLY_AUTHORITY`
- `CURSOR_FIRST_REQUIRED`
- `CLAUDE_HEAVY_REVIEW_REQUIRED`
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
- `NO_WORKER_NEEDED_UNDER_THRESHOLD`

Hard thresholds:

- More than 10 files: Cursor first.
- More than one major tree: Cursor first.
- More than one broad `rg` or inventory pass: Cursor first.
- More than one validator/parser triage pass: Cursor first.
- More than 3 minutes active Codex reasoning: Cursor or Claude.
- Strategy/contradiction review: Claude Sonnet unless final authority applies.
- More than 5 changed files, more than one Git/GitHub failure source, long CI logs, unclear checkpoint boundaries, branch/upstream divergence analysis, or PR/review triage over 3 minutes: Git/GitHub worker analysis first.
- Failed worker output: retry once with a narrower work order before Codex absorbs the task.

Each cron audit that touches worker-eligible work should record the selected gate, the worker handoff path if used, and any fallback reason.

## Delegation Adoption Recovery Mode

If the combined worker monitor reports `usage_reduction_confidence=LOW`, estimated reduction below 40%, no useful Cursor/Claude/GitHub worker-analysis handoff in the last 4 hours, or repeated `AI_WORKER_DELEGATION_DRIFT`, treat the main session as being in `DELEGATION_ADOPTION_RECOVERY_MODE`.

In recovery mode, cron jobs should not simply report that delegation is available. They should verify whether the next worker-eligible main-session task was actually delegated. The next broad scan, multi-file diagnosis, QA helper interpretation, Git/GitHub analysis, or >2 minute synthesis task should use Cursor, Claude, or `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED` unless final authority applies.

Use tightened temporary triggers until adoption recovers:

- More than 3 files: Cursor first.
- More than one script/helper: Cursor first.
- Any long QA/validation-result interpretation: Cursor extraction first.
- Any dirty-worktree, checkpoint-boundary, GitHub warning, CI/log, PR/comment, or branch/upstream analysis: Git/GitHub worker analysis first.
- More than 2 minutes strategy/contradiction reasoning: Claude subscription when healthy.

Exit recovery mode only after two useful compact real worker handoffs or one audit window with `usage_reduction_confidence=MEDIUM` or better and no direct-Codex worker-lane violations.

Monitor Scoring fields for worker-aware audits:

- `worker_eligible_tasks_detected`
- `worker_handoffs_attempted`
- `successful_compact_handoffs`
- `incomplete_or_failed_handoffs`
- `codex_fallback_cases`
- `direct_codex_worker_lane_violations`
- `git_github_worker_analysis_tasks_detected`
- `git_github_analysis_handoffs_attempted`
- `git_github_direct_codex_analysis_violations`
- `git_github_worker_mutation_attempts_detected`
- `git_github_connector_first_compliance`
- `estimated_codex_work_avoided_minutes`
- `estimated_usage_reduction_percent`
- `usage_reduction_confidence`

## Role Ownership

- The two-hour anti-loop supervisor is the primary progress and repo-cleanliness watchdog.
- The fleet-health supervisor verifies that the automation fleet itself is healthy and that the two-hour supervisor finalizes audits.
- The EC2 cost sentinel owns EC2/cost safety only.
- The daily artifact QA audit owns artifact/evidence integrity only.
- The daily cost/local-first audit owns local-first and EC2-on-time posture only.
- The six-hour milestone auditor owns sequence and milestone drift only.
- The weekly consistency audit owns Plan/Instructions/Items/Tracker consistency only.

Specialist jobs may report drift, but they should not all steer the main session. Use the shared correction lock before any steering message or project file edit.

Main-session steering ownership:
- The two-hour supervisor is the only routine progress-steering job.
- EC2 sentinel may interrupt only for EC2/GPU safety.
- Fleet health may interrupt only for missing/broken/non-finalizing automations or worker-lane health failure.
- Daily artifact, daily cost, six-hour milestone, and weekly consistency audits should default to external audit-only unless their finding is blocking or safety-critical.
- Cursor/Claude monitors should not steer project work; they may steer only worker-lane repair or usage-reduction drift.

## Audit Finalization And Stale Stub Handling

Every cron job that writes an audit must finish with a parseable final JSON record. Acceptable final statuses include `FINALIZED`, `FINAL`, `DEGRADED_FINALIZED`, or a documented monitor-specific pass/degraded status. A standalone `IN_PROGRESS` record is not a final audit.

If a job creates an `IN_PROGRESS` stub and later writes a separate final audit, the final audit must reference or supersede that stub when possible. Future fleet-health reviews should classify an old `IN_PROGRESS` stub as `STALE_IN_PROGRESS_SUPERSEDED` only when a newer final audit for the same automation/run window exists. If no newer final audit exists, classify it as `STALE_IN_PROGRESS_UNRESOLVED`.

Cron jobs must not repeatedly regenerate audits just to clean historical stubs. Record the stale-stub finding once, keep the audit external unless it blocks runtime safety, and return attention to concrete selected-inpaint runtime/orchestration work.

## Repo Cleanliness

Cron jobs may inspect repository state but must not mutate it. They must not run git add, commit, push, reset, checkout, restore, clean, or destructive cleanup.

When repo or GitHub investigation exceeds a tiny check, use `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED` before Codex spends a long turn on diff, CI, PR, issue, or branch-state analysis. Workers may produce read-only evidence and draft recommended Codex commands. Codex alone may execute Git/GitHub mutations.

Git/GitHub worker-analysis handoffs must preserve `mutation_boundary: Codex-only`.

For GitHub PR, issue, comment, label, reaction, review, release, and metadata reads, prefer the connected GitHub app/connector when available. Use local `gh` mainly for current-branch PR discovery, GitHub Actions logs, and local checkout correlation.

Use these classifications where applicable:
- REPO_SYNC_BLOCKER: repo or origin state blocks live deploy/EC2 gates, but local ComfyUI work can continue.
- REPO_CLEAN_RESUME_COMFYUI_WORK: repo gate is clean; stop Git/hydration/checkpoint churn and return to selected inpaint runtime/orchestration work.
- LOOPING_BOOKKEEPING: the main session is spending repeated turns on hydration, proof logs, trackers, manifests, Git dry-runs, or audit cleanup without a new concrete runtime/QA artifact.
- ADVANCING_WITH_REPO_SYNC_BLOCKER: concrete ComfyUI runtime/orchestration progress is happening, but live execution remains blocked by repo/origin state.

## Main-Session Steering

When correction is needed, steer toward one concrete next ComfyUI task:
- selected inpaint deploy-bundle rebuild/revalidation;
- selected S3 publish readiness or proof;
- selected input/model install proof;
- workflow wiring/runtime package validation;
- live-gated target-runtime preparation after explicit user authorization.

Do not steer to broad Wave65 refreshes, generic manifest hygiene, repeated hydration rewrites, Jira bookkeeping, or deferred Wave71+ work unless the user explicitly selects that lane.

When the main session needs broad local scanning, manifest reconciliation, or repetitive evidence extraction, route that work to Cursor first and keep Codex on the final judgment and bounded correction pass.

Use Claude as the high-effort Sonnet lane after Cursor has extracted raw evidence, or when the task is a difficult synthesis that does not require live authority. Do not route mask, EC2, S3, Jira, Git, Items/Tracker authority, or final visual QA decisions to Claude.

## Cursor, Jira, And Masks

Cursor read-only delegation should use ask mode first and must not be counted if it returns only progress/promise text.

Jira remains a control-plane board only. Do not bulk-create or recreate Jira Stories, Tasks, or Sub-tasks from the local ledger.

Manual gold masks remain a dependency boundary. Do not promote masks, consume candidate masks as truth, rerun Wave70 hard gates, or activate Wave71+ unless the user has explicitly declared the required gold masks ready and the relevant gates pass.
