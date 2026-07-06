# Wave 34 Release Gate Decision Engine

The release gate decision engine combines all proof states.

## Inputs
- App Mode release status
- orchestrator release status
- preview QA
- final render preflight
- local proof
- EC2 proof
- QA certification
- release manifest completeness
- unresolved failures

## Output decisions
- release_architecture_pack
- release_runtime_certified
- release_with_runtime_boundaries
- repair_required
- blocked_missing_proof
- blocked_failed_QA

## Rule
If any required runtime proof is missing, the release decision must say so directly.
