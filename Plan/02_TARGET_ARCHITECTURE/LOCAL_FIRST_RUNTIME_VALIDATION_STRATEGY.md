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

## Machine-readable contract

The canonical Row005 contract is:

`Plan/10_REGISTRIES/local_first_runtime_validation_contract.json`

It defines four independently testable gates:

1. `local_preflight` proves static validation, local-only scope, and zero failed checks before any live action.
2. `low_vram_policy` requires a bounded localhost command, `--lowvram`, no execution during dry-run validation, and no external contact.
3. `ec2_final_proof_boundary` keeps EC2 stopped unless a target-runtime fact cannot be established locally and all live gates pass.
4. `no_false_equivalence` prohibits local preflight, local object-info, local smoke, or local visual QA from being relabeled as target-runtime proof, lane certification, release certification, or full-project completion.

## Evidence equivalence matrix

| Evidence scope | May prove | Must not prove by itself |
|---|---|---|
| Local static preflight | Parseability, graph/schema checks, model references, local prerequisites | Model loading, generation, visual quality, target-runtime behavior |
| Local object-info | Local node visibility and API compatibility | EC2 node/path/model parity or target-runtime readiness |
| Local low-VRAM smoke | Bounded local execution for the exact workflow/input/model scope | EC2 proof, broader robustness, lane promotion, final quality |
| Local visual QA | Quality of the exact local artifact reviewed | Changed seeds, inputs, workflows, models, target runtime, or full portfolio |
| Target-runtime proof | Exact remote model/input/workflow execution and pullback scope | Broader lane, wave, release, or project completion without their gates |

## Low-VRAM execution policy

- Bind local development to `127.0.0.1` and a recorded port.
- Use `--lowvram` when the selected local GPU memory policy requires it.
- Record the exact command, GPU identity, total memory, execute flag, process ID, and external-contact flags.
- A dry run may validate command construction only; it is not runtime proof.
- A local generation must retain exact workflow, input, model, output, and QA hashes and remains local-scope evidence.
- Local failure blocks the dependent lane step. It does not justify starting EC2 to bypass a known static defect.

## EC2 final-proof boundary

EC2 remains an on-demand target-runtime worker, not a substitute for failed local validation and not a planning authority. Starting it requires an explicit selected scope plus current Git, authentication, budget, TTL, emergency-stop, input, model, workflow, pullback, and stopped-state controls. Local evidence may reduce EC2 starts; it never silently eliminates a required target-runtime gate.
