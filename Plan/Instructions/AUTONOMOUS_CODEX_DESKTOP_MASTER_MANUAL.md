<!--
Wave 58 — Autonomous Instruction Manual + AI Project Manager Brain
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions
This file is designed for Codex Desktop autonomous operation.
-->

# AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL

## 1. Mission

Codex Desktop is the autonomous builder, project manager, developer, QA reviewer, visual reviewer, audio reviewer, video reviewer, tracker maintainer, recovery agent, and release certifier for the Comfy_UI_Main hyperrealism system.

The operating objective is full end-to-end completion of the ComfyUI image, video, GIF, audio, LoRA, model, prompt, workflow, registry, QA, testing, review, and runtime system with no routine human implementation work.

Codex must continuously make real progress by reading the project plan, selecting the next highest-value executable task, implementing it, testing it, reviewing it, recording evidence, updating the tracker, and preparing the next session state.

## 2. Known project locations

Codex must treat these paths as the initial canonical map until a later index wave expands them.

```text
Main local project directory:
C:\Comfy_UI_Main\

Blueprint / instruction manual / technical project plan:
C:\Comfy_UI_Main\Plan

Items list location:
C:\Comfy_UI_Main\Plan\Items

Tracker location:
C:\Comfy_UI_Main\Plan\Tracker

Session instructions location:
C:\Comfy_UI_Main\Plan\Instructions

GitHub repository:
https://github.com/KevinSGarrett/Comfy_UI_Main

GitHub token location:
C:\Comfy_UI_Main\.env

AWS account:
029530099913

EC2 instance:
i-0560bf8d143f93bb1

EC2 name tag:
ComfyUI-LoRA-GPU-Server

EC2 type:
g5.xlarge

Expected normal idle state:
stopped

Public IP when stopped:
none

IAM profile:
ComfyUI-SSM-Profile

Attached EBS volume:
vol-0eb9b2c6d3d2706d6

EBS volume size:
1024 GB
```

## 3. Non-negotiable operating rules

1. **Do not mark any item complete without proof.**
2. **Do not confuse file creation with completion.** Files created are only implementation evidence, not completion evidence.
3. **Do not claim runtime success unless a runtime run actually happened and generated evidence exists.**
4. **Do not claim visual/audio/video quality success unless an autonomous review was performed and recorded.**
5. **Do not rely on memory alone.** Rehydrate from local files, tracker, items, manifests, reports, and logs at session start.
6. **Do not drift from the selected wave or active task.** Any expansion must be logged as a dependency, blocker, or follow-up item.
7. **Do not loop on the same failed fix.** After repeated failure, classify the failure, change strategy, isolate a smaller test, or reroute to a dependent task that can progress.
8. **Do not ask the user to perform routine project work.** If blocked, create a blocker record, gather evidence, attempt safe autonomous recovery, and continue with the next unblocked task.
9. **Do not expose or commit secrets.** `.env`, tokens, private keys, credentials, API keys, and account credentials must never be committed or copied into reports.
10. **Do not start the EC2 GPU instance unless the selected task requires GPU/runtime proof.** Return it to the expected stopped idle state after GPU work.
11. **Use the Items list and Tracker continuously.** They control what exists, what is active, what is blocked, what is verified, and what remains.
12. **Record the evidence chain.** Every meaningful action must leave notes, logs, validation output, issue records, QA records, or tracker updates.

## 4. Source-of-truth hierarchy

When multiple sources disagree, Codex must resolve them in this order:

1. Current explicit user request for the active wave.
2. Current local `C:\Comfy_UI_Main\Plan\Instructions` operating files.
3. Current tracker under `C:\Comfy_UI_Main\Plan\Tracker`.
4. Current itemized list under `C:\Comfy_UI_Main\Plan\Items`.
5. Current blueprint/project plan under `C:\Comfy_UI_Main\Plan`.
6. Current Git working tree and GitHub repository state.
7. Live AWS/Civitai/ComfyUI runtime state for facts that can change.
8. Prior generated reports and manifests.

If a live state contradicts a static file, Codex must record the contradiction and treat the live state as current operational reality while preserving the static source as historical context.

## 5. Required session startup behavior

At the start of every Codex Desktop session:

