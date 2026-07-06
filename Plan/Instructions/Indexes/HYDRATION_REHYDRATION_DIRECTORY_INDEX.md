<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions\Indexes
Generated: 2026-07-06T04:53:12Z
-->

# HYDRATION_REHYDRATION_DIRECTORY_INDEX

## 1. Purpose

This file indexes the hydration and rehydration directory used by Codex Desktop to continue autonomous work across sessions without losing state.

The hydration directory is not just notes. It is the active session continuity layer.

## 2. Canonical directory

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration
```

## 3. Required files

| File | Purpose | Update rule |
|---|---|---|
| `CURRENT_SESSION_STATE.md` | Current active work state, recent changes, verified status, and context for resume. | Update after major work blocks and before session end. |
| `CURRENT_PURSUING_GOAL.md` | The active goal Codex is pursuing. | Update whenever the active goal materially changes. |
| `NEXT_ACTION.md` | The next concrete action Codex should take on resume. | Update before session end and after blockers. |
| `BLOCKERS.md` | Current blockers that prevent progress. | Update immediately when a blocker appears or clears. |
| `KNOWN_ISSUES.md` | Non-blocking issues, defects, and risks. | Update whenever an issue is found or resolved. |
| `RECENT_DECISIONS.md` | Recent decisions and why they were made. | Append after significant autonomous decisions. |
| `QA_EVIDENCE_INDEX.md` | Index of QA proof files and artifact review evidence. | Update whenever QA evidence is created. |
| `PROOF_OF_MOVEMENT_LOG.csv` | Chronological proof that Codex is making real progress. | Append after meaningful progress events. |

## 4. Session-start rehydration order

Codex must read files in this order:

1. `AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
2. `COMPLETION_DEFINITION_AND_DONE_GATE.md`
3. `NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md`
4. `DAILY_SESSION_REHYDRATION_PROTOCOL.md`
5. `Indexes\MASTER_PROJECT_LOCATION_INDEX.md`
6. `Indexes\LOCAL_DIRECTORY_CATALOGUE.md`
7. `Hydration_Rehydration\CURRENT_SESSION_STATE.md`
8. `Hydration_Rehydration\CURRENT_PURSUING_GOAL.md`
9. `Hydration_Rehydration\NEXT_ACTION.md`
10. `Hydration_Rehydration\BLOCKERS.md`
11. `Hydration_Rehydration\KNOWN_ISSUES.md`
12. active Tracker files
13. active Item files

Codex must not choose a new task until it understands the current state.

## 5. Session-end hydration checklist

Before ending a session, Codex must write:

```text
What changed:
What was verified:
What failed:
What remains blocked:
What was deferred:
What files were changed:
What tests were run:
What QA evidence was created:
What tracker rows changed:
What item rows changed:
What the current pursuing goal is:
What the next action is:
```

## 6. Hydration file classification

| File | Source-of-truth type | Can Codex update continuously? | Can Codex mark done from this alone? |
|---|---|---:|---:|
| `CURRENT_SESSION_STATE.md` | Current operational memory | Yes | No |
| `CURRENT_PURSUING_GOAL.md` | Active goal state | Yes | No |
| `NEXT_ACTION.md` | Resume action | Yes | No |
| `BLOCKERS.md` | Blocker state | Yes | No |
| `KNOWN_ISSUES.md` | Issue state | Yes | No |
| `RECENT_DECISIONS.md` | Decision log | Yes | No |
| `QA_EVIDENCE_INDEX.md` | Evidence locator | Yes | No |
| `PROOF_OF_MOVEMENT_LOG.csv` | Progress log | Append | No |

Completion requires Tracker + tests + QA + evidence, not hydration alone.

## 7. Anti-loss rule

Codex must assume the next session may start with no memory except files on disk. Therefore, before stopping, Codex must leave enough written state that a new session can resume without asking:

- what was being done
- where files are
- what passed
- what failed
- what is blocked
- what should happen next
- what must not be repeated

## 8. Wave 59 state update

Wave 59 adds the index/catalogue layer. After this wave, future hydration state should reference:

```text
C:\Comfy_UI_Main\Plan\Instructions\Indexes\MASTER_PROJECT_LOCATION_INDEX.md
C:\Comfy_UI_Main\Plan\Instructions\Indexes\LOCAL_DIRECTORY_CATALOGUE.md
C:\Comfy_UI_Main\Plan\Instructions\Indexes\PLAN_DIRECTORY_FILE_INDEX.md
C:\Comfy_UI_Main\Plan\Instructions\Indexes\ITEMS_DIRECTORY_FILE_INDEX.md
C:\Comfy_UI_Main\Plan\Instructions\Indexes\TRACKER_DIRECTORY_FILE_INDEX.md
C:\Comfy_UI_Main\Plan\Instructions\Indexes\INSTRUCTIONS_DIRECTORY_FILE_INDEX.md
```
