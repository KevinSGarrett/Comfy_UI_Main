# Wave 37 Local/EC2 Sync Structure

## Local-to-EC2 sync staging

```text
12_EC2_SYNC_STAGING/
├── upload_manifest/
├── required_models/
├── required_loras/
├── required_workflows/
├── required_inputs/
├── runtime_scripts/
├── expected_outputs/
└── pullback_artifacts/
```

## Sync rule
Only required files should sync to EC2. Do not sync the whole local system by default.
