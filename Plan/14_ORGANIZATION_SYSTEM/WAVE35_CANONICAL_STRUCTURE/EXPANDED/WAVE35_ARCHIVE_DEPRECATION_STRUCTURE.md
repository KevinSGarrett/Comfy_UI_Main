# Wave 35 Archive and Deprecation Structure

Deprecated files should be clear, not scattered.

```text
10_ARCHIVED/
├── superseded_workflows/
├── failed_experiments/
├── deprecated_registries/
├── old_prompts/
├── old_profiles/
└── migration_snapshots/
```

## Required metadata

Every archived item should record:

- replaced_by
- archived_reason
- archived_at
- safe_to_delete
- migration_notes
