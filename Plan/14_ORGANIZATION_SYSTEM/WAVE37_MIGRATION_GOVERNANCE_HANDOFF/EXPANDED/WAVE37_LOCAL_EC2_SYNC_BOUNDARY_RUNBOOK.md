# Wave 37 Local/EC2 Sync Boundary Runbook

## Purpose

Use EC2 only for required runtime proof or expensive rendering, and only after preview/preflight gates allow it.

## Sync staging structure

```text
12_EC2_SYNC_STAGING/
├── upload_manifest/
├── required_models/
├── required_loras/
├── required_workflows/
├── required_inputs/
├── runtime_scripts/
├── expected_outputs/
├── pullback_artifacts/
└── sync_logs/
```

## EC2 sync rule

Do not sync the entire local system. Sync only the cataloged files needed for the selected run.

## Pullback rule

Every EC2 output must pull back:
- output artifact
- run log
- QA evidence
- manifest
- cost/runtime summary
- stop confirmation
