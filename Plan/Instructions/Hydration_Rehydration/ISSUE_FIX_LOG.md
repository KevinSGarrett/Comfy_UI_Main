# Issue / Fix Log

## ISSUE-W59-INDEX-001

- date_time: 2026-07-06T00:36:08-05:00
- severity: medium
- category: local_file_system
- affected_tracker_id: TRK-W59-002; TRK-W59-003
- affected_item_id: W59-002; W59-003; W59-004; W59-005; W59-006
- affected_files: Plan/Instructions/Scripts/Generate-Project-Indexes.ps1
- observed_behavior: The live index generator failed on Windows PowerShell because `[System.IO.Path]::GetRelativePath` was unavailable.
- expected_behavior: The generator should run on the documented `powershell -ExecutionPolicy Bypass -File ...` command and produce Plan, Items, Tracker, and Instructions CSV/JSON indexes.
- suspected_root_cause: The script used a .NET API available in newer runtimes but not in Windows PowerShell 5.1.
- fix_attempted: Added `Get-RelativePathCompat`, using `System.Uri.MakeRelativeUri`, and replaced the unsupported call.
- retest_result: retest_passed
- current_status: fixed
- evidence_path: Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json
- next_action: Continue local validation using regenerated live index artifacts.

## ISSUE-W59-GIT-001

- date_time: 2026-07-06T00:42:00-05:00
- severity: high
- category: github
- affected_tracker_id: TRK-W59-004; TRK-W60-001; TRK-W60-009
- affected_item_id: W59-007; W60-001; W60-009
- affected_files: C:\Comfy_UI_Main\.git; C:\Comfy_UI_Main\.gitignore; C:\Comfy_UI_Main\.env.example
- observed_behavior: `C:\Comfy_UI_Main` is not a Git repository, so Git root, branch, HEAD, remote, and working tree state cannot be verified there. `.env` exists, while `.gitignore` and `.env.example` were initially absent.
- expected_behavior: `C:\Comfy_UI_Main` should be the local Git root for `https://github.com/KevinSGarrett/Comfy_UI_Main`, with `.env` untracked and secret/binary protections present.
- suspected_root_cause: The Wave 58-62 pack appears extracted into `C:\Comfy_UI_Main` without repository metadata.
- fix_attempted: Created `.gitignore` and `.env.example`, initialized Git metadata, configured canonical origin, enabled LFS, committed, pushed `main`, and verified remote HEAD.
- retest_result: retest_passed
- current_status: fixed
- evidence_path: Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_INITIAL_COMMIT_20260706T010603-0500.json; Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_EVIDENCE_COMMIT_VERIFICATION_20260706T011016-0500.json
- next_action: Continue runtime readiness validation without exposing `.env` secrets.

## ISSUE-W60-OPS-001

- date_time: 2026-07-06T00:46:32-05:00
- severity: low
- category: local_file_system
- affected_tracker_id: TRK-W60-010
- affected_item_id: W60-010; W60-011
- affected_files: Plan/Instructions/Operations/Scripts/New-ModelRegistryRecord.ps1
- observed_behavior: Initial smoke execution using direct invocation was blocked by PowerShell execution policy because the script is unsigned.
- expected_behavior: Local smoke validation should run using the documented `powershell -ExecutionPolicy Bypass -File ...` pattern.
- suspected_root_cause: Wrapper used direct script invocation instead of the project-documented bypass pattern.
- fix_attempted: Reran the smoke test with `powershell -ExecutionPolicy Bypass -File`.
- retest_result: retest_passed
- current_status: fixed
- evidence_path: Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.json
- next_action: Keep using explicit execution-policy bypass for intended local PowerShell script smoke tests.

## ISSUE-W62-ZIP-001

- date_time: 2026-07-06T00:54:25-05:00
- severity: medium
- category: local_file_system
- affected_tracker_id: TRK-W62-009
- affected_item_id: ITEM-W62-009
- affected_files: C:\Comfy_UI_Main\*.zip
- observed_behavior: No cumulative zip file was found under `C:\Comfy_UI_Main`, so `Test-CumulativeWavePack.ps1` could not be run against a real pack.
- expected_behavior: A cumulative pack zip should exist when cumulative-pack validation is selected.
- suspected_root_cause: The extracted project contains Plan files but not the final cumulative zip artifact.
- fix_attempted: Built `Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip` from tracked project files with private-path exclusion and Git LFS coverage.
- retest_result: retest_passed
- current_status: fixed
- evidence_path: Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.json
- next_action: Continue runtime readiness validation.

## ISSUE-RUNTIME-COMFYUI-LOCAL-001

- date_time: 2026-07-06T01:23:01-05:00
- severity: high
- category: runtime_environment
- affected_tracker_id: TRK-W60-008; TRK-W61-006; TRK-W61-007
- affected_item_id: W60-008; ITEM-W61-006; ITEM-W61-007
- affected_files: C:\Comfy_UI_Main\ComfyUI
- observed_behavior: The local checkout has workflow templates but no local `ComfyUI` runtime directory, no expected local model folders, and no local model binaries.
- expected_behavior: Runtime workflow execution needs either a local ComfyUI runtime with required models or a verified EC2 runtime path.
- suspected_root_cause: The local project currently contains the plan/instruction pack and registries, not the ComfyUI runtime tree or model storage.
- fix_attempted: None locally; AWS account, EC2 identity, EC2 stopped state, EBS volume, and Civitai metadata readiness were validated.
- retest_result: preflight_passed_with_local_runtime_blocker
- current_status: active_runtime_blocker
- evidence_path: Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json
- next_action: Use bounded EC2 project sync because EC2 discovery found `/home/ubuntu/ComfyUI`.

## ISSUE-EC2-PROJECT-SYNC-001

- date_time: 2026-07-06T01:46:30-05:00
- severity: high
- category: runtime_environment
- affected_tracker_id: TRK-W60-003; TRK-W61-006
- affected_item_id: W60-003; ITEM-W61-006
- affected_files: /home/ubuntu/ComfyUI; /home/ubuntu/Comfy_UI_Main
- observed_behavior: Bounded EC2 discovery found `/home/ubuntu/ComfyUI` and NVIDIA A10G GPU readiness, but no `Comfy_UI_Main` project checkout in searched paths.
- expected_behavior: EC2 runtime validation needs the project checkout available so workflows, registries, QA protocols, and tracker state match the pushed local `main`.
- suspected_root_cause: The EC2 image has ComfyUI installed independently of the project repository.
- fix_attempted: None yet; EC2 was stopped after discovery.
- retest_result: discovery_passed_project_missing
- current_status: active_runtime_blocker
- evidence_path: Plan/Instructions/QA/Evidence/EC2_Runtime_Discovery/W60_W61_EC2_RUNTIME_DISCOVERY_20260706T012748-0500.json
- next_action: Start EC2 only for bounded project sync, clone or update `Comfy_UI_Main`, verify Git state, then stop EC2.
