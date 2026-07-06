# Wave 34 Local and EC2 Proof Runbook

## Local proof
Run local proof first:
- validate schemas
- compile manifests
- decode sample artifacts where available
- confirm release block policy
- confirm App Mode mapping

## EC2 proof
Run EC2 only after local proof and final preflight pass:
- start EC2 worker
- hydrate exact models/assets
- run ComfyUI workflow
- export runtime output evidence
- collect logs/manifests
- stop EC2 worker
- run QA certification

## Stop rule
If preflight does not unlock EC2, do not start EC2.
