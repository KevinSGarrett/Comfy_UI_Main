<!--
Wave 58 — Autonomous Instruction Manual + AI Project Manager Brain
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions
This file is designed for Codex Desktop autonomous operation.
-->

# DAILY_SESSION_REHYDRATION_PROTOCOL

## 1. Purpose

This protocol tells Codex Desktop how to restart work every day or every new session without losing context, repeating work, drifting, or asking the user to explain the project again.

Rehydration means rebuilding the current project state from files, trackers, manifests, reports, logs, Git state, and runtime evidence.

## 2. Required rehydration directory

Codex must maintain:

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration
```

Required files:

```text
CURRENT_SESSION_STATE.md
CURRENT_PURSUING_GOAL.md
NEXT_ACTION.md
BLOCKERS.md
KNOWN_ISSUES.md
RECENT_DECISIONS.md
QA_EVIDENCE_INDEX.md
PROOF_OF_MOVEMENT_LOG.csv
```

If any required file is missing, Codex must create it from the best available state.

## 3. Session start checklist

At the beginning of every session:

```text
1. Confirm C:\Comfy_UI_Main exists.
2. Confirm C:\Comfy_UI_Main\Plan exists.
3. Confirm C:\Comfy_UI_Main\Plan\Items exists.
4. Confirm C:\Comfy_UI_Main\Plan\Tracker exists.
5. Confirm C:\Comfy_UI_Main\Plan\Instructions exists.
6. Read AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md.
7. Read CURRENT_SESSION_STATE.md.
8. Read CURRENT_PURSUING_GOAL.md.
9. Read NEXT_ACTION.md.
10. Read BLOCKERS.md.
11. Read KNOWN_ISSUES.md.
12. Read latest delivery report.
13. Read latest validation report.
14. Read tracker summary/master tracker.
15. Read itemized list summary/master item list.
16. Check Git status.
17. Build active task candidate set.
18. Select next action.
19. Update CURRENT_PURSUING_GOAL.md.
20. Begin work.
```

## 4. Session state file format

`CURRENT_SESSION_STATE.md` must include:

```text
# Current Session State

## Last Updated
Timestamp.

## Active Wave
Wave number and name.

## Current Project Phase
Instruction / Indexing / Operations / QA / Runtime / Packaging / Recovery.

## Last Completed Certified Work
Exact task and evidence path.

## Current Pursuing Goal
Summary and link to CURRENT_PURSUING_GOAL.md.

## Active Files
Files currently in scope.

## Tracker State
Current tracker row/status or tracker update artifact.

## Items State
Current item IDs or item coverage.

## Validation State
Latest validation result and evidence path.

## QA State
Latest QA result and evidence path.

## Git State
Branch, dirty status, latest commit if available.

## AWS State
Only if checked; otherwise say not checked this session.

## Civitai State
Only if used; otherwise say not used this session.

## Blockers
Active blockers with status.

## Known Issues
Active known issues.

## Next Action
One exact next action.

## Do Not Repeat
Failed actions or duplicate work to avoid.
```

## 5. NEXT_ACTION file format

`NEXT_ACTION.md` must include:

```text
# Next Action

## Action
One exact action.

## Why
Reason this is the next best step.

## Files to Open First
List.

## Expected Output
List.

## Validation
Checks to run.

## If This Fails
Fallback.
```

## 6. BLOCKERS file format

`BLOCKERS.md` must include:

```text
# Blockers

| Blocker ID | Status | Wave | Area | Description | Evidence | Recovery Attempted | Next Autonomous Action |
|---|---|---|---|---|---|---|---|
```

Blocker statuses:

```text
OPEN
IN_RECOVERY
REROUTED
WAITING_EXTERNAL_RESOURCE
RESOLVED
```

## 7. KNOWN_ISSUES file format

`KNOWN_ISSUES.md` must include:

```text
# Known Issues

| Issue ID | Wave | Severity | Area | Description | Evidence | Proposed Fix | Status |
|---|---|---|---|---|---|---|---|
```

Severity:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

## 8. RECENT_DECISIONS file format

`RECENT_DECISIONS.md` must include:

```text
# Recent Decisions

| Decision ID | Timestamp | Wave | Decision | Reason | Files Affected | Follow-Up |
|---|---|---|---|---|---|---|
```

## 9. QA evidence index format

`QA_EVIDENCE_INDEX.md` must include:

```text
# QA Evidence Index

| Evidence ID | Type | Wave | Artifact | Review File | Score/Result | Status |
|---|---|---|---|---|---|---|
```

Types:

```text
STATIC_VALIDATION
RUNTIME_VALIDATION
IMAGE_QA
VIDEO_QA
AUDIO_QA
WORKFLOW_QA
MODEL_QA
PACKAGE_VALIDATION
```

## 10. Proof-of-movement log format

`PROOF_OF_MOVEMENT_LOG.csv` columns:

```text
Timestamp,Wave,Task,Action,Files_Changed,Validation_Run,Result,Evidence_Path,Next_Action
```

Codex must append a row whenever it completes a meaningful action.

## 11. Session end checklist

Before ending a session:

```text
1. Save all intended files.
2. Run required validation.
3. Record validation results.
4. Update tracker or tracker update artifact.
5. Update item coverage or item update artifact if applicable.
6. Update CURRENT_SESSION_STATE.md.
7. Update CURRENT_PURSUING_GOAL.md.
8. Update NEXT_ACTION.md.
9. Update BLOCKERS.md.
10. Update KNOWN_ISSUES.md.
11. Update RECENT_DECISIONS.md.
12. Update QA_EVIDENCE_INDEX.md.
13. Append PROOF_OF_MOVEMENT_LOG.csv.
14. Update delivery report.
15. Update validation report.
16. Update manifest.
17. Check Git status.
18. Commit validated work if appropriate.
19. Do not leave AWS GPU instance running unless a documented active runtime task requires it.
```

## 12. Rehydration after crash or interrupted session

If the previous session ended unexpectedly:

```text
1. Check Git status for changed files.
2. Check recently modified files.
3. Check temporary output/log folders.
4. Read last proof-of-movement row.
5. Read latest validation report.
6. Re-run validation for changed files.
7. Do not assume incomplete edits are valid.
8. Update CURRENT_SESSION_STATE.md with recovery status.
```

## 13. Rehydration after failed GPU/runtime session

If a GPU/runtime session failed:

```text
1. Confirm EC2 instance state.
2. Stop instance if it is running and no active GPU task requires it.
3. Pull back logs/output if available.
4. Record failure.
5. Do local/static diagnosis before trying GPU again.
6. Update blocker/issue log.
```

## 14. Rehydration after generated artifact QA failure

If an image/video/audio artifact failed QA:

```text
1. Preserve failed artifact.
2. Preserve QA scorecard.
3. Record root-cause hypothesis.
4. Create targeted next action.
5. Avoid regenerating blindly.
6. Update tracker to QA_FAILED or BLOCKED_AUTONOMOUS_RECOVERY_ACTIVE.
```

## 15. Wave 58 starter state

After extracting the Wave 58 pack, Codex must create or confirm these starter files:

```text
CURRENT_SESSION_STATE.md
CURRENT_PURSUING_GOAL.md
NEXT_ACTION.md
BLOCKERS.md
KNOWN_ISSUES.md
RECENT_DECISIONS.md
QA_EVIDENCE_INDEX.md
PROOF_OF_MOVEMENT_LOG.csv
```

The Wave 58 starter state should tell the next session to begin with Wave 59 unless Wave 58 validation fails.
