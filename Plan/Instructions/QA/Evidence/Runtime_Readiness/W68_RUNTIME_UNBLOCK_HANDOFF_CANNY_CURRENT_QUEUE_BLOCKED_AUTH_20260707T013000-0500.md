# Runtime Unblock Handoff

- created_at: 2026-07-06T23:11:16-05:00
- result: handoff_ready_runtime_blocked_auth
- failure_category: expired_session
- next_required_action: complete_aws_browser_sso_login
- lane: sdxl_realvisxl_controlnet_canny_lane
- local_only: true
- aws_contacted: false
- ec2_started: false
- generation_executed: false

## Current Gate Summary

- Auth gate: blocked_expired_session, safe_to_start_ec2=False, account_match=False, failure_category=expired_session
- Profile matrix: blocked_no_valid_profile, matching profiles=0, expected account=029530099913
- Lane readiness: local_pre_ec2_ready_runtime_blocked_auth, lane_id=sdxl_realvisxl_controlnet_canny_lane, lane_match=True, local_pre_ec2_ready=True, ready_for_ec2_static_proof=False, ready_for_generation=False
- Project readiness: pass_local_ready_runtime_blocked, lane_id=sdxl_realvisxl_controlnet_canny_lane, lane_match=True, local_ready=True, ec2_start_allowed=False, generation_allowed=False, scan_hit_count=0
- Runtime lane queue: pass_local_only, first_runtime_lane_id=sdxl_low_risk_fallback_lane, current_runtime_lane_id=sdxl_realvisxl_controlnet_canny_lane, current_runtime_lane_match=True, selected_lane_order=3, queue_allows_selected_lane_ec2_static_proof=True
- Model registry coverage: pass_local_only, selected_lane_covered=True, selected_lane_result=pass, failed_check_count=0, coverage_allows_selected_lane_ec2_static_proof=True
- Workflow smoke: missing_workflow_smoke, run_id=, complete=False, final_state=, local_pullback_status=
- Pullback record: missing_pullback_record, hashes_verified=False, complete=False, file_count_remote=, file_count_local=
- Image QA technical: missing_image_technical_qa, technical_integrity=, resolution_check=, complete=False
- Image QA visual: missing_image_visual_qa, qa_score=, pass_threshold=, complete=False
- Run package: supplied=True, valid=True, run_id=sdxl_realvisxl_controlnet_canny_lane_static_package_v1, profile=, prompt_hash_match=True

## Safety Invariants

- Start only EC2 instance `i-0560bf8d143f93bb1`.
- Expected AWS account is `029530099913`.
- Do not start EC2 unless auth gate reports `ec2_work_allowed=true` and `safe_to_start_ec2=true`.
- Do not start EC2 unless runtime lane queue validation reports `current_runtime_lane_id=sdxl_realvisxl_controlnet_canny_lane`, selected lane in queue, and failed check count `0`.
- Do not start EC2 unless model registry coverage reports `result=pass_local_only`, selected lane `sdxl_realvisxl_controlnet_canny_lane` result `pass`, and failed check count `0`.
- Do not start EC2 unless local Git is clean and `HEAD` equals `origin/main`.
- Do not run EC2 static proof unless lane readiness reports `lane_id=sdxl_realvisxl_controlnet_canny_lane` and `ready_for_ec2_static_proof=true`.
- Do not run generation until object-info, checkpoint path, and checkpoint hash proof exists.
- Stop EC2 after runtime work and verify final state `stopped`.
- If workflow smoke, pullback hashes, technical image QA, and visual image QA are complete for this lane, do not rerun EC2 for the same smoke proof; checkpoint evidence and advance.

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
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W63_RUNTIME_LANE_QUEUE_VALIDATION_<timestamp>.json
```

Expected evidence: result=pass_local_only, current_runtime_lane_id=sdxl_realvisxl_controlnet_canny_lane, selected lane in queue, failed_check_count=0.

### model_registry_coverage_recheck

Gate: before_any_ec2_execute

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_<timestamp>.json
```

Expected evidence: result=pass_local_only, selected lane sdxl_realvisxl_controlnet_canny_lane has result=pass, failed_check_count=0, registry records and runtime-validation queue rows exist.

### local_comfyui_dev_preflight

Gate: before_optional_local_iteration

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_controlnet_canny_lane -LocalComfyRoot <path-to-local-ComfyUI>
```

Expected evidence: Local dev candidate status recorded without claiming EC2 equivalence.

### deploy_bundle_build

Gate: before_ec2_sync_or_execute

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_controlnet_canny_lane -RunPackageManifestFile <run-package-manifest>
```

Expected evidence: DEPLOY_BUNDLE_MANIFEST.json and bundle zip created while EC2 is stopped.

### deploy_bundle_s3_publish

Gate: before_ec2_sync_or_execute

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix>
```

Expected evidence: s3_bundle_uri and bundle_zip_sha256 recorded before EC2 starts.

### git_checkpoint_recheck

Gate: before_any_ec2_execute

```powershell
git -C C:\Comfy_UI_Main status --short --branch; git -C C:\Comfy_UI_Main rev-parse HEAD; git -C C:\Comfy_UI_Main rev-parse origin/main
```

Expected evidence: Working tree clean and local HEAD equals origin/main before any EC2 helper runs with -Execute.

### emergency_stop_schedule

Gate: before_any_ec2_execute

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -SchedulerRoleArn arn:aws:iam::<account-id>:role/<scheduler-stop-role> -StopAfterMinutes 60 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_EMERGENCY_STOP_SCHEDULE_<timestamp>.json
```

Expected evidence: One-time EventBridge Scheduler stop created or explicit missing-role blocker recorded.

### realvisxl_model_s3_install

Gate: before_realvisxl_static_proof

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1 -SourceS3Uri s3://<bucket>/<model-cache-prefix>/realvisxlV50_v50Bakedvae.safetensors -ExpectedSha256 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80 -MaxEc2RuntimeMinutes 20 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W63_EC2_REALVISXL_MODEL_INSTALL_<timestamp>.json
```

Expected evidence: result=install_model_hash_verified, final_state=stopped, generation_executed=false.

### lane_readiness_recheck

Gate: auth_gate_safe_to_start_ec2_true

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -LaneId sdxl_realvisxl_controlnet_canny_lane -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Expected evidence: local_pre_ec2_ready=true, lane_id=sdxl_realvisxl_controlnet_canny_lane, and ready_for_ec2_static_proof=true before EC2 static proof.

### ec2_static_proof

Gate: ready_for_ec2_static_proof_true

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_controlnet_canny_lane -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
```

Expected evidence: Object-info node availability, checkpoint path, checkpoint size/hash, LaneId match, S3 bundle hash verification when supplied, and EC2 stop verification.

### bounded_workflow_smoke

Gate: static_proof_generation_allowed

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId sdxl_realvisxl_controlnet_canny_lane -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 45 -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -RunPackageManifestFile "C:\Comfy_UI_Main\runtime_artifacts\run_packages\sdxl_realvisxl_controlnet_canny_lane_static_package_v1\RUN_PACKAGE_MANIFEST.json" -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json
```

Expected evidence: Bounded prompt execution from validated run package sdxl_realvisxl_controlnet_canny_lane_static_package_v1, LaneId-matched static proof/readiness, S3 deploy bundle preference, remote artifact manifest, pullback route, and EC2 stop verification.

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
