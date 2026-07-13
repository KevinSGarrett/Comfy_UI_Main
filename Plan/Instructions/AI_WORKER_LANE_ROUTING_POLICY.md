# AI Worker Lane Routing Policy

Updated: 2026-07-13

This policy defines how Codex Desktop, Cursor CLI, and Claude Code subscription work together for Comfy_UI_Main.

## Objective

Reduce Codex Desktop usage by moving bounded worker tasks to Cursor, high-effort synthesis tasks to Claude Code subscription, and read-only Git/GitHub investigation to worker-analysis lanes while keeping Codex as final project authority.

Target outcome: reduce active Codex Desktop usage by at least 50% for this 24/7 autonomous ComfyUI build. Cursor and Claude are not extra project managers; they are worker lanes that absorb work Codex Desktop would otherwise spend long turns doing.

Current usage baseline:

```text
C:\Comfy_UI_Main\runtime_artifacts\agent_handoffs\ai_worker_rollout\CODEX_DESKTOP_USAGE_BOOKMARK_20260709T150020-0500.json
```

The bookmarked Codex Desktop weekly usage is `78%` with a weekly reset on `2026-07-15`. Worker delegation should be evaluated against the explicit target of reducing Codex Desktop usage by at least 50%.

Use these deterministic tools for comparable measurements:

```text
C:\Comfy_UI_Main\tools\New-CodexDesktopUsageSnapshot.ps1
C:\Comfy_UI_Main\tools\Measure-AIWorkerCodexUsageReduction.ps1
C:\Comfy_UI_Main\tools\Measure-AIWorkerNetUsageReductionProxy.ps1
C:\Comfy_UI_Main\tools\Measure-CodexAutomationScheduleLoad.ps1
```

The monitor must prefer measured weekly quota burn-rate reduction over an unaudited estimate whenever finalized post-baseline snapshots exist. A snapshot must record the displayed percentage and whether it means `UsedPercent` or `RemainingPercent`; never infer the UI semantics. One post-baseline snapshot is capped at `MEDIUM`. `HIGH_TWO_MEASURED_PERIODS` requires two post-baseline measurements that both meet the 50% target, span at least 24 hours from baseline, and are at least 6 hours apart.

Proxy estimates must use the net tool and include final-authority work, Codex review/validation, failed-handoff recovery, worker orchestration, direct eligible work absorbed by Codex, and incremental scheduled-Codex overhead. Worker-eligible avoided minutes alone are not an estimate of total Codex Desktop reduction. Every proxy result is capped at `MEDIUM`.

Use `Measure-CodexAutomationScheduleLoad.ps1` for scheduled invocation frequency. Never convert scheduled run counts into token or quota cost without external usage telemetry.

## Shared Project Boundaries

All worker routing must also respect:

```text
C:\Comfy_UI_Main\Plan\Instructions\AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\GIT_GITHUB_WORKER_ANALYSIS_LANE_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md
C:\Comfy_UI_Main\Plan\Instructions\JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md
```

## Main-Session Root Preflight

The authoritative workspace is `C:\Comfy_UI_Main`. At the beginning of a resumed or compacted main-session turn, resolve this path and use it as the explicit working directory for project commands and every worker `-ProjectRoot`. If thread metadata still reports legacy `C:\Comfy_UI`, treat that as a host-context mismatch, not project authority. Do not copy, synchronize, or recreate completed work merely to reconcile the displayed thread directory.

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

Before a broad worker scan, create a bounded scope packet when authoritative files are already known:

```text
C:\Comfy_UI_Main\tools\New-AIWorkerScopePacket.ps1
```

The normal path is deterministic shortlist first, then narrow worker review. Pass the packet to the Cursor wrapper with `-ScopePacketPath`. The wrapper validates repository containment, the 1-12 file limit, and current SHA-256 hashes before launching Cursor. A worker-side whole-tree task-selection scan is allowed only with `-AllowBroadDiscovery -BroadDiscoveryReason <reason>` when current hydration, work-order, queue, or manifest authority cannot produce a bounded candidate list.

Cursor's normal timeout ceiling is 600 seconds. A timeout above 600 seconds is allowed only with the explicit broad-discovery exception and may never exceed 900 seconds. A broad reconciliation or inventory must not use a 900-second first attempt without that exception.

