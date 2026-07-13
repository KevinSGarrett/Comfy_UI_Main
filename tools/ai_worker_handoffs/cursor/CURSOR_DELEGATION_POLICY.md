# Comfy_UI_Main Cursor Delegation Policy

Status: active external policy
Date: 2026-07-13
Owner: Codex Desktop orchestrator plus Cursor CLI worker

## Objective

Reduce Codex Desktop active usage by at least 50% by moving bounded local worker tasks to Cursor CLI while keeping Codex responsible for orchestration, final QA, visual judgment, safety decisions, and project-state authority.

Cursor is a usage-reduction worker lane, not a project manager. Its job is to absorb broad scans, repetitive local reads, summaries, triage, and first-pass drafts so Codex Desktop can stay focused on final decisions and selected-inpaint ComfyUI runtime/orchestration progress.

## Shared ComfyUI Boundaries

Cursor work and Cursor-health monitoring must respect the project policies:

```text
C:\Comfy_UI_Main\Plan\Instructions\AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md
C:\Comfy_UI_Main\Plan\Instructions\JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md
```

Local `C:\Comfy_UI_Main` is authoritative. EC2 `/home/ubuntu/Comfy_UI_Main` is runtime/cache state only and must not be used to reopen completed fallback/base/Canny/local-smoke work.

Cursor delegation is useful only when it reduces Codex active work and returns compact evidence. Cursor handoffs, health checks, hydration updates, proof-log updates, tracker/index/manifest updates, Git dry-runs, and audit files do not count as project progress unless they directly support a concrete ComfyUI runtime/orchestration/QA artifact.

Cursor-health monitors should not interrupt the main session for ordinary audit results. They may steer only when Cursor is broken, producing repeated incomplete handoffs, causing Codex to redo long worker-suitable tasks, or creating safety/policy drift.

## Responsibility Split

Codex Desktop keeps ownership of:
- task selection, project management, and final acceptance;
- visual QA, generated image/video inspection, and final render decisions;
- user-facing summaries and blocker decisions;
- Git add/commit/push/reset/checkout/restore/clean/merge/rebase decisions;
- GitHub PR, issue, label, workflow, release, and project mutation decisions;
- EC2/AWS/S3 runtime start/stop decisions;
- mask promotion, Wave70 hard gates, Wave71+ activation, and Jira control-plane changes;
- final Items/Tracker status mutation.

Codex remains final authority. Cursor evidence is worker input only, even when it edits a narrow file under an explicit work order.

Cursor CLI should handle:
- long local file searches, inventories, and evidence summarization;
- static script/readiness review;
- first-pass implementation drafts inside explicitly allowed files;
- parser/validator failure triage;
- repetitive evidence extraction and compact report generation;
- docs/spec consistency review and gap lists;
- suggested patch plans for Codex to review;
- read-only Git/GitHub status, diff, CI, PR, issue, and checkpoint-boundary extraction;
- commit-message, PR-body, release-note, and checkpoint-summary drafts for Codex review;
- low-risk local-only helper generation when a work order explicitly allows writes.

## Required Handoff Pattern

Use the wrapper:

`C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1`

The wrapper launches Cursor with WSL workspace `/mnt/c/Comfy_UI_Main`, not the handoff-record directory. Work orders identify both Windows and WSL roots and require WSL filesystem commands to use the WSL root. Creating a Windows drive-name path inside the repository is a malformed-path failure.

The wrapper pins the Cursor worker to WSL distribution `Ubuntu-22.04`. Git/LFS work must use `-RequireGitLfs`; the wrapper preflights `git lfs version` and records the native or fallback route before Cursor starts. Use `-GitLfsEvidencePath` only with evidence created by `C:\Comfy_UI_Main\tools\Export-GitLfsReadOnlyEvidence.ps1`.

Codex must provide a compact work order. Cursor must return compact JSON/text evidence. Codex should review only the resulting summary, touched files, errors, and usage numbers unless the evidence requires deeper inspection.

Do not live-tail Cursor work. The usage-saving pattern is: create work order, wait for `handoff_record.json`, inspect the compact result, then decide the next action.

