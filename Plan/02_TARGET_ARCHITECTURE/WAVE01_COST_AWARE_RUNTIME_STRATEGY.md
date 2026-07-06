# Wave 01 Cost-Aware Runtime Strategy

## Main rule

EC2 is off by default. Local development happens first.

## Why

The system needs to avoid expensive GPU runtime while the project is still validating:

- repo structure
- workflow JSON
- model registries
- schema contracts
- pass planner decisions
- mask plans
- QA manifests
- source inventories
- Git safety rules

These can be validated without turning on EC2.

## Local development modes

### Mode A — No GPU / static-only

Allowed:

```text
schema validation
workflow JSON parse
workflow graph reachability
workflow linting
model reference lookup
model registry validation
pass plan compilation
QA manifest validation
GitHub repo validation
EC2 dry-run planning
S3 dry-run hydration planning
```

Not allowed:

```text
claims of runtime generation
claims of model load proof
claims of visual realism proof
claims of video/audio generation proof
```

### Mode B — Local GPU available

Allowed in addition:

```text
small smoke tests
one-frame image test
low-res workflow test
small inpaint test
local ComfyUI /prompt proof
```

Must still avoid:

```text
large batch generation
full video render
large model hydration without manifest
untracked output sprawl
```

### Mode C — EC2 runtime proof

Use only when:

```text
local static validation passes
exact workflows are selected
exact model assets are selected
expected cost/risk is known
dry-run command manifest exists
user/AI operator approves exact proof
```

## EC2 proof minimum package

Before EC2 starts, create:

```text
manifests/ec2_runtime_proof/request.json
manifests/ec2_runtime_proof/model_hydration_manifest.json
manifests/ec2_runtime_proof/workflow_list.json
manifests/ec2_runtime_proof/dry_run_commands.txt
manifests/ec2_runtime_proof/expected_outputs.json
```

## Start/stop guard

The AI system must never call EC2 start directly from generic code. It must use a guarded script.

Required confirmation token:

```text
START_EC2_RUNTIME_PROOF
```

If the token is absent, the script must exit before any live EC2 command.

## Cost containment checklist

Before every EC2 session:

```text
[ ] Local QA passed.
[ ] Model hydration is exact and minimal.
[ ] No full S3 sync of all models.
[ ] Output folder is predeclared.
[ ] Stop command is prepared.
[ ] CloudWatch/log capture is enabled if available.
[ ] Runtime proof has max-duration expectation.
[ ] Failure still stops instance.
```