## Lane 1: Codex Desktop Final Authority

Codex owns:

- final project decisions and user-facing summaries;
- visual QA and final image/video judgment;
- Git checkpoint, add, commit, push, reset, checkout, restore, clean, merge, rebase, and branch decisions;
- GitHub PR, issue, label, release, workflow, and project mutation decisions;
- AWS, EC2, S3, live runtime, and ComfyUI generation decisions;
- mask promotion, Wave70 hard gates, Wave71+ activation, and Jira mutation;
- Items/Tracker status mutation.

## Canonical Enforcement Package

The versioned authority for worker wrappers, verifier scripts, policy mirrors, and automation templates is `tools/ai_worker_handoffs`. `worker_handoff_package_manifest.json` binds every deployable file by byte length and SHA-256. Use `Install-AIWorkerHandoffPackage.ps1` only after canonical validation and only when neither worker lock exists. Use `Test-AIWorkerHandoffPackageDrift.ps1` to detect live-versus-canonical drift; direct edits to live wrapper or automation files are temporary defects that must be reconciled back to the package.

Cursor is read-only: ask/plan only, plain `gpt-5.3-codex`, no fast variant, no agent mode, no writes, and no `--force`. Scope packets must declare `Cursor` or `GitGitHub`, use the matching routing gate, and remain within the wrapper's aggregate byte budget. `status: blocked` is `CURSOR_HANDOFF_WORKER_REPORTED_BLOCKED`, not useful completion. A changed hash-bound scope is a mutation violation; unrelated worktree change with unchanged scope is `CURSOR_CONCURRENT_WORKTREE_DRIFT_DETECTED` and receives no useful credit without misattributing the edit.

Claude receives only `Read,Glob,Grep` through `--tools` under `--safe-mode`, `--strict-mcp-config`, disabled slash-command skills, and `--no-chrome`. The child environment excludes AWS, GitHub, cloud, and API credentials while preserving first-party subscription OAuth. The Opus ceiling is an immutable global maximum of two completed calls per local day. Except for the explicit direct high-risk architecture exception, Opus requires a same-decision Sonnet record with exact normalized status, exact `low|medium|high` confidence, mutation-free bounded scope, and evidence satisfying the named escalation trigger.

Default worker verification is static and must not launch Cursor, Sonnet, or Opus. Live transport probes require an explicit verifier switch and are never launched by the recurring combined monitor. Probe calls consume normal subscription capacity and, for Opus, the same immutable daily ceiling.

Codex should not spend long active turns doing broad mechanical scans when Cursor or Claude can produce compact evidence.

## Lane 2: Cursor First Worker

Cursor is the default first worker for:

- broad local inventories;
- evidence extraction from many files;
- parser and validator triage;
- helper or script first drafts in narrow scopes;
- bookmark-resume diagnosis;
- repetitive file/path/hash summaries.

Cursor delegated work uses plain `gpt-5.3-codex`. Fast Cursor variants are prohibited. Cursor owns mechanical extraction and first-pass gap identification, not repeated semantic final review.

Use:

```text
C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1
```

Default read-only mode is `ask`. Use `plan` only after `ask` is insufficient. Incomplete promise-style output is not evidence.

## Lane 3: Claude Code Subscription

Claude subscription has two exact, non-interchangeable model tiers. `claude-sonnet-5` is the primary semantic worker for:

- difficult strategy synthesis;
- contradiction review across plans and policies;
- architecture or routing critique;
- first substantive semantic diagnosis, plan, or contradiction synthesis;
- bounded implementation and safety review after deterministic validation;
- heavy reasoning tasks that would otherwise consume a long Codex Desktop turn.
- semantic final review after a mechanical Cursor extraction when the decision crosses policies, evidence authority, certification wording, or more than eight files.

`claude-opus-4-8` is an escalation lane only when Sonnet is blocked or low-confidence after one bounded pass, a high-severity issue survives one remediation cycle, the decision spans at least three subsystems or two authority domains, material local/GitHub/AWS/runtime/policy evidence conflicts, or the architecture decision would otherwise consume more than about 15 minutes of Codex reasoning.

