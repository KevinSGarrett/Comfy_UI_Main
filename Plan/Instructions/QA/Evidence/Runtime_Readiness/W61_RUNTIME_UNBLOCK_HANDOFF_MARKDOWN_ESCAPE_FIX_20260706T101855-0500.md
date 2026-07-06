# Runtime Unblock Handoff

- created_at: 2026-07-06T10:18:55-05:00
- result: handoff_ready_runtime_blocked_auth
- failure_category: expired_session
- next_required_action: complete_aws_browser_sso_login
- lane: sdxl_low_risk_fallback_lane
- local_only: true
- aws_contacted: false
- ec2_started: false
- generation_executed: false

## Current Gate Summary

- Auth gate: blocked_expired_session, safe_to_start_ec2=False, account_match=False, failure_category=expired_session
- Profile matrix: blocked_no_valid_profile, matching profiles=0, expected account=029530099913
- Lane readiness: local_pre_ec2_ready_runtime_blocked_auth, lane_id=sdxl_low_risk_fallback_lane, lane_match=True, local_pre_ec2_ready=True, ready_for_ec2_static_proof=False, ready_for_generation=False
- Project readiness: pass_local_ready_runtime_blocked_auth, lane_id=sdxl_low_risk_fallback_lane, lane_match=True, local_ready=True, ec2_start_allowed=False, generation_allowed=False, scan_hit_count=0
- Runtime lane queue: pass_local_only, first_runtime_lane_id=sdxl_low_risk_fallback_lane, first_runtime_lane_match=True, selected_lane_order=1, queue_allows_selected_lane_ec2_static_proof=True
- Model registry coverage: pass_local_only, selected_lane_covered=True, selected_lane_result=pass, failed_check_count=0, coverage_allows_selected_lane_ec2_static_proof=True
- Run package: supplied=True, valid=True, run_id=sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1, profile=hyperreal_editorial_portrait_v1, prompt_hash_match=True

## Safety Invariants

- Start only EC2 instance `i-0560bf8d143f93bb1`.
- Expected AWS account is `029530099913`.
- Do not start EC2 unless auth gate reports `ec2_work_allowed=true` and `safe_to_start_ec2=true`.
- Do not start EC2 unless runtime lane queue validation reports `first_runtime_lane_id=sdxl_low_risk_fallback_lane`, selected lane order `1`, and failed check count `0`.
- Do not start EC2 unless model registry coverage reports `result=pass_local_only`, selected lane `sdxl_low_risk_fallback_lane` result `pass`, and failed check count `0`.
- Do not start EC2 unless local Git is clean and `HEAD` equals `origin/main`.
- Do not run EC2 static proof unless lane readiness reports `lane_id=sdxl_low_risk_fallback_lane` and `ready_for_ec2_static_proof=true`.
- Do not run generation until object-info, checkpoint path, and checkpoint hash proof exists.
- Stop EC2 after runtime work and verify final state `stopped`.

## Command Sequence

### aws_browser_sso_login

Gate: external_interactive_browser_required

```powershell
aws login --remote
```

Expected evidence: AWS CLI login refreshed for account 029530099913

### auth_gate_recheck

Gate: after_aws_login

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1 -AttemptRemoteLogin -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_AUTH_GATE_<timestamp>.json
```

Expected evidence: result=pass, ec2_work_allowed=true, safe_to_start_ec2=true, account_match=true

### profile_matrix_recheck

Gate: after_auth_gate_or_for_diagnosis

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsProfileAuthMatrix.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_PROFILE_AUTH_MATRIX_<timestamp>.json
```

Expected evidence: At least one profile authenticates to account 029530099913, or a clear diagnostic if not.

### runtime_lane_queue_recheck

Gate: before_any_ec2_execute

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W61_RUNTIME_LANE_QUEUE_VALIDATION_<timestamp>.json
```

Expected evidence: result=pass_local_only, first_runtime_lane_id=sdxl_low_risk_fallback_lane, selected lane order=1, failed_check_count=0.

### model_registry_coverage_recheck

Gate: before_any_ec2_execute

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_<timestamp>.json
```

Expected evidence: result=pass_local_only, selected lane sdxl_low_risk_fallback_lane has result=pass, failed_check_count=0, registry records and runtime-validation queue rows exist.

### git_checkpoint_recheck

Gate: before_any_ec2_execute

```powershell
git -C C:\Comfy_UI_Main status --short --branch; git -C C:\Comfy_UI_Main rev-parse HEAD; git -C C:\Comfy_UI_Main rev-parse origin/main
```

Expected evidence: Working tree clean and local HEAD equals origin/main before any EC2 helper runs with -Execute.

### lane_readiness_recheck

Gate: auth_gate_safe_to_start_ec2_true

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -LaneId sdxl_low_risk_fallback_lane -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Expected evidence: local_pre_ec2_ready=true, lane_id=sdxl_low_risk_fallback_lane, and ready_for_ec2_static_proof=true before EC2 static proof.

### ec2_static_proof

Gate: ready_for_ec2_static_proof_true

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
```

Expected evidence: Object-info node availability, checkpoint path, checkpoint size/hash, LaneId match, and EC2 stop verification.

### bounded_workflow_smoke

Gate: static_proof_generation_allowed

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_low_risk_fallback_lane -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -RunPackageManifestFile "C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json" -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
```

Expected evidence: Bounded prompt execution from validated run package sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1, LaneId-matched static proof/readiness, remote artifact manifest, pullback route, and EC2 stop verification.

### artifact_pullback_record

Gate: generated_artifacts_pulled_back

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json
```

Expected evidence: PULLBACK_RECORD.json with count/hash match and QA routing.

### image_artifact_qa

Gate: pullback_hashes_verified

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```

Expected evidence: Image technical QA record and human/visual review checklist.

## Runtime Boundary

This handoff was generated from local evidence only. It did not contact AWS, GitHub APIs, Civitai, ComfyUI, or EC2.
