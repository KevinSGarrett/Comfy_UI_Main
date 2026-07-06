# Session End Hydration Checklist

## Goal

This checklist prevents loss of work between autonomous Codex Desktop sessions.

## Required end-of-session writes

Before ending, Codex must update these files:

```text
Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
Plan\Instructions\Hydration_Rehydration\RECENT_DECISIONS.md
Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
Plan\Instructions\Hydration_Rehydration\PROOF_OF_MOVEMENT_LOG.csv
Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md
```

## Required summary fields

The end state must capture:

- session date/time
- active wave or task
- files changed
- tests run
- tests not run and why
- QA completed
- QA still pending
- blockers
- known limitations
- next exact action
- tracker rows updated
- itemized-list rows updated
- evidence paths created
- GitHub status
- AWS/EC2 status
- Civitai/model status

## Tracker update rule

Every item touched must have a tracker update. If implementation was completed but QA was not run, the tracker status must be `pending_validation`, not `complete`.

## Itemized-list update rule

Every new deliverable, script, registry, template, evidence file, or protocol must be represented in the itemized-list supplement or main itemized list.

## QA evidence rule

Every generated artifact must have evidence or a clear note explaining why evidence is pending.

## Blocker rule

Blockers must include:

- blocker ID
- affected item / tracker ID
- blocker type
- exact missing dependency or failed condition
- best next non-blocked task
- whether EC2, GitHub, Civitai, or local filesystem is involved

## Resume file rule

The final file written should be:

```text
RESUME_HERE_NEXT_CODEX_SESSION.md
```

That file must be concise enough for the next Codex window to read first, but detailed enough to continue without asking the user.
