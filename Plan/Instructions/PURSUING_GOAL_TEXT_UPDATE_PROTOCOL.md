<!--
Wave 58 — Autonomous Instruction Manual + AI Project Manager Brain
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions
This file is designed for Codex Desktop autonomous operation.
-->

# PURSUING_GOAL_TEXT_UPDATE_PROTOCOL

## 1. Purpose

The pursuing goal text is the live mission statement for the current Codex Desktop session. It prevents drift by making the active objective, scope, evidence, and stop condition explicit.

Codex must update this text whenever the working objective changes.

## 2. Canonical file path

The current pursuing goal must be stored here:

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
```

If the file does not exist, Codex must create it during session rehydration.

## 3. Required goal format

The pursuing goal file must use this structure:

```text
# Current Pursuing Goal

## Active Wave
Wave number and name.

## Goal Statement
One clear sentence stating the exact thing being completed now.

## Why This Goal Is Active
Source-of-truth reason from user request, tracker, itemized list, validation failure, or dependency.

## Current Scope
Files, folders, workflows, registry areas, or systems that may be changed.

## Out of Scope
Explicit list of work not being done in this goal.

## Source Inputs
Blueprint, Items, Tracker, Instructions, GitHub, AWS, Civitai, local files, logs, or generated artifacts used.

## Required Evidence
Exact evidence needed before the task can advance.

## Validation Plan
Static, runtime, visual, audio, video, tracker, and package checks needed.

## Current Status
NOT_STARTED, IN_PROGRESS, BLOCKED, VALIDATING, QA_REVIEW, READY_FOR_CERTIFICATION, COMPLETE_CERTIFIED, or other allowed tracker status.

## Last Action
Most recent concrete action and evidence path.

## Next Action
One exact next action.

## Stop Condition
The condition that means this goal is complete or must be rerouted.

## Fallback / Reroute
What to do if the current path fails.
```

## 4. When Codex must update the pursuing goal

Codex must update the file:

```text
At session start after rehydration.
Before editing files.
Before running a test suite.
Before starting EC2 or any cost-bearing runtime operation.
When selecting a new tracker item.
When a blocker appears.
When validation fails.
When QA fails.
When task scope changes.
When a dependency is discovered.
When a task is ready for certification.
When a task is complete.
Before ending the session.
```

## 5. Goal quality rules

A good pursuing goal is:

```text
Specific:
"Create Wave 58 autonomous instruction manual files" not "work on docs".

Bounded:
Lists what can and cannot be changed.

Evidence-based:
States what proof is required.

Actionable:
Next action can be executed without asking the user.

Aligned:
References tracker/items/user wave request.

Recoverable:
Includes fallback if the action fails.
```

## 6. Bad pursuing goal examples

Bad:

```text
Keep improving the project.
Work on ComfyUI stuff.
Fix everything.
Make it better.
Continue where we left off.
```

Why bad:
- no scope
- no evidence
- no stop condition
- no next action
- easy to drift

## 7. Good pursuing goal examples

Good:

```text
Create the seven Wave 58 autonomous instruction brain Markdown files under C:\Comfy_UI_Main\Plan\Instructions, validate that each required section exists, generate a manifest and validation report, and package them as the Wave 58 cumulative instruction pack.
```

Good:

```text
Repair the tracker row status normalization rule by updating the tracker protocol file, running CSV validation on the master tracker, and recording the validation result before changing any workflow files.
```

Good:

```text
Run local static validation for the Flux base generation workflow templates, fix only missing path/model reference issues, and do not start EC2 until all static checks pass.
```

## 8. Intelligent update triggers

Codex must not update the pursuing goal just because time passed. Update only when there is a meaningful state change.

Meaningful changes include:

```text
new selected task
new evidence
new failure
new blocker
new scope
new validation result
new QA result
new dependency
new source-of-truth contradiction
new completion state
```

## 9. Monitoring the goal for staleness

Before each major action, Codex must check:

```text
Does the pursuing goal still match the current action?
Does the listed scope still match the files being touched?
Does the next action still match what Codex is about to do?
Did validation or QA results change the required work?
Does the stop condition need to change?
```

If stale, update the goal first.

## 10. Goal-to-tracker linkage

Every pursuing goal must reference at least one of:

```text
Tracker row ID
Item ID
Wave deliverable
Known issue ID
Validation failure ID
User requested wave scope
```

If no tracker row exists yet, Codex must create a temporary wave task identifier and later reconcile it to the tracker.

## 11. Goal completion rule

A pursuing goal may be marked complete only when:

```text
All in-scope implementation is done.
All required validation was run.
All required QA was run.
All evidence paths are listed.
Tracker/items were updated or update instructions were written.
Delivery/validation reports were updated.
No known blocker remains inside the stated scope.
```

If any item is missing, the goal must move to `IMPLEMENTED_NOT_VERIFIED`, `QA_FAILED`, `BLOCKED_AUTONOMOUS_RECOVERY_ACTIVE`, or another non-complete state.

## 12. Wave 58 default pursuing goal

For this wave, the first pursuing goal should be:

```text
Create the Wave 58 Autonomous Instruction Manual + AI Project Manager Brain pack by generating the seven required instruction files under C:\Comfy_UI_Main\Plan\Instructions, adding hydration starter state, manifest, delivery report, validation report, and file index, then validate the package without claiming runtime/GPU proof.
```
