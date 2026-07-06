# Wave 01 Ongoing Source Integration Rules

## Sources marked ongoing

The following sources are still being built and must be re-ingested as the 35 waves progress:

```text
wave42_working_tracker_20260704_105253_ltxv_router_metadata_repromotion_20260705_142403_asset_compat_registry_promotion.csv
Plans.zip
```

## Rule 1 — Do not freeze ongoing sources

The AI system must not treat these as final truth. They are upstream planning/runtime artifacts that may change.

## Rule 2 — Preserve traceability

When a future wave uses one of these sources, it must record:

```text
source file name
sha256
relevant path or row IDs
what was imported
what was changed
what was ignored
why
```

## Rule 3 — Reconcile, do not blindly copy

If the tracker/Plans conflict with the 35-wave blueprint:

```text
1. Record the conflict.
2. Identify which source is newer or more authoritative.
3. Preserve both references.
4. Update the 35-wave blueprint only after a decision log entry exists.
```

## Rule 4 — Keep user-approved direction primary

The current 35-wave blueprint is now the AI PM operating plan. The tracker and Plans ZIP are supporting sources.

## Rule 5 — Never import restrictions that block personal creative usage unless the user explicitly asks

The AI system should focus on technical runtime, QA, implementation, asset compatibility, local/EC2 proof, and visual/audio quality gates.

## Rule 6 — Treat future tracker rows as implementation tasks

Tracker rows should become GitHub issues/project tasks, not be pasted into the blueprint blindly.