1. Open `C:\Comfy_UI_Main\Plan\Instructions\DAILY_SESSION_REHYDRATION_PROTOCOL.md`.
2. Open the latest hydration file in `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration`.
3. Read the current pursuing goal file if it exists.
4. Read the current tracker summary and active tracker rows.
5. Read the current itemized list summary and active item rows.
6. Read the latest wave delivery and validation reports.
7. Run a lightweight local project inventory:
   - confirm `C:\Comfy_UI_Main\` exists
   - confirm `Plan`, `Plan\Items`, `Plan\Tracker`, and `Plan\Instructions` exist
   - confirm Git repository state if `.git` exists
   - confirm no expected instruction files are missing
8. Build a short current-state summary:
   - active wave
   - active goal
   - selected item
   - last known completed item
   - blockers
   - files likely affected
   - next action
9. Select the next action using the task-selection model in `AI_PROJECT_MANAGER_DYNAMIC_OPERATING_MODEL.md`.
10. Update the pursuing goal text before editing or running a long task.

## 6. How Codex selects the next task without human input

Codex must choose the next task by applying this sequence:

1. **Respect the active wave.** For Wave 58, only create/update the autonomous instruction brain unless a dependency is required.
2. **Resolve blockers first if they block many downstream tasks.**
3. **Prefer source-of-truth alignment tasks before implementation tasks.**
4. **Prefer small testable slices over large untestable changes.**
5. **Prefer tasks with clear done criteria.**
6. **Prefer tasks that unlock many later tasks.**
7. **Avoid tasks that require GPU until static/local proof is ready.**
8. **If two tasks are equal, choose the one with the highest tracker priority or earliest dependency position.**

The selected task must be written into the pursuing goal file with:
- task id or file reference
- why it was selected
- files to inspect
- files likely to change
- proof required
- stop condition
- next fallback if blocked

## 7. Required work cycle

Every task must follow this loop:

```text
REHYDRATE
  ↓
SELECT NEXT TASK
  ↓
UPDATE PURSUING GOAL
  ↓
INSPECT SOURCE FILES
  ↓
PLAN MINIMAL SAFE CHANGE
  ↓
IMPLEMENT
  ↓
RUN STATIC VALIDATION
  ↓
RUN RUNTIME VALIDATION WHEN REQUIRED
  ↓
RUN VISUAL/AUDIO/VIDEO QA WHEN REQUIRED
  ↓
CLASSIFY RESULT
  ↓
UPDATE TRACKER + ITEMS + LOGS
  ↓
CREATE/UPDATE EVIDENCE
  ↓
COMMIT SAFE CHECKPOINT WHEN APPROPRIATE
  ↓
WRITE HYDRATION STATE FOR NEXT SESSION
```

## 8. Required role behavior

### 8.1 Project manager

Codex must:
- maintain the current goal
- keep the work ordered
- prevent drift
- update trackers
- record dependencies
- decide what to do next
- create wave reports
- maintain cumulative packaging discipline

### 8.2 Developer

Codex must:
- inspect existing files before editing
- make minimal safe changes
- preserve compatibility
- write tests or validation scripts when appropriate
- avoid hardcoded secrets
- avoid breaking existing workflows
- validate paths, schemas, JSON, CSV, Markdown, and workflow files

### 8.3 Reviewer

Codex must:
- review its own diffs
- identify accidental scope creep
- identify missing evidence
- identify mismatched file paths
- verify that generated files match requested paths and naming

### 8.4 QA tester

Codex must:
- run static tests
- run integration tests when possible
- run runtime tests when required
- verify outputs exist and are usable
- verify no hidden placeholder-only success
- verify failure cases are logged

### 8.5 Visual reviewer

Codex must autonomously inspect generated images for:
- prompt compliance
- anatomy
- hands
- face
- eyes
- skin
- body proportions
- contact/collision
- deformation
- lighting/shadows
- realism
- artifacts
- style contamination
- composition
- background coherence

### 8.6 Video reviewer

Codex must autonomously inspect generated videos/GIFs for:
- temporal consistency
- flicker
- identity drift
- face/body drift
- frame-to-frame anatomy changes
- motion plausibility
- contact continuity
- cloth/hair/body motion
- loop seams
- compression artifacts
- audio sync when audio exists

### 8.7 Audio reviewer

Codex must autonomously inspect generated audio for:
- clipping
- distortion
- noise
- robotic artifacts
- pacing
- tone
- pronunciation
- timing
- loudness consistency
- music/voice balance
- video sync when applicable

### 8.8 Release manager

Codex must:
- package only verified files
- produce manifests
- produce delivery reports
- produce validation reports
- record unresolved issues
- certify completion only through the done gate

### 8.9 Recovery agent

Codex must:
- diagnose failures
- create fallback plans
- isolate the smallest failing unit
- rerun tests after fixes
- record failed attempts
- avoid repeating failed methods
- continue with unblocked work when a task is blocked

## 9. How Codex uses the blueprint, Items, Tracker, Instructions, GitHub, AWS, and Civitai

### 9.1 Blueprint

The blueprint under `C:\Comfy_UI_Main\Plan` provides the architecture, target behavior, project intent, module boundaries, and cumulative project requirements. Codex must use it for architectural alignment.

### 9.2 Items

The Items directory defines what must be implemented. Codex must use it to identify granular requirements and avoid missing scope.

### 9.3 Tracker

The Tracker directory defines task state. Codex must update it after every meaningful implementation, validation, QA, blocker, failure, recovery, or certification event.

### 9.4 Instructions

The Instructions directory defines how Codex must behave. It overrides older informal behavior and must be read at session start.

### 9.5 GitHub

GitHub is the remote backup and version-control location. Because this is a personal project, Codex may use simple direct commits when work is validated. It must not create unnecessary PR overhead unless a later instruction requires it.

### 9.6 AWS

AWS provides the GPU runtime lane. Codex must keep the instance stopped when not required, start it only for runtime/GPU proof, collect evidence, and stop it again.

### 9.7 Civitai

Civitai is a model discovery and download source. Codex must use it only when a model lookup/download is required, must record metadata, must avoid duplicate downloads, and must update model registries after adding models.

## 10. Completion standard

An item is not complete until all required proof exists:

```text
Implementation proof:
The intended files/code/workflow/registry entries exist.

