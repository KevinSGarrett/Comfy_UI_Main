# Wave 34 Local and EC2 Proof Gate Model

## Local proof
Local proof validates:
- schemas
- registries
- App Mode control mapping
- preview plans
- manifests
- basic file decode
- QA report structure
- proof-gate readiness

## EC2 proof
EC2 proof validates:
- model hydration
- dependency availability
- ComfyUI startup
- exact workflow execution
- runtime outputs
- output manifests
- run logs
- shutdown/stop evidence

## Boundary
Local proof can prepare a release. EC2 proof is required before claiming runtime execution for EC2-rendered outputs.
