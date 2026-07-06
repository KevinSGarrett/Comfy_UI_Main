# Wave 34 Final Integration Release Architecture

Wave 34 assembles every prior wave into a final release framework.

## Final integration layers
1. App Mode control surface
2. Scene Director / orchestrator
3. workflow compiler
4. engine router
5. local preview/proof runner
6. EC2 runtime runner
7. manifest collector
8. QA certification gates
9. release decision engine
10. final handoff packet

## Release principle
The release system is evidence-first. No UI surface, workflow route, render lane, or final output can be certified from plans alone.

## Required release objects
- app_mode_release_contract
- orchestrator_release_plan
- local_proof_report
- ec2_proof_report
- qa_certification_packet
- release_manifest
- final_handoff_packet
- release_gate_decision
