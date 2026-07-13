# Automation Cron Fleet Supervision Strategy

Updated: 2026-07-13

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

Usage-reduction scoring must use the deterministic snapshot and burn-rate tools when a current finalized snapshot exists:

```text
C:\Comfy_UI_Main\tools\New-CodexDesktopUsageSnapshot.ps1
C:\Comfy_UI_Main\tools\Measure-AIWorkerCodexUsageReduction.ps1
C:\Comfy_UI_Main\tools\Measure-AIWorkerNetUsageReductionProxy.ps1
```

Without two comparable post-baseline measurements, the monitor may report only a proxy estimate or a single measured result and must cap confidence at `MEDIUM`. Proxy scoring must include final-authority minutes, review/validation, failed-handoff recovery, orchestration, direct eligible Codex work, and incremental scheduled-automation overhead.

Cron jobs should reinforce this division:
- Use Cursor-first for broad mechanical local reads, inventories, parser/validator triage, file/path/hash summaries, and first-pass drafts.
- Use exact `claude-sonnet-5` as the primary worker when semantic synthesis is the hard part. Use exact `claude-opus-4-8` only through the audited escalation contract; Opus is never a routine extra reviewer.
- Keep Codex Desktop on final authority: project steering, live runtime decisions, visual QA, Git/AWS/S3/Jira/mask authority, final validation, and user-facing conclusions.

The seven project cron prompts must inherit the shared worker and Git/GitHub policies by path. Do not copy the full Git/GitHub routing policy into every prompt. Keep each prompt role-specific and compact; update the shared policy once. The combined delegation monitor is separate from the seven project jobs and is the sole recurring worker-health authority.

Routine cron orchestration should use the smallest proven Codex model at low reasoning. A heavier automation model is justified only for an explicitly documented non-deterministic final-authority review that cannot be delegated. Broad mechanical cron reads route to Cursor; difficult non-authority synthesis routes to Claude; the cron retains only compact orchestration and its role-specific final classification.

A cron audit should classify `CODEX_USAGE_DRIFT` only when the main session repeatedly performs long worker-suitable scans or synthesis directly in Codex while worker lanes are healthy. The first correction should be a compact recommendation to delegate the next suitable task, not a broad interruption or new bookkeeping task.

## Worker Lane Policy

Use five explicit lanes:

1. Codex-only
   - final authority for runtime, mask, Git, Jira, AWS, EC2, S3, and visual QA decisions
   - any gated action or project-state mutation
2. Cursor-first
   - broad inventories
   - read-only evidence extraction
   - helper/script first drafts
   - parser/validator triage
   - bookmark/task split diagnosis
3. Claude Sonnet primary
   - first substantive semantic synthesis when reasoning is the hard part
   - long contradiction review
   - difficult strategy critique when no live authority is required
   - bounded safety and evidence-authority review
4. Claude Opus escalation
   - one adjudication for unresolved, high-severity, cross-system, or architectural decisions
   - exact escalation reason, decision unit, hash-bound scope, prior Sonnet evidence or explicit direct exception
   - at most two completed Opus calls per local day during the pilot, counted globally across project roots and capability probes
5. Git/GitHub worker analysis
   - read-only dirty-worktree, diff, CI, PR, issue, and branch-state investigation
   - Cursor first for mechanical extraction
   - Claude for checkpoint, branch, PR, or push-risk synthesis
   - Codex-only for all Git and GitHub mutations

Claude Desktop/subscription is available through:

```text
C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1
```

Use the Claude subscription lane only when `Test-ClaudeSubscriptionHandoff.ps1` passes or the latest successful probe is fresh. It must use `claude.ai` first-party subscription auth, exact model IDs, credential-scrubbed child execution, and unchanged worktree fingerprints. It must not fall back to Anthropic API keys or Console PAYG. Routine health checks must not consume Opus.

## Mandatory Pre-Work Delegation Gate

Before any cron job performs a broad scan, audit, helper draft, multi-file diagnosis, evidence extraction, or strategy review, it must apply the gate from `AI_WORKER_LANE_ROUTING_POLICY.md`:

- `CODEX_ONLY_AUTHORITY`
- `CURSOR_FIRST_REQUIRED`
- `CLAUDE_SONNET_PRIMARY_REQUIRED`
- `CLAUDE_OPUS_ESCALATION_REQUIRED`
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
- `DETERMINISTIC_FAST_PATH`

Hard thresholds:

