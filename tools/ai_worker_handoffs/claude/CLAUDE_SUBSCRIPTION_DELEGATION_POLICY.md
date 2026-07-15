# Comfy_UI_Main Claude Subscription Delegation Policy

Status: active external policy
Date: 2026-07-13
Owner: Codex Desktop orchestrator plus Claude Code subscription worker

## Objective

Use the authenticated Claude Desktop / Claude Code subscription as the primary non-authority semantic worker lane while reducing Codex Desktop active usage. Sonnet 5 owns most eligible synthesis and review. Opus 4.8 is a bounded escalation lane for unresolved or genuinely cross-cutting decisions.

This lane is subscription-backed. It must not use Anthropic API keys, Console PAYG, or an automatic paid fallback. The wrapper has no API-fallback switch and must stop when subscription capacity is unavailable.

Claude subscription is a usage-reduction synthesis lane, not a project manager. Its job is to absorb high-effort review and reasoning so Codex Desktop can stay focused on final decisions and selected-inpaint ComfyUI runtime/orchestration progress. The target is to help reduce active Codex Desktop usage by at least 50% for worker-suitable synthesis/review tasks.

## Shared ComfyUI Boundaries

Claude subscription work and Claude-health monitoring must respect the project policies:

```text
C:\Comfy_UI_Main\Plan\Instructions\AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md
C:\Comfy_UI_Main\Plan\Instructions\LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md
C:\Comfy_UI_Main\Plan\Instructions\JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md
```

Local `C:\Comfy_UI_Main` is authoritative. EC2 `/home/ubuntu/Comfy_UI_Main` is runtime/cache state only and must not be used to reopen completed fallback/base/Canny/local-smoke work.

Claude delegation is useful only when it reduces Codex active reasoning and returns compact evidence for difficult synthesis. Claude handoffs, health checks, hydration updates, proof-log updates, tracker/index/manifest updates, Git dry-runs, and audit files do not count as project progress unless they directly support a concrete ComfyUI runtime/orchestration/QA artifact.

Claude-health monitors should not interrupt the main session for ordinary audit results. They may steer only when Claude subscription auth is broken, API fallback risk appears, repeated incomplete handoffs occur, or Codex is repeatedly doing high-effort synthesis that should have been delegated.

## Authentication

Use the installed Claude Code binary:

`C:\Users\kevin\AppData\Roaming\Claude\claude-code\2.1.205\claude.exe`

The expected auth status is:

- `loggedIn: true`
- `authMethod: claude.ai`
- `apiProvider: firstParty`

