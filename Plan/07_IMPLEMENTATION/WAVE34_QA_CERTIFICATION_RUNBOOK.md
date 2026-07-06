# Wave 34 QA Certification Runbook

## Certification assembly
Collect:
- release manifest
- source manifest
- App Mode manifest
- orchestrator manifest
- preview QA
- state diff report
- local proof report
- EC2 proof report, if EC2 was used
- image/video/audio QA reports
- release gate decision

## Certification rule
A missing required proof file blocks runtime certification. It does not block the architecture release pack, but it must be disclosed in the decision status.