A Cursor call only counts as successful delegation when `handoff_record.json` has `status: PASS`, `classification: CURSOR_HANDOFF_COMPLETED`, no blocking `issues`, and a final result that includes `status:`, `summary:`, `files inspected:`, `blockers:`, and `recommended Codex follow-up:`. Promise-style answers such as "I will inspect next" or "next I will read" are incomplete handoffs and must be rerun with a narrower work order or recorded as Cursor unavailable.

The wrapper may store only a compact `cursor_result_excerpt` in `handoff_record.json`, but output-contract validation must use the full parsed Cursor result. Required labels appearing after the compact excerpt cutoff must not cause an incomplete-output classification. Records produced by the corrected wrapper identify `output_contract_validated_from: full_result`.

Cursor-health scheduled audits must write parseable final JSON. If an `IN_PROGRESS` stub exists, a newer final audit must supersede it; otherwise report the stale stub as a monitor defect and do not treat cleanup of that stub as project progress.

## Modes

- `ask`: default read-only explanation, summarization, triage, inventory, or design recommendation.
- `plan`: read-only implementation plan; use only when `ask` is insufficient or explicitly requested, because headless `plan` mode has been more likely to return progress-style text instead of final compact evidence.
- `agent`: may edit files only when the work order explicitly allows writes and allowed paths are narrow.

Default automation and main-session read-only behavior should prefer `ask`; use `plan` only after a successful recent `ask` result is insufficient. Use `agent` only for intentionally delegated implementation.

Scheduled automations should not use `agent` mode during normal audits. Use read-only `ask` first, then let Codex decide whether `plan` or a narrow manual write handoff is worth the risk.

For narrow `agent` write handoffs, `Invoke-CursorAgentHandoff.ps1` auto-enables Cursor `--force` only after `-AllowWrites` and explicit `-AllowedPaths` are supplied. The wrapper records `auto_force_cursor_commands=true`, snapshots Git status before/after the handoff, and fails the handoff as `CURSOR_HANDOFF_WRITE_SCOPE_VIOLATION` if any newly changed path falls outside the allowed path list. Codex must inspect the handoff record and final diff before accepting the worker output.

## Model Policy

Do not rely on Cursor `auto` for scheduled or delegated work unless a task is explicitly experimental. `auto` is useful for manual ad hoc Cursor sessions, but it makes recurring cost, latency, and quality less predictable.

Wrapper defaults:
- no explicit mode: `ask`
- `ask`, `plan`, and `agent`: `gpt-5.3-codex`

Fast Cursor model variants are prohibited for scheduled and delegated work because their observed credit cost is disproportionate. Use plain `gpt-5.3-codex`; route difficult semantic synthesis to the Claude subscription lane rather than escalating Cursor to a fast model.

Keep the model in the work order record. Prefer the cheapest model that can reliably produce a compact handoff.

## Hard Bans For Cursor Jobs

Cursor jobs must not:
- print or inspect `.env` secret values;
- print AWS keys, GitHub tokens, Civitai keys, Cursor keys, or credential-like values;
- run `git add`, `git commit`, `git push`, `git reset`, `git checkout`, `git restore`, `git clean`, merge, rebase, branch mutation, or staging/unstaging operations;
- run `git lfs install`, `track`, `untrack`, `migrate`, `pull`, `fetch`, `checkout`, or any LFS operation that changes configuration, attributes, pointers, the index, or working files;
- create, update, merge, close, or reopen GitHub PRs;
- mutate GitHub issues, labels, milestones, releases, workflows, projects, comments, reactions, or reviews;
- start EC2, stop EC2, upload to S3, launch ComfyUI GPU work, or run remote runtime commands;
- promote masks, consume candidate masks as truth, rerun Wave70 hard gates, activate Wave71+, or mutate Jira;
- regenerate broad trackers/packages unless the work order explicitly scopes that operation;
- perform whole-repo scans when a targeted path list is available.
- execute project scripts, tests, validators, generators, or audit helpers in ask/plan mode unless the work order explicitly declares the exact command side-effect-free.