Do not run this lane when `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or `ANTHROPIC_BASE_URL` is set in the process, user, or machine environment. Anthropic documents that API-key environment variables can route usage away from the subscription.

As of 2026-07-13, Anthropic's planned separate Agent SDK credit treatment is paused. Noninteractive `claude -p` currently draws from normal subscription usage. Do not assume a separate monthly worker-credit pool. The authenticated CLI reports Team but does not reveal Standard versus Premium seat type, so capacity planning must remain conservative and fail closed on a limit response.

The child process must remove AWS, GitHub, cloud-provider, Git credential-helper, OpenAI, Cursor, and Civitai credential/profile variables before launch. Redaction alone is not a permission boundary.

## Role Split

Codex Desktop keeps final authority for:

- project management and final acceptance;
- visual QA and final image/video judgment;
- Git staging, commits, pushes, resets, checkouts, and branch decisions;
- GitHub PR, issue, label, workflow, release, and project mutation decisions;
- AWS, EC2, S3, and live runtime actions;
- mask promotion, Wave70 hard gates, Wave71+ activation, and Jira mutation;
- Items/Tracker status mutation.

Cursor remains the first worker for:

- broad mechanical inventories;
- local file extraction;
- parser and validator triage;
- helper/script first drafts.

Claude Sonnet 5 is the primary semantic lane for:

- high-effort synthesis after Cursor extraction;
- difficult strategy review;
- contradiction analysis across policies and plans;
- first substantive semantic diagnosis or plan when reasoning is the hard part;
- bounded implementation and safety critique after deterministic validation;
- architecture or routing recommendations where Sonnet reasoning quality is useful.
- Git/GitHub checkpoint, branch, PR, CI, or push-risk synthesis after read-only extraction.

Claude Opus 4.8 is an escalation lane only when at least one auditable trigger applies:

- Sonnet returns blocked or low confidence after one bounded attempt;
- a high-severity issue remains unresolved after one remediation cycle;
- the decision spans at least three subsystems or two authority domains;
- local, GitHub, AWS, runtime, and project-policy evidence materially conflict;
- the architecture decision would otherwise consume more than about 15 minutes of Codex reasoning.

Opus is not a routine final reviewer. Use at most one Opus handoff per decision unit and at most two completed Opus handoffs per local day during the pilot. The ceiling is global across project roots and includes capability probes; completed calls are recorded under the external `opus_usage\YYYY-MM-DD` ledger. Prefer a successful pinned Sonnet record before Opus. A direct Opus call requires the explicit high-risk architecture exception, an exact reason, and a hash-bound scope packet.

For Git LFS, Claude consumes compact evidence extracted by native Cursor Git LFS or the validated Windows read-only evidence bridge. Claude must not perform mechanical LFS discovery, environment installation, tracking/migration, pointer repair, pull/fetch/checkout, staging, or any other Git/LFS mutation.

## Mandatory Pre-Work Delegation Gate

Before Codex performs high-effort synthesis, contradiction review, strategy review, or architecture/routing critique, it must classify the task with one of:

- `CODEX_ONLY_AUTHORITY`
- `CURSOR_FIRST_REQUIRED`
- `CLAUDE_SONNET_PRIMARY_REQUIRED`
- `CLAUDE_OPUS_ESCALATION_REQUIRED`
- `GIT_GITHUB_WORKER_ANALYSIS_REQUIRED`
- `DETERMINISTIC_FAST_PATH`

Use `CLAUDE_SONNET_PRIMARY_REQUIRED` when a task is expected to take more than 3 minutes of active Codex semantic reasoning or requires strategy synthesis. Use `CLAUDE_OPUS_ESCALATION_REQUIRED` only when the Opus trigger contract above passes. `CLAUDE_HEAVY_REVIEW_REQUIRED` is a deprecated compatibility label and should not be emitted by new work.

Hard thresholds:

- More than 10 files: Cursor first for extraction, then Claude for synthesis when needed.
- More than one major tree: Cursor first for extraction, then Claude for synthesis when needed.
- More than one broad inventory or `rg` pass: Cursor first.
- More than one validator/parser triage pass: Cursor first.
- More than 3 minutes active Codex reasoning: Claude subscription or Cursor, depending on whether the work is synthesis or mechanical extraction.
- Strategy/contradiction review: Claude Sonnet unless final authority applies.
- Git/GitHub checkpoint-boundary, branch, PR, CI, push-risk, or policy contradiction review after read-only extraction: Claude subscription when synthesis is the hard part.
- Git/GitHub analysis with more than 5 unclassified changed files, more than one ownership group or failure source, long CI logs, unclear checkpoint boundaries, branch/upstream ambiguity, or PR/review triage over 3 minutes should use the Git/GitHub worker-analysis lane before Codex absorbs the work.
- Machine-check threshold token: `More than 5 unclassified changed files`.

For GitHub PR, issue, comment, label, reaction, review, release, and metadata synthesis, prefer evidence from the connected GitHub app/connector when available. Use local `gh` evidence mainly for current-branch PR discovery, GitHub Actions logs, and local checkout correlation.

If Claude output is incomplete, retry once with a narrower work order or route the mechanical extraction portion to Cursor before Codex absorbs the task. Do not answer an incomplete Sonnet result by automatically calling Opus.

Use `C:\Comfy_UI_Main\tools\New-AIWorkerScopePacket.ps1` to provide no more than 12 exact candidate files whenever project authority already bounds the review. The default aggregate packet budget is 524,288 bytes. Larger packets require an explicit size-budget reason; prefer a compact evidence packet over sending the nearly 1 MB hydration ledgers wholesale.

Pass the generated packet to the wrapper with `-ScopePacketPath`. The wrapper verifies repository containment, the Claude worker lane, candidate count, file existence, and current SHA-256 hashes before launching Claude. `SonnetPrimary` requires this packet unless an explicit `-AllowBroadDiscovery -BroadDiscoveryReason <reason>` exception is recorded. Health probes do not require project scope; Opus never permits broad discovery.

Do not narrate repeated wait updates while Claude runs. Start one bounded handoff, wait for its finalized record, and issue at most one timeout/retry update unless the user asks for status.

For Git/GitHub work, `KNOWN_SCOPE_GIT_FAST_PATH` may bypass worker analysis only when the current implementation has an exact include list, no unrelated dirty paths, known branch/upstream state, and deterministic local safety checks. Claude remains the heavy synthesis lane for any uncertain checkpoint, branch, CI, PR, or push-risk decision.

Claude adoption floor: if the latest combined worker monitor shows zero useful Claude handoffs while subscription auth is healthy, the next eligible synthesis, contradiction review, routing critique, checkpoint-risk synthesis, or strategy review expected to take more than 2 minutes must use `CLAUDE_SONNET_PRIMARY_REQUIRED` before Codex absorbs it. This floor does not apply to mechanical extraction or final authority.

Adoption target: Claude should handle 60-70% of eligible non-authority semantic/synthesis work over a rolling 24-hour window. In a four-hour window with at least two eligible semantic tasks, at least one should use Sonnet. This is a useful-work target, not permission to manufacture reviews. Opus has no minimum-use target.

Review budget: use Cursor extraction when needed, one Sonnet semantic pass, Codex remediation/final authority, and at most one Sonnet confirmation. If a material issue remains unresolved after that cycle and the Opus contract passes, use one Opus adjudication. Do not run a third Sonnet confirmation or independent Cursor, Sonnet, and Opus reviews of the same clean deterministic unit.

Monitor Scoring fields:

- `worker_eligible_tasks_detected`
- `worker_handoffs_attempted`
- `successful_compact_handoffs`
- `incomplete_or_failed_handoffs`
- `codex_fallback_cases`
- `direct_codex_worker_lane_violations`
- `claude_required_but_missing_count`
- `git_github_worker_analysis_tasks_detected`
- `git_github_analysis_handoffs_attempted`
- `git_github_direct_codex_analysis_violations`
- `git_github_worker_mutation_attempts_detected`
- `git_github_connector_first_compliance`
- `estimated_codex_work_avoided_minutes`
- `estimated_usage_reduction_percent`
- `usage_reduction_confidence`
- `claude_sonnet_primary_handoffs`
- `claude_opus_escalation_handoffs`
- `claude_opus_escalations_justified`
- `claude_opus_daily_ceiling_rejections`
- `claude_subscription_capacity_unavailable`
- `duplicate_review_cycles_detected`
- `adopted_worker_outputs`

## Model And Effort

Primary semantic model: exact `claude-sonnet-5`

Escalation model: exact `claude-opus-4-8`

Default substantive effort: `medium`

Do not use `sonnet`, `opus`, `fable`, or other drifting aliases. Health probes use exact `claude-sonnet-5` with low effort. Sonnet primary work uses medium, high, or xhigh. Opus escalation uses high or xhigh. Max requires explicit approval and is never a routine automation setting.

Wrapper task tiers:

- `HealthProbe`: pinned Sonnet 5, low effort, no project analysis;
- `SonnetPrimary`: pinned Sonnet 5, medium/high/xhigh;
- `OpusEscalation`: pinned Opus 4.8, high/xhigh, exact decision unit and escalation reason, hash-bound scope, a successful prior Sonnet record for that same decision unit unless the direct exception is explicitly approved.

The wrapper must run substantive work in a registered isolated worktree and capture repository-visible state and hash-bound scope files before and after every live handoff. A changed hash-bound scope file is `CLAUDE_SUBSCRIPTION_READ_ONLY_MUTATION_VIOLATION`. A change outside the bounded scope with unchanged scoped hashes is `CLAUDE_CONCURRENT_WORKTREE_DRIFT_WARNING`; it is recorded but does not invalidate otherwise complete evidence. Lane locks queue for a bounded interval before returning `CLAUDE_SUBSCRIPTION_LOCK_WAIT_TIMEOUT`.

## Output Contract

Every handoff must return compact labeled output containing:

- `status:`
- `summary:`
- `files inspected:`
- `blockers:`
- `confidence:`
- `recommended Codex follow-up:`

Opus handoffs must also include `escalation outcome:`.

Git/GitHub synthesis handoffs must also include `git_github_scope:`, `risks:`, `recommended_codex_commands:`, and `mutation_boundary: Codex-only`.

Promise-style output such as "I will inspect next" is not a completed handoff. Codex should retry with a narrower work order or route the task to Cursor.

A zero process exit is not sufficient for useful credit. The wrapper must parse and normalize the labeled worker status. `confirmed` normalizes to pass, `pass_with_findings` completes with findings, and `verified_blocked_as_intended` completes as an explicit blocked diagnosis. A genuine failure remains failed, and an unrecognized status is `CLAUDE_SUBSCRIPTION_INVALID_STATUS_LABEL`. Blocked diagnosis never implies implementation or certification success.

The wrapper may store only a compact result excerpt in `handoff_record.json`, but output-contract validation must use the full captured Claude stdout. A handoff should not be marked incomplete merely because required labels appear after the compact excerpt cutoff.

Claude-health scheduled audits must write parseable final JSON. If an `IN_PROGRESS` stub exists, a newer final audit must supersede it; otherwise report the stale stub as a monitor defect and do not treat cleanup of that stub as project progress.

## Hard Bans

Claude subscription jobs must not:

- print or inspect secret values;
- use Anthropic API keys or Console PAYG fallback;
- receive inherited AWS, GitHub, cloud-provider, or credential-helper environment access;
- run Git staging, add, commit, push, reset, checkout, restore, clean, merge, rebase, or branch mutation;
- create, update, merge, close, or reopen GitHub PRs;
- mutate GitHub issues, labels, milestones, releases, workflows, projects, comments, reactions, or reviews;
- start or stop EC2, upload to S3, launch ComfyUI generation, or run live runtime commands;
- promote masks, run Wave70 hard gates, activate Wave71+, or mutate Jira;
- edit files unless a future explicit write wrapper is created.
- invoke subagents or unrestricted shell tooling from the read-only wrapper.

## Success Metric

This lane counts as successful only when it reduces Codex Desktop reasoning time by producing compact, reviewable evidence for hard synthesis work while Codex retains final authority.

The combined worker monitor should score Claude against:

- Claude-eligible heavy-review tasks detected;
- Claude handoffs attempted;
- successful compact Claude handoffs;
- incomplete or failed handoffs;
- direct Codex fallback cases;
- estimated Codex reasoning avoided.
- Sonnet primary and Opus escalation counts separately;
- justified versus rejected Opus escalations;
- adopted worker output and duplicate-review rates;
- subscription-capacity and read-only-mutation failures.

Total Codex Desktop reduction must use `C:\Comfy_UI_Main\tools\Measure-AIWorkerNetUsageReductionProxy.ps1` for proxy accounting and `C:\Comfy_UI_Main\tools\Measure-AIWorkerCodexUsageReduction.ps1` for direct quota measurements. Proxy accounting includes final-authority, review/validation, failed-handoff recovery, orchestration, direct eligible Codex work, and incremental scheduled-automation minutes and is capped at `MEDIUM` confidence.

A high-confidence 50% reduction recommendation requires two qualifying post-baseline measurements meeting at least 50% reduction, separated by at least six hours and spanning at least 24 hours from baseline; at least 25 substantive handoffs with 85% or better useful success; at least 95% bounded-scope compliance; at least 80% adopted-output rate; duplicate reviews below 10%; and zero fast-Cursor, API-fallback, worker-mutation, or live-authority violations in the qualification window.

## Enforced Runtime Contract

The canonical wrapper is versioned in `tools/ai_worker_handoffs/claude` and installed by hash. It preserves first-party `claude.ai` subscription OAuth while exposing only `Read,Glob,Grep` under safe mode, strict MCP isolation, disabled slash-command skills, and disabled Chrome. AWS, GitHub, cloud-profile, API-key, and credential-helper environment variables are removed from the child process.

The Opus global ceiling is a non-overridable maximum of two completed calls per local day. Except for the explicit direct high-risk architecture exception, exact `claude-opus-4-8` requires a recent same-decision exact `claude-sonnet-5` record with validated scope, no mutation or concurrent drift, normalized status, exact `low|medium|high` confidence, and evidence satisfying the named trigger. Invalid markers do not count as valid usage evidence, but they are a monitor defect. Default verification is static; live Sonnet or Opus probes require explicit switches and are not cron work.
