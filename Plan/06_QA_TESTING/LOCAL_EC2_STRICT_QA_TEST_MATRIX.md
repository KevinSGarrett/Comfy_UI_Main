# Local + EC2 Strict QA Test Matrix

## Local tests must run with EC2 off

| Test | Local? | Requires models? | Purpose |
|---|---:|---:|---|
| JSON schema validation | yes | no | Validate scene/pass/mask/QA artifacts. |
| Workflow graph reachability | yes | no | Ensure intended nodes feed outputs. |
| Model manifest lookup | yes | no | Validate model IDs and paths without loading binaries. |
| Engine compatibility check | yes | no | Prevent Flux/SDXL/Pony mismatch. |
| Pass planner dry-run | yes | no | Prove the AI can choose pass order. |
| App Mode config validation | yes | no | Ensure exposed controls map to valid fields. |
| Python unit tests | yes | no | Validate orchestrator logic. |
| Placeholder mask QA | yes | no | Validate mask schema and overlay creation with sample images. |

## EC2 tests require GPU runtime proof

| Test | EC2? | Purpose |
|---|---:|---|
| Checkpoint/LoRA loader proof | yes | Confirm actual model files load. |
| Base image generation proof | yes | Confirm output images exist and decode. |
| Masked pass proof | yes | Confirm inpaint/detail pass changes only target region. |
| Video/GIF proof | yes | Confirm frame/video pipeline executes. |
| Audio proof | maybe | Confirm audio generation/mix executes when model/API present. |
| End-to-end proof | yes | Confirm full pipeline with manifests and QA. |

## Required EC2 stop rule

Every EC2 proof script must end with either:

```text
EC2_STOPPED_CONFIRMED=true
```

or a blocking failure report explaining why the instance could not be stopped.
