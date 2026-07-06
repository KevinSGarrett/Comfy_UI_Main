# Wave 37 Migration Rollback and Backup Plan

## Required before migration

```text
11_BACKUPS/
├── pre_migration_snapshot/
├── workflow_snapshot/
├── registry_snapshot/
├── catalog_snapshot/
└── rollback_manifest/
```

## Rollback manifest fields

- migration_id
- source_path
- target_path
- file_count_before
- file_count_after
- hash_sample_before
- hash_sample_after
- rollback_command
- validation_status

## Rollback rule

A migration is not complete until rollback is possible and validation passes.
