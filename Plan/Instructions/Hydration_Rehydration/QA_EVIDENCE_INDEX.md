# QA Evidence Index

## Current packaging evidence

| Evidence ID | Artifact | Type | Result | Path |
|---|---|---|---|---|
| EVID-W62-PACKAGE-VALIDATION | Wave 58-62 cumulative pack | package_validation | pass | Plan/Instructions/Reports/WAVE62_VALIDATION_REPORT.json |
| EVID-W62-FINAL-CERT | Wave 58-62 final certification | certification | pass | Plan/Instructions/Hydration_Rehydration/WAVE58_62_FINAL_COMPLETION_CERTIFICATION.md |
| EVID-W59-LIVE-INDEX-REGEN-20260706T003608-0500 | Wave 59 live local directory/index regeneration | live_local_index_validation | pass_with_notes | Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json |
| CERT-W59-LIVE-INDEX-VALIDATION-20260706T003608-0500 | Wave 59 live local index validation certification | done_certification | done_with_non_blocking_notes | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_VALIDATION_20260706T003608-0500.md |
| EVID-W59-W60-GIT-LOCAL-VERIFICATION-20260706T004200-0500 | Wave 59/60 local Git verification and secret guard check | git_local_verification | blocked | Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_LOCAL_VERIFICATION_20260706T004200-0500.json |
| EVID-W59-W60-GIT-RECOVERY-INITIAL-COMMIT-20260706T010603-0500 | Wave 59/60 Git recovery, initial commit, LFS setup, and push verification | git_recovery_initial_commit_and_push | pass | Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_INITIAL_COMMIT_20260706T010603-0500.json |
| EVID-W59-W60-GIT-RECOVERY-EVIDENCE-COMMIT-VERIFICATION-20260706T011016-0500 | Wave 59/60 Git recovery evidence/tracker commit remote verification | git_recovery_evidence_commit_verification | pass | Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_EVIDENCE_COMMIT_VERIFICATION_20260706T011016-0500.json |
| EVID-W60-OPERATIONS-STATIC-VALIDATION-20260706T004632-0500 | Wave 60 operations helper scripts/schemas/templates local validation | operations_static_validation | pass_with_notes | Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.json |
| CERT-W60-OPERATIONS-STATIC-VALIDATION-20260706T004632-0500 | Wave 60 operations static validation certification | done_certification | done_with_non_blocking_notes | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.md |
| EVID-W61-QA-HELPER-STATIC-VALIDATION-20260706T005111-0500 | Wave 61 QA helper scripts/schemas/templates local validation | qa_helper_static_validation | pass_with_notes | Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_STATIC_VALIDATION_20260706T005111-0500.json |
| CERT-W61-QA-HELPER-STATIC-VALIDATION-20260706T005111-0500 | Wave 61 QA helper static validation certification | done_certification | done_with_non_blocking_notes | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_STATIC_VALIDATION_20260706T005111-0500.md |
| EVID-W62-HYDRATION-HELPER-STATIC-VALIDATION-20260706T005425-0500 | Wave 62 hydration helper scripts/templates local validation | hydration_helper_static_validation | pass_with_pending_validation | Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_STATIC_VALIDATION_20260706T005425-0500.json |
| CERT-W62-SESSION-STATE-HELPER-VALIDATION-20260706T005425-0500 | Wave 62 session-state helper validation certification | done_certification | done_with_non_blocking_notes | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_SESSION_STATE_HELPER_VALIDATION_20260706T005425-0500.md |
| EVID-W62-CUMULATIVE-PACK-VALIDATION-20260706T011548-0500 | Wave 62 cumulative Wave 58-62 pack build and validation | cumulative_pack_validation | pass | Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.json |
| CERT-W62-CUMULATIVE-PACK-VALIDATION-20260706T011548-0500 | Wave 62 cumulative pack validation certification | done_certification | done_with_non_blocking_runtime_notes | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.md |
| EVID-W60-W61-RUNTIME-READINESS-PREFLIGHT-20260706T012301-0500 | Secret-safe GitHub AWS EC2 Civitai and local ComfyUI readiness preflight | runtime_readiness_preflight | pass_with_local_runtime_blocker | Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json |
| CERT-W60-W61-RUNTIME-READINESS-PREFLIGHT-20260706T012301-0500 | Wave 60/61 runtime readiness preflight certification | done_certification | done_with_local_runtime_blocker | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.md |
| EVID-W60-W61-EC2-RUNTIME-DISCOVERY-20260706T012748-0500 | Bounded EC2 runtime discovery with SSM GPU ComfyUI path and stop verification | ec2_runtime_discovery | pass_with_project_sync_required | Plan/Instructions/QA/Evidence/EC2_Runtime_Discovery/W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.json |
| CERT-W60-W61-EC2-RUNTIME-DISCOVERY-20260706T012748-0500 | Wave 60/61 EC2 runtime discovery certification | done_certification | done_with_project_sync_required | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.md |
| EVID-W60-W61-EC2-PROJECT-SYNC-20260706T015022-0500 | Bounded EC2 project checkout sync with Git LFS verification and stop verification | ec2_project_sync | pass | Plan/Instructions/QA/Evidence/EC2_Project_Sync/W60_W61_EC2_PROJECT_SYNC_20260706T015022-0500.json |
| CERT-W60-W61-EC2-PROJECT-SYNC-20260706T015022-0500 | Wave 60/61 EC2 project sync certification | done_certification | done_with_runtime_inventory_pending | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_PROJECT_SYNC_20260706T015022-0500.md |
| EVID-W60-W61-EC2-RUNTIME-INVENTORY-20260706T020209-0500 | Bounded EC2 ComfyUI model and workflow prerequisite inventory | ec2_runtime_inventory | pass | Plan/Instructions/QA/Evidence/EC2_Runtime_Inventory/W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.json |
| CERT-W60-W61-EC2-RUNTIME-INVENTORY-20260706T020209-0500 | Wave 60/61 EC2 runtime inventory certification | done_certification | done_with_workflow_execution_pending | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_EC2_RUNTIME_INVENTORY_20260706T020209-0500.md |
| EVID-W61-WORKFLOW-LANE-SELECTION-20260706T024025-0500 | SDXL low-risk workflow lane selection and executable graph authoring | workflow_prerequisite_matching | selected_and_authored_pending_ec2_validation | Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.json |
| CERT-W61-WORKFLOW-LANE-SELECTION-20260706T024025-0500 | Wave 61 workflow lane selection pending runtime validation certification | done_certification | pending_runtime_validation | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_WORKFLOW_LANE_SELECTION_20260706T024025-0500.md |
| LOCAL-COMFY-WORKFLOW-STATIC-20260706T024811-0500 | SDXL low-risk workflow local static graph validation | workflow_static_validation | pass | Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.json |
| EC2-LANE-STATIC-PROOF-DRY-RUN-20260706T024846-0500 | EC2 lane static-proof helper dry-run plan | ec2_lane_static_proof_dry_run | pass_no_start | Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_DRY_RUN_20260706T024845-0500.json |
| CERT-W61-SDXL-LOW-RISK-WORKFLOW-STATIC-VALIDATION-20260706T024811-0500 | SDXL low-risk workflow static validation certification | done_certification | pending_runtime_validation | Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.md |

## Pending runtime evidence

- GitHub API-specific token evidence, if required separately from pushed Git remote evidence
- AWS/EC2 static lane proof after AWS login refresh
- Civitai API evidence
- ComfyUI workflow test evidence
- Image review evidence
- Video review evidence
- Audio review evidence
