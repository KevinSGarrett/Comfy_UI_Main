# Next Action

Complete the AWS CLI remote browser login in an interactive/browser-capable shell, then rerun the secret-safe auth gate:

```powershell
aws login --remote
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1 -AttemptRemoteLogin -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_AUTH_GATE_<timestamp>.json
```

Expected account: `029530099913`.

Do not start EC2 unless the auth gate reports:

```text
ec2_work_allowed: true
safe_to_start_ec2: true
```

After AWS auth is refreshed and verified, rerun the EC2 static proof for `sdxl_low_risk_fallback_lane`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json
```

Only proceed to EC2 static proof when the readiness record reports:

```text
local_pre_ec2_ready: true
ready_for_ec2_static_proof: true
```

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json
```

- update `/home/ubuntu/Comfy_UI_Main` to `origin/main`
- query ComfyUI `/object_info` and confirm `CheckpointLoaderSimple`, `EmptyLatentImage`, `CLIPTextEncode`, `KSampler`, `VAEDecode`, and `SaveImage`
- resolve `/home/ubuntu/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`
- record file size and sha256
- stop EC2 and verify `stopped`

Only after that proof exists, run the bounded ComfyUI smoke request and perform image QA.

Smoke helper command shape after proof exists and ComfyUI API is reachable:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-ComfyWorkflowSmoke.ps1 -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_COMFY_WORKFLOW_SMOKE_EXECUTION_<timestamp>.json
```

After the generated image and runtime logs are pulled back locally, create the local pullback record:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json
```

Then route the pulled-back image to image QA:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md
```
