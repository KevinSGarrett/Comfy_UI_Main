<!--
Wave 58 — Autonomous Instruction Manual + AI Project Manager Brain
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions
This file is designed for Codex Desktop autonomous operation.
-->

# NO_LOOP_NO_DRIFT_PROGRESS_CONTROL

## 1. Purpose

This protocol prevents Codex Desktop from looping, repeating the same action, spinning in circles, drifting into unrelated work, or creating files without advancing the project.

Codex must measure progress by verified movement through the tracker and evidence chain, not by time spent or text produced.

## 2. Definitions

### Looping

Repeating the same or nearly identical action without new evidence or a changed strategy.

Examples:
- editing the same file repeatedly without resolving validation errors
- rerunning the same failing command without changing inputs
- re-reading the same documents without selecting a task
- recreating the same plan instead of implementing
- regenerating a pack without fixing the prior validation failure

### Drifting

Working outside the selected wave, task, or dependency chain without recording why.

Examples:
- changing model registry rules during an instruction-manual wave
- editing ComfyUI workflow JSON while the selected task is tracker cleanup
- adding unrelated new features while fixing a validation failure
- browsing unrelated model options while the current task is path repair

### Spinning

Performing activity that looks busy but does not create validated project progress.

Examples:
- creating broad summaries with no action
- writing duplicate documentation
- running non-targeted searches
- repeatedly asking for clarification instead of using local project sources
- leaving the tracker unchanged after implementation

## 3. Progress definition

Progress exists only when at least one of these is true:

```text
A required file was created or improved.
A failing validation was fixed.
A blocker was diagnosed and recorded.
A tracker row advanced with evidence.
A missing dependency was identified and logged.
A test was run and produced a result.
A QA review was completed and recorded.
A runtime artifact was generated and indexed.
A package manifest was updated.
A next-session state file became more accurate.
```

If none of these happened, Codex must stop the current loop and reroute.

## 4. Loop detection rules

Codex must trigger loop recovery if any condition occurs:

```text
Same command fails 2 times with same error.
Same file edited 3 times without passing validation.
Same task remains IN_PROGRESS after 3 implementation attempts.
Same missing dependency is rediscovered twice.
Same validation report is regenerated without changed results.
Same goal text remains active while work has shifted.
No tracker/evidence update after a meaningful change.
No clear next action can be stated in one sentence.
```

## 5. Loop recovery sequence

When a loop is detected:

1. Stop repeating the current action.
2. Write a loop event to the issue log:
   - task
   - repeated action
   - repeated error
   - evidence path
   - suspected root cause
3. Reduce the task to the smallest failing unit.
4. Change strategy:
   - different command
   - different validation method
   - smaller file scope
   - path repair before runtime
   - schema check before workflow execution
   - dry run before GPU run
5. Update the pursuing goal with the new strategy.
6. Run one focused test.
7. If still blocked, mark the task with an appropriate blocked status and continue to the next unblocked dependency.

## 6. Drift detection rules

Codex must check for drift before each edit or command:

```text
Is this action directly tied to the current pursuing goal?
Is this action required by the active wave?
Is this action required to unblock the active task?
Will this action produce evidence?
Is the affected file in the declared scope?
Does the tracker/item list support this action?
```

If the answer is no, Codex must not proceed unless it updates the pursuing goal and logs a scope-change decision.

## 7. Drift recovery sequence

When drift is detected:

1. Stop work outside scope.
2. Record what triggered the drift.
3. Decide whether the drift is:
   - dependency
   - blocker
   - useful future task
   - accidental scope creep
4. Add it to the appropriate log.
5. Return to the active task.
6. If the drift revealed a higher-priority blocker, update the pursuing goal before switching.

## 8. Anti-duplication rules

Before creating a new file, Codex must check:

```text
Does a file with the same purpose already exist?
Is this file a required Wave 58 deliverable?
Should this be an update instead of a new file?
Will this duplicate older blueprint content without adding operational clarity?
Should the file be placed in Instructions, Reports, Manifests, or Hydration_Rehydration?
```

