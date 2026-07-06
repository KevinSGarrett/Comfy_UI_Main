# Wave 34 QA Certification Model

QA certification assembles all pass/fail evidence.

## Certification domains
- schema validity
- registry validity
- App Mode mapping
- orchestrator route completeness
- model/asset compatibility
- preview QA
- state diff
- image QA
- video temporal QA
- audio sync QA
- spatial audio QA
- local proof
- EC2 proof
- release manifest completeness

## Certification statuses
- certified
- certified_with_runtime_boundaries
- repair_required
- blocked_missing_proof
- blocked_failed_QA

## Rule
Certification cannot overwrite missing runtime proof.
