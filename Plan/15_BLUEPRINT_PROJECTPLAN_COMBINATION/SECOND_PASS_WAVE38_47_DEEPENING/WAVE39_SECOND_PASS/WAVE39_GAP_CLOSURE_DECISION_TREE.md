# Wave 39 Gap Closure Decision Tree

## Gap closure decisions

```text
already_covered → link to existing artifact
partially_covered → add missing schema/registry/catalog record
needs_registry → create registry entry
needs_schema → create schema and example
needs_workflow → add workflow placeholder or runtime bridge
needs_runtime_proof → keep blocked until actual output/evidence exists
needs_handoff → add handoff section/checklist
conflict_requires_decision → create decision record
obsolete_or_superseded → archive or mark superseded
```

## Rule

A gap is not closed just because a document mentions it. It is closed only when an artifact, registry/catalog record, and validation gate exist.