The wrapper snapshots the complete dirty-worktree fingerprint before and after every mode. Any ask/plan change is `CURSOR_HANDOFF_READ_ONLY_MUTATION_VIOLATION`, even when the path was already dirty before the handoff. Read-only violations never count as useful delegation.

## Codex Usage Reduction Rules

1. Before doing a long local scan, broad static review, repetitive evidence extraction, or first-pass draft fix, Codex should create a Cursor work order and stop actively reasoning about the details.
2. Codex should not stream-follow Cursor work. It should wait for the wrapper evidence and inspect only the compact result.
3. If the compact result is missing, incomplete, or classified as `CURSOR_HANDOFF_INCOMPLETE_OUTPUT_CONTRACT`, Codex should rerun a narrower Cursor handoff rather than absorbing the long worker task back into Codex.
4. Automations should use Cursor for worker probes when the expected Codex analysis would exceed a small bounded read-only audit.
5. EC2 cost sentinel remains tiny and should not call Cursor during normal hourly checks.
6. Fleet health should verify Cursor handoff freshness and wrapper health, not re-run all project audits.

Delegation thresholds:
- Delegate when a task likely requires reading more than 10 files, scanning more than one major tree, or running more than one validator.
- Delegate when a local-only audit is expected to take more than 3 minutes of active Codex reasoning.
- Delegate first-pass summaries of Plan/Tracker/QA evidence by default.
- Delegate Git/GitHub analysis when there are more than 5 unclassified changed files, more than one ownership group or failure source, long CI logs, unclear checkpoint boundaries, or PR/review triage over 3 minutes.
- Keep Codex-only work under a compact probe unless there is a clear reason Cursor cannot do it.
- Escalate back to Codex only for final judgment, visual review, safety authority, or ambiguous blockers.

## Mandatory Pre-Work Delegation Gate

- `CODEX_ONLY_AUTHORITY`: allowed only for final authority tasks such as visual QA, Git, EC2, S3, Jira, masks, Wave70/Wave71 gates, Items/Tracker status mutation, or final acceptance.
- `CURSOR_FIRST_REQUIRED`: required when the task is mechanical local reading, inventory, parser/validator triage, helper draft work, or evidence extraction above threshold.
- `CLAUDE_HEAVY_REVIEW_REQUIRED`: use the Claude subscription lane for difficult synthesis or contradiction review when final authority is not involved.
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`: use Cursor first for read-only Git/GitHub extraction and draft preparation above threshold.
- `NO_WORKER_NEEDED_UNDER_THRESHOLD`: allowed only when the task remains below threshold.

Hard Cursor thresholds:
- More than 10 files to inspect.
- More than one major tree to inspect.
- More than one broad `rg` or inventory pass.
- More than one validator/parser triage pass.
- Helper/script first draft in a narrow local scope.
- Strategy/contradiction review should go to Claude subscription unless final authority applies.
- Git/GitHub analysis with more than 5 unclassified changed files, more than one ownership group or failure source, long CI logs, unclear checkpoint boundaries, branch/upstream ambiguity, or PR/review triage over 3 minutes.
- Machine-check threshold token: `More than 5 unclassified changed files`.

When Cursor output is incomplete, retry once with a narrower work order before Codex absorbs the task. If Codex performs direct fallback, record the worker failure reason and why direct fallback was necessary.

Use `C:\Comfy_UI_Main\tools\New-AIWorkerScopePacket.ps1` before task-selection or analysis handoffs whenever current authority files can provide an exact candidate set. The normal limit is 12 files. Whole-tree worker discovery requires an explicit reason and must not be the default first attempt.

Pass the generated packet with `-ScopePacketPath`. The wrapper validates all candidate hashes before Cursor starts. Broad discovery without a packet must use `-AllowBroadDiscovery -BroadDiscoveryReason <reason>`. The default and normal maximum timeout is 600 seconds. Only an explicit broad-discovery exception may request 601-900 seconds.

`-AllowedPaths` accepts a real PowerShell array and defensively normalizes accidental comma-, pipe-, semicolon-, or newline-delimited input. Git status capture is byte-safe and rejects control/private-use/drive-like repository paths. The wrapper reconciles abandoned `IN_PROGRESS` records once no worker lock/process remains and removes orphan locks whose recorded PID no longer exists.

Do not narrate repeated wait updates while Cursor runs. Start one bounded handoff, wait for its finalized record, and issue at most one timeout/retry update unless the user asks for status.

`KNOWN_SCOPE_GIT_FAST_PATH` is allowed when the current implementation already declared an exact include list, every changed path belongs to it, no unrelated dirty paths exist, branch/upstream state is known, and deterministic repository safety scripts perform the checks. Git mutation remains Codex-only. Any uncertainty routes to `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.

