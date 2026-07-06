# Done Certification - W60 AWS Auth Gate Contract Hardening

## Certification ID

CERT-W60-AWS-AUTH-GATE-CONTRACT-HARDENING-20260706T050352-0500

## Scope

Local-first hardening of AWS auth/readiness evidence shape. This work makes `Test-AwsAuthGate.ps1` emit top-level summary fields and teaches `Test-OperationsHelperStatic.ps1` to validate those fields without starting EC2.

## Files changed

- `Plan/Instructions/Operations/Scripts/Test-AwsAuthGate.ps1`
- `Plan/Instructions/Operations/Scripts/Test-OperationsHelperStatic.ps1`

## Evidence

- Auth gate evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_AUTH_GATE_CONTRACT_20260706T050233-0500.json`
- Profile matrix evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_AWS_PROFILE_AUTH_MATRIX_CONTRACT_20260706T050233-0500.json`
- Lane readiness evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W61_LANE_RUNTIME_READINESS_CONTRACT_20260706T050233-0500.json`
- First validation failure evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_AUTH_CONTRACT_20260706T050233-0500.json`
- Retest validation evidence: `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_HELPER_CURRENT_VALIDATION_AUTH_CONTRACT_RETEST_20260706T050327-0500.json`

## Validation result

- Auth gate top-level `result`: `blocked_expired_session`
- Auth gate top-level `failure_category`: `expired_session`
- Auth gate top-level `account_match`: false
- Auth gate top-level `remote_login_status`: `not_attempted`
- Profile count checked: 15
- Profiles matching expected account `029530099913`: 0
- Lane `local_pre_ec2_ready`: true
- Lane `ready_for_ec2_static_proof`: false
- Lane `ready_for_generation`: false

## Operations retest

- Result: `pass_local_only`
- Operation scripts parsed: 15
- Script parse failures: 0
- Operation JSON schemas/templates parsed: 5
- JSON parse failures: 0
- Local smoke checks: 8
- Local smoke failures: 0
- Auth evidence contract checks: 1
- Auth evidence contract failures: 0

## Retest note

The first operations validation failed because the new auth-contract check referenced `Has-Property` before that helper was defined in `Test-OperationsHelperStatic.ps1`. The retest evidence proves the helper was added and the auth-contract validation now passes.

## Certification decision

This local evidence-contract hardening is certified as passed. It does not refresh AWS auth and does not permit EC2 start.

## Runtime boundary

No EC2 instance was started. No ComfyUI runtime generation occurred. No generated image/video/audio QA is claimed by this certification.