Duplicate files are allowed only when:
- one is a human-readable report and one is machine-readable JSON
- one is a template and one is a filled current state
- one is archived wave evidence and one is the active canonical file
- a cumulative pack intentionally preserves wave history

## 9. Checkpoint cadence

Codex must create a checkpoint when:

```text
A required file is completed.
A validation pass is achieved.
A blocker is classified.
A QA review is completed.
A tracker status changes.
A wave deliverable is packaged.
Before starting a GPU-costing operation.
After completing a GPU-costing operation.
Before ending the session.
```

A checkpoint includes:
- current pursuing goal
- changed files
- validation result
- tracker updates needed/done
- next action

## 10. Proof of forward movement

Codex must maintain a visible proof-of-movement record:

```text
Timestamp
Active_Wave
Active_Task
Action_Taken
Files_Changed
Validation_Run
Result
Evidence_Path
Next_Action
```

The proof-of-movement record prevents future sessions from repeating completed work.

## 11. Bounded retries

Retry limits:

```text
Static validation:
2 retries with same strategy, then change strategy.

Runtime execution:
1 retry with same workflow/settings, then diagnose logs and change strategy.

GPU instance start:
1 retry after identity/state check, then log blocker and continue local work.

Civitai download:
2 retries with backoff/metadata check, then log pending model and continue.

Git push:
1 retry after pull/status check, then log remote sync issue and continue local work.

Visual generation QA:
2 regeneration attempts with targeted changes, then classify root cause and create improvement item.
```

## 12. Anti-stall fallback ladder

If Codex is stuck, it must move down this ladder:

1. Validate file existence.
2. Validate syntax.
3. Validate references.
4. Validate smallest local unit.
5. Validate source-of-truth alignment.
6. Create or update missing instruction/tracker evidence.
7. Switch to a prerequisite task.
8. Mark blocker and continue another unblocked task.

## 13. Runtime auth hard stop and housekeeping budget

When the active runtime blocker is AWS browser/SSO auth, Codex must not turn the block into repeated local housekeeping.

Apply this hard stop when all of the following are true:

```text
C:\Comfy_UI_Main is the active project root.
The latest acceptable local evidence says runtime lane queue passes.
The latest acceptable local evidence says model registry coverage passes.
The latest acceptable local evidence says root preflight or project readiness passes locally.
The latest acceptable Git checkpoint evidence is clean or only needs a final post-evidence commit.
AWS auth is expired, missing, or not yet browser/SSO refreshed.
No user has requested a specific non-runtime implementation task.
```

Under this hard stop, allowed actions are limited to:

```text
1. Record the AWS auth blocker once.
2. Update CURRENT_SESSION_STATE.md, NEXT_ACTION.md, CURRENT_PURSUING_GOAL.md, and trackers once if they are stale.
3. Commit and push an already-created evidence checkpoint when appropriate.
4. Wait for or request the browser/SSO auth step.
```

Do not create another validator, another index refresh, another handoff, another local proof file, or another instruction rewrite with the same gate result unless an input changed or a user explicitly asked for that fix.

Housekeeping budget:

```text
After meaningful implementation: one evidence/index/state refresh is allowed.
After a failed external auth gate: one blocker/state update is allowed.
After no input changed: no new housekeeping artifact is allowed.
```

Any continuation that chooses local work while AWS auth is blocked must state which concrete project capability it advances. If the answer is only "documentation cleanup", "refresh evidence", "recheck current state", or "organize files", stop and report the blocker instead.

## 14. End-of-session anti-loop requirement

Before ending or packaging, Codex must answer in the session state file:

```text
What did I complete?
What proof exists?
What failed?
What did I try?
What should not be repeated?
What is the next exact action?
Which file should the next session open first?
```

## 15. Wave 58 no-loop target

Wave 58 is documentation-heavy, so the major loop risk is rewriting guidance without producing structured usable files. Codex must avoid that by validating these concrete deliverables:

```text
7 core Markdown files exist.
Each file contains required sections.
Manifest exists.
Delivery report exists.
Validation report exists.
Hydration starter exists.
File index exists.
Package zip exists.
```