If Cursor fails because of wrapper invocation, parser, environment, or lock friction, retry once with the smallest safe work order: ask mode, a validated scope packet or supplied file/status list, no worker-side broad Git discovery, no file edits, and no mutation authority. The wrapper applies process-local PowerShell execution-policy bypass internally. If the retry fails, classify `CURSOR_WRAPPER_FRICTION_COMPACT_FALLBACK`, record the failure evidence, and keep the Codex fallback compact.

Git LFS capability uses a separate fail-closed path. If `git lfs version` fails in `Ubuntu-22.04`, classify `CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS`. Repair the environment once. If immediate repair is unavailable, export one Windows read-only evidence packet and rerun Cursor with `-GitLfsEvidencePath`. Do not count a partial LFS result as completed delegation and do not shift mechanical LFS extraction to Claude.

Git/GitHub Cursor output must include `git_github_scope:`, `commands_run_read_only:`, `changed_files_grouped:`, `risks:`, `recommended_codex_commands:`, and `mutation_boundary: Codex-only`.

For GitHub PR, issue, comment, label, reaction, review, release, and metadata reads, prefer the connected GitHub app/connector when available. Use local `gh` mainly for current-branch PR discovery, GitHub Actions logs, and local checkout correlation.

Monitor Scoring fields:

- `worker_eligible_tasks_detected`
- `worker_handoffs_attempted`
- `successful_compact_handoffs`
- `incomplete_or_failed_handoffs`
- `codex_fallback_cases`
- `direct_codex_worker_lane_violations`
- `cursor_required_but_missing_count`
- `git_github_worker_analysis_tasks_detected`
- `git_github_analysis_handoffs_attempted`
- `git_github_direct_codex_analysis_violations`
- `git_github_worker_mutation_attempts_detected`
- `git_github_connector_first_compliance`
- `estimated_codex_work_avoided_minutes`
- `estimated_usage_reduction_percent`
- `usage_reduction_confidence`
- `codex_final_authority_minutes`
- `codex_review_and_validation_minutes`
- `codex_failed_handoff_recovery_minutes`
- `codex_worker_orchestration_minutes`
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

## Success Metrics

- Cursor handoff wrapper works from PowerShell through WSL using `cursor-agent`.
- Cursor work orders produce evidence under `runtime_artifacts\agent_handoffs\cursor`.
- Cron prompts reference this policy and avoid doing long worker tasks directly in Codex.
- Codex main session uses Cursor for bounded local work after the current checkpoint completes.
- Codex active time should drop by at least half because Codex waits for summaries rather than performing every scan/review itself.

## Enforced Runtime Contract

The canonical wrapper is versioned in `tools/ai_worker_handoffs/cursor` and installed by hash. Cursor uses only plain `gpt-5.3-codex` in read-only ask/plan mode. Agent mode, project writes, `--force`, fast models, Claude models, and credential-store reads are prohibited. First-pass fixes are returned as proposed patches for Codex to apply.

Every bounded packet validates gate, worker lane, file count, per-file bytes and SHA-256, aggregate bytes, and repository containment. A blocked or invalid status receives no useful credit. A changed scoped file is a mutation violation; unrelated concurrent drift is classified separately. Static verification checks wrapper syntax, model policy, Git LFS, status parsing, scope enforcement, credential scrubbing, and drift attribution without making a Cursor request. A live probe is explicit and never scheduled by the combined monitor.
