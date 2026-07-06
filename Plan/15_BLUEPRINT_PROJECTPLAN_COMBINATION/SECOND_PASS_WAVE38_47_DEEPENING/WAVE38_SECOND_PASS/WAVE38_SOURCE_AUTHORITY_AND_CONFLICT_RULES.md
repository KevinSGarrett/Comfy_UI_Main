# Wave 38 Source Authority and Conflict Rules

## Authority order

1. Actual runtime evidence and corrected reality-status records.
2. Current cumulative implementation structure.
3. Blueprint/manual/technical project plan intent.
4. Tracker acceptance criteria and task rows.
5. Generated second-pass merge artifacts.

## Conflict rule

When sources disagree:
- preserve both source statements,
- classify the conflict,
- do not overwrite runtime proof status,
- create a merge action,
- require validation before promotion.

## Conflict classes

```text
proof_conflict
path_conflict
naming_conflict
workflow_conflict
catalog_conflict
scope_conflict
deprecated_source_conflict
runtime_boundary_conflict
```
