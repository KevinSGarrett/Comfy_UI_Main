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

Concrete progress means one of:
- selected inpaint/runtime lane implementation or workflow wiring;
- deploy-bundle rebuild/revalidation planning or proof;
- S3 publish readiness or dry-run proof for selected runtime assets;
- input/model install proof;
- local ComfyUI object_info or runtime readiness proof;
- generated artifact QA when live gates allow it;
- narrow validator/helper work that directly unblocks runtime/QA/cost safety.

Hydration, proof-log, tracker, manifest, index, Git, or audit updates do not count as progress unless they follow a concrete ComfyUI runtime/orchestration/QA artifact.

## Worker Lane Policy

Use three explicit lanes:

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

Claude Desktop/subscription is available through:

```text
C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1
```

Use the Claude subscription lane only when `Test-ClaudeSubscriptionHandoff.ps1` passes or the latest successful probe is fresh. It must use `claude.ai` subscription auth and must not fall back to Anthropic API keys or Console PAYG billing.

## Role Ownership

- The two-hour anti-loop supervisor is the primary progress and repo-cleanliness watchdog.
- The fleet-health supervisor verifies that the automation fleet itself is healthy and that the two-hour supervisor finalizes audits.
- The EC2 cost sentinel owns EC2/cost safety only.
- The daily artifact QA audit owns artifact/evidence integrity only.
- The daily cost/local-first audit owns local-first and EC2-on-time posture only.
- The six-hour milestone auditor owns sequence and milestone drift only.
- The weekly consistency audit owns Plan/Instructions/Items/Tracker consistency only.

Specialist jobs may report drift, but they should not all steer the main session. Use the shared correction lock before any steering message or project file edit.

## Repo Cleanliness

Cron jobs may inspect repository state but must not mutate it. They must not run git add, commit, push, reset, checkout, restore, clean, or destructive cleanup.

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