Use at most one Opus handoff per decision unit and at most two completed Opus handoffs per local day during the pilot. This is one global ceiling across project roots, including capability probes, backed by the external Claude wrapper's daily usage ledger. Opus has no minimum-use target and must not become a routine second or third reviewer.

Use:

```text
C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1
```

The wrapper must verify:

- `loggedIn: true`
- `authMethod: claude.ai`
- `apiProvider: firstParty`
- no `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or `ANTHROPIC_BASE_URL` environment fallback
- inherited AWS, GitHub, cloud-provider, and credential-helper variables removed from the Claude child process
- repository-visible and scope-file fingerprints unchanged after every handoff

Do not use model aliases. Health probes use exact `claude-sonnet-5` with low effort. Sonnet primary work uses medium by default, high for broad or safety-sensitive review, and xhigh only when justified. Opus uses high or xhigh. Max requires explicit approval and is never a routine automation setting.

Anthropic's planned separate Agent SDK credit treatment is currently paused. Noninteractive `claude -p` usage still draws from normal subscription limits. The CLI reports Team but not Standard versus Premium seat type, so the lane must fail closed on capacity errors and never switch to API or paid fallback automatically.

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

### Git LFS capability gate

Git LFS analysis is not ordinary Git analysis. Any work order that mentions Git LFS, LFS-managed files, LFS tracking, or `.gitattributes` must use the Cursor wrapper's `-RequireGitLfs` contract. The wrapper probes `git lfs version` inside the pinned `Ubuntu-22.04` Cursor environment before the worker starts and records:

- `git_lfs_capability_status`
- `git_lfs_analysis_route`
- `git_lfs_wsl_version`
- `git_lfs_capability_classification` when degraded

The native route is `CURSOR_WSL_NATIVE_GIT_LFS`. Missing native capability without validated fallback evidence is `CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS`, not generic wrapper friction and not a successful partial handoff.

When native Git LFS is unavailable, Codex may run `C:\Comfy_UI_Main\tools\Export-GitLfsReadOnlyEvidence.ps1` once and pass its hash-recorded output with `-GitLfsEvidencePath`. This is `WINDOWS_READ_ONLY_GIT_LFS_EVIDENCE_BRIDGE`. It is a bounded contingency, not the expected normal route. Claude may synthesize the supplied evidence but must not replace Cursor's mechanical LFS extraction.

Git LFS environment installation and all repository-changing LFS operations remain Codex-only. Workers must not run `git lfs install`, `track`, `untrack`, `migrate`, `pull`, `fetch`, `checkout`, or any command that changes attributes, pointers, the index, or working files.

## Routing Order

1. If the task involves final authority, live runtime, masks, Git/GitHub mutation, Jira, S3, EC2, or visual QA, keep final execution in Codex.
2. If the task is Git/GitHub read-only analysis above threshold, use `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
3. If the task is mechanical local reading, inventory, triage, or drafting, send it to Cursor first.
4. If semantic reasoning is the hard part, use `CLAUDE_SONNET_PRIMARY_REQUIRED` before Codex performs the same analysis.
5. Use `CLAUDE_OPUS_ESCALATION_REQUIRED` only after its auditable escalation contract passes.
6. Codex reviews compact worker evidence and decides the final action.

Do not run Cursor gap review, Cursor final review, and Claude final review for the same deterministic unit. Use one of:

- deterministic local validation only when the authority and expected result are already exact;
- Cursor gap extraction followed by Codex bounded correction for mechanical defects;
- Cursor extraction followed by one Sonnet semantic review for difficult cross-artifact decisions.

Use one Sonnet confirmation after remediation at most. If a material problem remains and the Opus trigger passes, use one Opus adjudication instead of a third Sonnet review. Do not run independent Cursor, Sonnet, and Opus reviews of the same clean deterministic unit.

Over a rolling 24-hour window, Claude should handle 60-70% of eligible non-authority semantic/synthesis work. In a four-hour window containing at least two eligible semantic tasks, at least one should use Sonnet. Mechanical tasks do not count toward this denominator. Opus has no minimum-use target.

## Mandatory Pre-Work Delegation Gate

Before Codex starts any broad scan, audit, helper draft, multi-file diagnosis, evidence extraction, strategy review, or Git/GitHub investigation above a tiny check, it must classify the work with exactly one gate:

