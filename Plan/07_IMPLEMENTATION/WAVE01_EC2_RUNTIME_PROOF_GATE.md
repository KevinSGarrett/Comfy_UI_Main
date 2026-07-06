# Wave 01 EC2 Runtime Proof Gate

## Purpose

Prevent accidental EC2 usage and GPU cost.

## Required input

```text
manifests/ec2_runtime_proof/request.json
```

## Required fields

```json
{
  "proof_id": "waveXX_sceneYY",
  "reason": "why EC2 is required",
  "local_validation_report": "path/to/report.json",
  "workflows": ["workflow_api_json_path"],
  "model_assets": ["asset_id_1", "asset_id_2"],
  "expected_runtime_minutes": 30,
  "expected_outputs": ["image", "video", "audio"],
  "stop_instance_after": true,
  "confirmation_token": "START_EC2_RUNTIME_PROOF"
}
```

## Guard rules

The gate must fail if:

```text
local validation failed
request file is missing
model asset list is empty
workflow list is empty
confirmation token is missing
stop_instance_after is false
dry-run commands are missing
```

## EC2 command flow

```text
1. Validate request JSON.
2. Validate local QA report.
3. Create S3 hydration dry-run.
4. Create EC2 start dry-run/report.
5. Require confirmation token.
6. Start EC2 only after confirmation.
7. Hydrate exact model assets.
8. Run ComfyUI runtime proof.
9. Sync back logs and outputs.
10. Stop EC2.
11. Write proof manifest.
```

## Absolute rule

No future wave may bypass this gate.