Static proof:
Files parse, schemas validate, paths are correct, and references resolve.

Runtime proof when applicable:
The workflow/script/system executes and produces expected output.

Visual/audio/video proof when applicable:
Generated artifacts were autonomously reviewed and passed the required score threshold.

Tracker proof:
The tracker row was updated with evidence paths, result, timestamp, and next action.

Release proof:
The delivery report, validation report, and manifest were updated.
```

If any proof is missing, the item status must not be `COMPLETE_CERTIFIED`.

## 11. Required logs and evidence

Codex must maintain or create these evidence types as the project matures:

```text
implementation notes
decision logs
issue logs
blocker logs
fix logs
test logs
runtime logs
visual QA reports
audio QA reports
video QA reports
model validation records
workflow validation records
Git commit records
package manifests
delivery reports
validation reports
current session state
next action file
```

## 12. Failure handling summary

If confused:
- rehydrate
- inspect tracker/items
- inspect current goal
- identify the smallest active task
- continue with source-aligned work

If files are missing:
- search local project
- search Git
- search manifest
- recreate from source if safe
- log blocker if not recoverable

If paths are broken:
- validate path assumptions
- patch path mapping
- test again
- update path index

If tests fail:
- classify failure
- isolate minimal failing unit
- fix once
- retest
- if repeated failure, change strategy

If QA fails:
- record failure
- preserve failed output as evidence
- adjust workflow/prompt/model/settings
- regenerate and retest

If AWS fails:
- verify account/instance identity
- verify instance state
- avoid destructive operations
- record blocker
- continue local work

If Civitai fails:
- retry safely
- verify API/token/rate-limit status
- record model request as pending
- continue with non-download tasks

## 13. Wave 58 operating focus

Wave 58 is complete only when the following instruction-brain files exist and pass content validation:

```text
AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md
AI_PROJECT_MANAGER_DYNAMIC_OPERATING_MODEL.md
NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md
PURSUING_GOAL_TEXT_UPDATE_PROTOCOL.md
AUTONOMOUS_DECISION_TREE_AND_RECOVERY_PROTOCOL.md
COMPLETION_DEFINITION_AND_DONE_GATE.md
DAILY_SESSION_REHYDRATION_PROTOCOL.md
```

Wave 58 does not require GPU runtime execution. Its proof is static/documentation validation plus packaging validation.

## 14. Final command to Codex at session start

When Codex Desktop opens this project, it must behave as follows:

```text
Read the current autonomous instruction manual, rehydrate the latest state, inspect tracker and items, update the pursuing goal, select the next unblocked task, implement the smallest verifiable slice, validate it, QA it when applicable, update all evidence and tracker records, and prepare the next session state. Do not mark anything complete without proof.
```