- More than 10 files: Cursor first.
- More than one major tree: Cursor first.
- More than one broad `rg` or inventory pass: Cursor first.
- More than one validator/parser triage pass: Cursor first.
- More than 3 minutes active Codex reasoning: Cursor or Claude.
- Strategy/contradiction review: `CLAUDE_SONNET_PRIMARY_REQUIRED` unless final authority applies.
- Opus requires the centralized escalation contract; a cron prompt may not call Opus merely because a task is long.
- More than 5 unclassified changed files, more than one ownership group or Git/GitHub failure source, long CI logs, unclear checkpoint boundaries, branch/upstream divergence analysis, or PR/review triage over 3 minutes: Git/GitHub worker analysis first.
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

Claude adoption floor: if the latest audit window shows zero useful Claude handoffs while subscription auth is healthy, the monitor should require the next eligible synthesis, contradiction review, routing critique, checkpoint-risk synthesis, or strategy review to use `CLAUDE_SONNET_PRIMARY_REQUIRED` before Codex absorbs it. This floor does not apply to mechanical extraction or final authority.

Score Claude's share over 24 hours. The target is 60-70% of eligible non-authority semantic/synthesis work, plus at least one Sonnet handoff in any four-hour window containing two or more eligible semantic tasks. Opus has no minimum-use target. Do not create duplicate reviews to satisfy these targets.

Cursor friction retry discipline: wrapper invocation, parser, environment, or lock friction should be followed by one narrow retry before Codex fallback. The retry should use ask mode, a hash-validated scope packet or supplied file/status list, no worker-side broad Git discovery, no file edits, and no mutation authority. The wrapper owns process-local execution-policy bypass. If the retry fails, classify `CURSOR_WRAPPER_FRICTION_COMPACT_FALLBACK` and record the fallback reason.

Git LFS capability gaps are not generic wrapper friction. Git/LFS work must use `-RequireGitLfs`. Missing WSL capability is `CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS`; repair it once or use one hash-recorded Windows packet from `tools\Export-GitLfsReadOnlyEvidence.ps1`. Do not credit partial LFS grouping, do not send mechanical LFS extraction to Claude, and do not normalize recurring Codex fallback.

Any ask/plan Cursor worktree change is `CURSOR_HANDOFF_READ_ONLY_MUTATION_VIOLATION`. Exclude it from useful credit, require Codex to preserve user-owned changes, and diagnose the exact command or script that wrote files.

Broad Cursor discovery must pass `-ScopePacketPath` or use the explicit `-AllowBroadDiscovery -BroadDiscoveryReason` exception. The normal timeout ceiling is 600 seconds; only an explicit broad-discovery exception may use up to 900 seconds.

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
- `claude_adoption_floor_active`
- `cursor_wrapper_friction_retry_attempted`
- `estimated_codex_work_avoided_minutes`
- `estimated_usage_reduction_percent`
- `usage_reduction_confidence`
- `codex_final_authority_minutes`
- `codex_review_and_validation_minutes`
- `codex_failed_handoff_recovery_minutes`
- `codex_worker_orchestration_minutes`
- `direct_codex_worker_eligible_minutes`
- `incremental_scheduled_codex_minutes`
- `net_estimated_usage_reduction_percent`
- `scope_packet_compliance_percent`
- `malformed_path_or_write_scope_violations`
- `stale_or_interrupted_worker_records`
- `git_lfs_tasks_detected`
- `cursor_git_lfs_native_capability_passes`
- `cursor_git_lfs_capability_gaps`
- `windows_git_lfs_evidence_bridges`
- `direct_codex_git_lfs_analysis_fallbacks`
- `claude_sonnet_primary_handoffs`
- `claude_opus_escalation_handoffs`
- `claude_opus_escalations_justified`
- `claude_opus_escalations_rejected`
- `claude_opus_daily_ceiling_rejections`
- `claude_subscription_capacity_unavailable`
- `claude_worker_reported_blocked`
- `claude_invalid_status_labels`
- `claude_read_only_mutation_violations`
- `claude_concurrent_worktree_drift_detected`
- `adopted_worker_outputs`
- `duplicate_review_cycles_detected`

The combined worker monitor is the sole recurring Cursor/Claude/GitHub delegation-health authority. A separate Claude-only monitor is redundant once the combined monitor verifies subscription auth, the Claude adoption floor, and substantive Claude handoffs. Keep ordinary monitor runs small-model, low-effort, and bounded; use a heavyweight model only for an explicitly requested deep effectiveness review.