- `CODEX_ONLY_AUTHORITY`
- `CURSOR_FIRST_REQUIRED`
- `CLAUDE_SONNET_PRIMARY_REQUIRED`
- `CLAUDE_OPUS_ESCALATION_REQUIRED`
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
- `DETERMINISTIC_FAST_PATH`

If Codex selects `CODEX_ONLY_AUTHORITY`, it must record the authority reason, such as visual QA, Git/GitHub mutation, EC2, S3, Jira, masks, Wave70/Wave71 gates, Items/Tracker status mutation, or final acceptance.

If Codex selects `DETERMINISTIC_FAST_PATH`, it must keep the work under the thresholds below. If the work grows past threshold, Codex must stop and create a worker handoff. `CLAUDE_HEAVY_REVIEW_REQUIRED` and `NO_WORKER_NEEDED_UNDER_THRESHOLD` remain deprecated compatibility labels only.

## Budget Thresholds

Use these thresholds as hard routing triggers:

- More than 10 files to inspect: `CURSOR_FIRST_REQUIRED`.
- More than one major tree to inspect: `CURSOR_FIRST_REQUIRED`.
- More than one broad `rg` or inventory pass: `CURSOR_FIRST_REQUIRED`.
- More than one validator or parser triage pass: `CURSOR_FIRST_REQUIRED`.
- More than 3 minutes of active Codex reasoning expected: use Cursor or Claude.
- Helper/script first draft in a narrow local scope: Cursor first unless final authority blocks delegation.
- Strategy/contradiction review, broad synthesis, or architecture/routing critique: `CLAUDE_SONNET_PRIMARY_REQUIRED` unless it includes final authority.
- Opus may be selected only when a recorded escalation trigger, exact decision unit, hash-bound scope, daily ceiling, and prior successful Sonnet record or direct high-risk architecture exception all pass.
- More than 5 unclassified changed files, more than one ownership group, or any uncertain checkpoint boundary: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- More than one Git/GitHub failure source: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- CI/log review beyond a tiny bounded read: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- Unclear checkpoint boundary, PR review inventory, branch/upstream divergence analysis, or GitHub Actions diagnosis likely to take more than 3 minutes: `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`.
- Failed or incomplete worker output: retry once with a narrower work order before Codex absorbs the task.

Codex may bypass these triggers only when the task is explicitly in final authority scope, and the bypass reason must be recorded.

## Deterministic Scope And Known-Git Fast Paths

For worker selection, use `New-AIWorkerScopePacket.ps1` with no more than 12 explicit candidate files and a default aggregate budget of 524,288 bytes. `SonnetPrimary` requires a hash-bound packet unless an explicit broad-discovery exception is recorded. Opus always requires a packet and a successful prior Sonnet record for the same decision unit unless the direct high-risk architecture exception is explicitly approved. Prefer current hydration top blocks, the active work order, queue rows, and existing manifest links as shortlist sources. Do not send the full large hydration ledgers or ask a worker to rediscover the repository when those authorities identify the candidate surface.

For Git, a checkpoint may stay on the deterministic fast path even when more than five files changed only when all conditions hold:

- every changed path was produced by the current implementation unit;
- the include list was declared before mutation;
- no unrelated or user-owned dirty path is present;
- branch/upstream state is already known;
- existing local scripts perform status, diff-check, blocked-path, and secret checks;
- Codex records `KNOWN_SCOPE_GIT_FAST_PATH` and keeps mutation authority.

If any condition is false, use `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`. File count alone must not create worker ceremony for an already deterministic checkpoint, but file count plus uncertainty requires delegation.

While a worker runs, do not issue repeated progress narration or poll partial output. Start one bounded handoff, wait for its finalized record, and emit at most one timeout/retry update unless the user asks for status.

For deterministic known-scope work, batch three to five completed units into one guarded Git checkpoint when their ownership boundaries and validation contracts are compatible. Use a single-unit checkpoint only for a safety boundary, independently reversible feature, user-requested checkpoint, or unrelated dirty-worktree constraint.

## Fallback Rules

If Cursor is unavailable or returns incomplete output, Codex should narrow and retry once before doing the work directly.

If Claude subscription auth is missing, expired, non-`claude.ai`, or API-key fallback risk is present, Codex must route the work to Cursor or record `CLAUDE_SUBSCRIPTION_UNAVAILABLE`.

