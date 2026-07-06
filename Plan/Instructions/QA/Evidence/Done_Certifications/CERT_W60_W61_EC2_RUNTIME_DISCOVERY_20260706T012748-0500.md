# Done Certification: Wave 60/61 EC2 Runtime Discovery

- certification_id: CERT-W60-W61-EC2-RUNTIME-DISCOVERY-20260706T012748-0500
- timestamp: 2026-07-06T01:46:30-05:00
- task_tracker_id: TRK-W60-002
- related_tracker_id: TRK-W60-003; TRK-W61-006; TRK-W61-007
- title: Bounded EC2 runtime discovery with stop verification
- certifier: Codex Desktop autonomous release manager
- final_decision: done_with_project_sync_required

## Artifact Scope

- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T012748-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Discovery/W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.json`

## Implementation Summary

Started the verified EC2 instance only for bounded runtime discovery. SSM was online. The retry discovery command succeeded, found GPU support and a ComfyUI runtime at `/home/ubuntu/ComfyUI`, found no `Comfy_UI_Main` project checkout in searched remote paths, then stopped the instance and verified final state `stopped`.

## Tests Performed

- Verified EC2 could start from `stopped`.
- Waited for running/status-ok.
- Verified SSM Online.
- Ran SSM Run Command discovery.
- Checked GPU via `nvidia-smi`.
- Searched likely project and ComfyUI paths.
- Stopped EC2.
- Verified final state `stopped`.

## QA Summary

- EC2 start: pass.
- SSM availability: pass.
- SSM discovery command: pass on retry.
- GPU discovery: pass, NVIDIA A10G.
- ComfyUI path discovery: pass, `/home/ubuntu/ComfyUI`.
- Project checkout discovery: blocked, no `Comfy_UI_Main` path found.
- Stop verification: pass.

## Evidence Paths

- `Plan/Instructions/Operations/Run_Records/aws_gpu_run_20260706T012748-0500.json`
- `Plan/Instructions/QA/Evidence/EC2_Runtime_Discovery/W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.json`
- `Plan/Instructions/Waves/Wave60/WAVE60_TRACKER_SUPPLEMENT.csv`
- `Plan/Instructions/Waves/Wave61/WAVE61_TRACKER_SUPPLEMENT.csv`

## Known Issues

- `BLOCKER-EC2-PROJECT-SYNC-001`: EC2 has ComfyUI at `/home/ubuntu/ComfyUI`, but the `Comfy_UI_Main` project checkout was not found in searched paths.

## Runtime Note

This certification does not claim project sync, workflow execution, model download, generated artifact QA, or final project completion.
