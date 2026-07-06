# Wave 07 Director / Orchestrator / Engine Router Boundary

## Three separate responsibilities

## 1. Scene Director

The Scene Director answers:

- What is the user asking for?
- What should the scene contain?
- What camera/framing is required?
- What masks are needed?
- What model families and passes are likely needed?
- What QA must be checked?

The Director outputs a plan.

## 2. Orchestrator / Workflow Compiler

The orchestrator answers:

- Which workflow template/subgraph should be used?
- How should the ComfyUI API JSON be patched?
- Which assets must be hydrated?
- Which outputs should be collected?
- Which pass runs next?

The orchestrator executes the plan, but still does not decide promotion by itself.

## 3. Engine Router

The engine router answers:

- Is this engine valid for this pass?
- Are these models compatible with the engine?
- Is a cross-engine bridge allowed?
- Is this model proof-gated or production-ready?
- Is this asset rejected/superseded/disabled?

The router enforces compatibility.

## Boundary table

| Decision | Scene Director | Orchestrator | Engine Router | QA Gate |
|---|---:|---:|---:|---:|
| Interpret user request | yes | no | no | no |
| Create scene graph | yes | no | no | no |
| Create pass plan | yes | yes, compile only | validate | no |
| Select candidate models | yes | hydrate only | validate/allow/block | verify output |
| Patch workflow JSON | no | yes | no | no |
| Start EC2 | no | yes, only when proof required | no | no |
| Run ComfyUI | no | yes | no | no |
| Judge output | no | no | no | yes |
| Promote output | no | no | no | yes |

## Required failure behavior

If the Director creates a plan with an invalid engine/model combination, the router must block it.

If the orchestrator cannot find a workflow module, it must block execution.

If runtime outputs are missing, QA must block promotion.

If a Scene Director plan is underspecified but usable, it should proceed with assumptions. If it is truly blocked, the plan should contain `blocking_questions[]` and status `blocked`.