If Git/GitHub worker analysis is incomplete, Codex should narrow the work order to one of: dirty-worktree grouping, CI failure extraction, PR comment inventory, checkpoint-boundary synthesis, or branch/upstream state summary. Codex may absorb the work only after one narrow retry or when the Git/GitHub decision is urgent final authority.

`CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS` does not use the generic retry loop. Repair Git LFS in the pinned Cursor WSL environment once. If immediate repair is unavailable, export one bounded Windows read-only evidence packet and retry Cursor with that packet. Only if both routes fail may Codex perform a compact read-only fallback; record the capability probe, evidence-export result, and why Cursor could not consume the evidence.

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

Claude adoption floor: if the latest monitor window shows zero useful Claude handoffs while subscription auth is healthy, the next eligible synthesis, contradiction review, routing critique, checkpoint-risk synthesis, or strategy review expected to take more than 2 minutes must use `CLAUDE_SONNET_PRIMARY_REQUIRED` before Codex absorbs it. Do not route mechanical extraction or final authority to Claude.

Cursor friction retry discipline: if Cursor fails because of wrapper invocation, parser, environment, or lock friction, retry once with the smallest safe work order: ask mode, a validated scope packet or supplied file/status list, no worker-side broad Git discovery, no file edits, and no mutation authority. The wrapper applies process-local PowerShell execution-policy bypass internally. If the retry fails, classify `CURSOR_WRAPPER_FRICTION_COMPACT_FALLBACK`, record the failure evidence, and fall back compactly instead of live-tailing or absorbing a long task silently.

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
- `git_github_worker_analysis_tasks_detected`
- `git_github_analysis_handoffs_attempted`
- `git_github_direct_codex_analysis_violations`
- `git_github_worker_mutation_attempts_detected`
- `git_github_connector_first_compliance`
- estimated Codex work avoided;
- usage reduction confidence.
- Codex final-authority minutes.
- Codex review and validation minutes.
- Codex failed-handoff recovery minutes.
- Codex worker-orchestration minutes.
- direct Codex worker-eligible minutes.
- incremental scheduled Codex minutes.
- scope-packet compliance percentage.
- malformed-path or write-scope violations.
- stale or interrupted worker records.
- Cursor read-only mutation violations.
- Claude substantive semantic-review share.
- duplicate gap/final/reviewer cycles avoided.
- deterministic checkpoint batch size.
- Git LFS tasks detected.
- native Cursor Git LFS capability passes and gaps.
- Windows Git LFS evidence bridges used.
- direct Codex Git LFS analysis fallbacks.
- Sonnet primary handoffs.
- Opus escalation handoffs and explicit trigger classifications.
- justified, rejected, duplicate-suppressed, and daily-ceiling Opus attempts.
- Claude subscription-capacity failures.
- Claude worker-reported blocked and invalid-status results.
- Claude read-only mutation violations.
- Claude concurrent worktree drift classifications, counted separately from mutation violations and excluded from useful credit.
- adopted worker outputs.
- duplicate semantic/review cycles.

The monitor may recommend high confidence only after the measured tool returns `HIGH_TWO_MEASURED_PERIODS`, at least 25 substantive handoffs have an 85% or better useful success rate, scope-packet compliance is at least 95%, adopted-output rate is at least 80%, duplicate-review rate is below 10%, and fast-Cursor, API-fallback, worker-mutation, live-authority, and direct-routing violations are all zero for the qualification window.

Usage reduction confidence should be reported as:

- `LOW`: net proxy is below 50%, operational thresholds fail, or direct-Codex violations repeat.
- `MEDIUM`: net proxy meets 50% or one direct measurement meets 50%, but the two-measurement qualification gate is incomplete.
- `HIGH_TWO_MEASURED_PERIODS`: two qualifying post-baseline measurements meet 50% and all operational thresholds above pass.

Estimated audit windows can demonstrate adoption but can never produce `HIGH` or `PROVEN`. When finalized snapshots exist, use `Measure-AIWorkerCodexUsageReduction.ps1`; do not replace a direct result with a more favorable proxy.

## Output Contract

Worker handoffs must return:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `confidence:`
- `recommended Codex follow-up:`

Opus escalation handoffs must also return `escalation outcome:`.

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