For Opus daily-ceiling and duplicate-decision accounting, the combined monitor must read `C:\Users\kevin\.codex\claude_subscription_handoff\opus_usage\YYYY-MM-DD`. Project-local handoff directories remain the source for task outcomes; the external ledger is the cross-project source for completed Opus consumption.

## Role-Specific Claude Invocation Rules

- EC2 hourly sentinel: no Cursor or Claude during normal bounded checks; Sonnet only after repeated conflicting safety evidence; never call Opus automatically.
- Automation fleet health: Sonnet only for a genuine shared-policy contradiction; never call Opus routinely.
- Combined worker monitor: never launch Cursor, Sonnet, or Opus. It observes finalized records and runs deterministic verification only when required.
- Two-hour anti-loop supervisor: Sonnet for a real multi-source progress contradiction; Opus only when one Sonnet pass cannot resolve a cross-authority deadlock.
- Six-hour milestone auditor: Sonnet for real sequence or ledger contradiction; Opus only for unresolved cross-wave authority conflict.
- Daily artifact QA: Cursor performs inventory; Sonnet is the normal semantic review when contradictory evidence remains; Opus only for certification-level contradiction.
- Daily cost/local-first audit: Sonnet for cross-system cost/readiness contradiction; Opus only for unresolved architecture, never routine cost checks.
- Weekly consistency audit: Cursor performs bounded inventory and Sonnet performs the normal semantic pass; at most one Opus escalation when Sonnet cannot reconcile authoritative policies.

All eight active automations remain `gpt-5.4-mini` low-effort orchestrators. The seven project jobs plus the combined monitor inherit the complete contract from shared policy; each prompt carries only its role-specific clause.

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

Every steering message must name `C:\Comfy_UI_Main` as the authoritative `ProjectRoot`. If the target thread metadata reports legacy `C:\Comfy_UI`, require explicit commands and worker packets to use Main; do not copy or recreate work to reconcile the thread's displayed directory.

When correction is needed, steer toward one concrete next ComfyUI task:
- selected inpaint deploy-bundle rebuild/revalidation;
- selected S3 publish readiness or proof;
- selected input/model install proof;
- workflow wiring/runtime package validation;
- live-gated target-runtime preparation after explicit user authorization.

Do not steer to broad Wave65 refreshes, generic manifest hygiene, repeated hydration rewrites, Jira bookkeeping, or deferred Wave71+ work unless the user explicitly selects that lane.

When the main session needs broad local scanning, manifest reconciliation, or repetitive evidence extraction, route that work to Cursor first and keep Codex on the final judgment and bounded correction pass.

Use Sonnet 5 before Codex absorbs eligible difficult synthesis, not only as a final reviewer after Codex has already done the reasoning. Allow one Sonnet remediation confirmation. Use Opus 4.8 only after its centralized escalation contract passes. Do not route mask, EC2, S3, Jira, Git, Items/Tracker authority, or final visual QA decisions to Claude.

## Cursor, Jira, And Masks

Cursor read-only delegation should use ask mode first and must not be counted if it returns only progress/promise text.

Jira remains a control-plane board only. Do not bulk-create or recreate Jira Stories, Tasks, or Sub-tasks from the local ledger.

Manual gold masks remain a dependency boundary. Do not promote masks, consume candidate masks as truth, rerun Wave70 hard gates, or activate Wave71+ unless the user has explicitly declared the required gold masks ready and the relevant gates pass.

## Canonical Worker Package And Monitor Boundary

All eight active automations inherit the worker rules from `AI_WORKER_LANE_ROUTING_POLICY.md`; do not duplicate the full contract in each prompt. Their canonical TOML templates live under `tools/ai_worker_handoffs/automations` and are installed only through the hash-validated package installer. Active jobs remain `gpt-5.4-mini` with low reasoning and `C:\Comfy_UI_Main` as their only project cwd. The two retired/replaced jobs remain paused in the canonical package.

The combined monitor may run only static wrapper/package drift verification. It must never pass a live-probe switch or launch Cursor, Sonnet, or Opus. It separately counts Cursor worker-blocked results, invalid status/confidence, scoped mutation, concurrent drift, Claude tool-isolation drift, unjustified Opus attempts, invalid Opus usage markers, and live/canonical package drift. The seven project jobs may request a worker only for real role-specific work allowed by the shared routing policy; normal EC2 sentinel checks never launch a worker.
