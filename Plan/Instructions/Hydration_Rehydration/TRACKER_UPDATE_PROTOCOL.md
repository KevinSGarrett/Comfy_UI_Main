# Tracker Update Protocol

## Purpose

This protocol defines how Codex updates tracker rows so future sessions know exactly what happened.

## Tracker location

```text
C:\Comfy_UI_Main\Plan\Tracker
```

## When to update the tracker

Update the tracker whenever Codex:

- starts a task
- completes implementation
- runs a test
- performs QA
- finds a failure
- applies a fix
- retests
- creates evidence
- blocks or unblocks an item
- changes next action
- creates a cumulative pack

## Required tracker fields

Every tracker row or supplement row should include:

- wave
- tracker_id
- deliverable
- implementation_status
- qa_status
- evidence_path
- remaining_runtime_validation
- blocker_id if blocked
- last_updated
- next_action

## Status values

Use consistent values:

- not_started
- in_progress
- implemented_pending_test
- pending_validation
- qa_passed
- qa_failed
- needs_retest
- blocked
- complete
- superseded

## Critical rule

Do not use `complete` unless done certification exists.

Acceptable pre-completion states:

- `implemented_pending_test`
- `pending_validation`
- `qa_passed`
- `needs_retest`

## Evidence path rule

Every tracker update that claims progress must include at least one evidence path.

Examples:

```text
Plan/Instructions/QA/Evidence/Workflow_Validation/<record>.json
Plan/Instructions/Reports/<report>.md
Plan/Instructions/Waves/Wave62/<supplement>.csv
```

## Blocked item rule

A blocked row must include:

- why blocked
- blocking dependency
- date identified
- best non-blocked next task

## Retest rule

If a task fails and then passes, preserve both:

- original failure evidence
- successful retest evidence
