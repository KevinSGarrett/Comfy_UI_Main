# Local-First Runtime Validation Strategy

## Primary rule

Do as much validation locally as possible before EC2 is started.

## Local-only checks

The following checks must always run locally first:

```text
workflow JSON parse
workflow graph link validation
model reference extraction
registry JSON parsing
schema parsing
.env key validation
tracker CSV column inventory
Plans ZIP file inventory
advanced additions ZIP inventory
object_info validation if local ComfyUI is running
```

## Checks that do not need GPU

These checks do not need GPU and must not start EC2:

- JSON syntax
- CSV parsing
- ZIP manifest listing
- schema file parsing
- prompt/pass-plan JSON parsing
- model filename extraction
- graph reachability
- disabled node inventory
- Git repo hygiene
- `.env.example` existence
- no model binaries in Git
- Civitai metadata raw-cache structure
- S3 key naming convention validation

## Checks that may need local ComfyUI but not EC2

- `/object_info` node visibility
- queue/history endpoint sanity
- API JSON compilation without high-cost generation
- custom node presence
- workflow API-format compatibility

## Checks that justify EC2

EC2 may be started only for:

- GPU model loading proof
- VAE/checkpoint/LoRA memory compatibility proof
- video model runtime proof
- high-res image runtime proof
- final output proof
- node that only exists on EC2 and cannot be mirrored locally

## EC2 preflight gate

Before EC2 starts, the AI project manager must produce:

```json
{
  "static_validation": "PASS",
  "local_object_info": "PASS or explicitly unavailable",
  "model_hydration_plan": "generated",
  "required_models": "minimal list only",
  "estimated_ec2_reason": "clear reason",
  "rollback_plan": "defined",
  "stop_instance_after_run": true
}
```

## Failure policy

If local static validation fails, do not start EC2.

If object_info fails because a custom node is missing locally, do one of:

1. install the custom node locally,
2. mark it as EC2-only and prove it on EC2 later,
3. replace the workflow node with a supported module,
4. remove the module from production scope.

Never ignore missing node types.
