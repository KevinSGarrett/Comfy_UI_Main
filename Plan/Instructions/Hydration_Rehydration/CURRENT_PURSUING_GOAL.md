# Current Pursuing Goal

## Active Wave
Wave 63 EC2 cost-control and local/CI preflight packaging, continuing Wave 61 runtime proof for queued lanes.

## Goal Statement
Advance `C:\Comfy_UI_Main` toward end-to-end autonomous ComfyUI completion by using `Plan/Instructions` as the operating system, avoiding repeated housekeeping, minimizing paid EC2 time, and moving from the completed first-lane runtime proof to the next concrete queued runtime work.

## Required Instruction Read Order
Every continuation must use `C:\Comfy_UI_Main` as the project root and must read these project instructions before changing code, evidence, trackers, runtime helpers, or goals:

1. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md`
2. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\SESSION_START_REHYDRATION_CHECKLIST.md`
3. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md`
4. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md`
5. `C:\Comfy_UI_Main\Plan\Instructions\NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md`
6. `C:\Comfy_UI_Main\Plan\Instructions\Operations\EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md`
7. `C:\Comfy_UI_Main\Plan\Instructions\AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
8. `C:\Comfy_UI_Main\Plan\Instructions\Operations\README_OPERATIONS_WAVE60.md`
9. `C:\Comfy_UI_Main\Plan\Instructions\QA\README_QA_WAVE61.md`
10. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\TRACKER_UPDATE_PROTOCOL.md`
11. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\ITEMIZED_LIST_UPDATE_PROTOCOL.md`
12. `C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_LOG_PROTOCOL.md`
13. `C:\Comfy_UI_Main\Plan\Instructions\Waves\Wave63\WAVE63_SCOPE.md`

Do not replace this read order with a short autonomous goal. The pursuing goal is only the active objective pointer; detailed operating rules live in `Plan/Instructions`.

## How To Use The Instruction Files
Before acting, reconcile the newest acceptable evidence across the instruction files:

- Prefer current passing evidence with the newest timestamp over older failed blockers when the newer evidence directly supersedes it.
- Treat `BLOCKER-W59-GIT-001` as superseded for `C:\Comfy_UI_Main`; this root has a valid `.git`, canonical `origin`, and pushed `main`.
- Treat `C:\Comfy_UI` as historical/source context and a possible local development ComfyUI environment, not the active Plan-bearing project root.
- Treat Wave42/Main Flow analysis, registries, release records, and snapshots under `Plan` as source/staging context. The active runtime surface is `C:\Comfy_UI_Main\Workflows\base_generation`, with concrete API lanes only.
- If top summaries conflict with newer lower sections or evidence files, fix the summary instead of repeating old work.
- Use generated indexes to find files, but do not refresh indexes repeatedly unless files changed in the current turn.
- When evidence commits advance `HEAD`, rerun the Git checkpoint gate immediately before any EC2 `-Execute` path.
- Read `EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md` before any AWS/EC2 decision. If local or CI validation can advance the work while EC2 is stopped, do that first.

## Current Status
The first queued runtime lane, `sdxl_low_risk_fallback_lane`, completed target EC2 static proof, one bounded package-fed workflow smoke generation, SSM pullback, technical image QA, and visual QA with runtime-smoke notes. Do not repeat that lane just to re-prove the same path.

The next queued runtime lane is `sdxl_realvisxl_base_lane`. It is locally authored and static-valid, but it still needs target EC2 object-info, RealVisXL checkpoint path/hash/load proof, generation, pullback, and image QA before it can be treated as runtime-proven.

Wave 63 cost controls are active:

- Local dev preflight: `tools\Test-LocalComfyUIDevPreflight.ps1`.
- Deploy bundle builder: `tools\New-EC2DeployBundle.ps1`.
- GitHub Actions preflight/package workflow: `.github\workflows\preflight-package.yml`.
- EC2 helpers now support `-SkipGitLfsPull` and `-MaxEc2RuntimeMinutes`.
- EC2 should be used only for target-runtime facts, not for package/build/index housekeeping.

## Last Verified Facts
The current root is `C:\Comfy_UI_Main`. `.env` is ignored, GitHub/Civitai variable names are present without printing values, and model binaries/private keys/generated media must not be committed.

Current proof evidence for the first lane includes:

```text
Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_POST_LOGIN_RETEST_20260706T104311-0500.json
Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_POST_STATIC_PROOF_RETEST_20260706T110424-0500.json
Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500/PULLBACK_RECORD.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_TECHNICAL_20260706T121958-0500.json
Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_VISUAL_20260706T122027-0500.json
```

S3 pullback was blocked by missing EC2 role permissions and SSH/SCP timed out, so SSM chunk pullback is the known working fallback. EC2 final state was verified `stopped`.

## Next Exact Work
First, if the runtime proof, cost-control, tracker, or instruction updates are uncommitted, finish one clean Git checkpoint and verify local `HEAD == origin/main`.

Second, use the cost-control lane before any EC2 start:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -AllowNonFirstLane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_base_lane -RunPackageManifestFile <realvisxl-run-package-manifest>
```

Third, after AWS auth and Git gates pass, use one bounded EC2 window for the next target-runtime proof. Default to `-SkipGitLfsPull` unless the selected lane explicitly requires repository LFS payloads:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId sdxl_realvisxl_base_lane -Execute -SkipGitLfsPull -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W63_EC2_LANE_STATIC_PROOF_REALVISXL_<timestamp>.json
```

Only after RealVisXL static proof passes, run its package-fed workflow smoke with `-SkipGitLfsPull`, `-MaxEc2RuntimeMinutes`, pullback, and image QA.

## Hard Stop And No-Loop Rules
If AWS auth is expired, Git is not clean/pushed, or the selected lane is not ready, do not start EC2. Record the blocker once and switch only to a concrete local/CI task that changes runtime capability.

Allowed local/CI tasks while EC2 is stopped:

- Improve a lane, prompt profile, model registry record, run package, deploy bundle, or QA rule.
- Run local ComfyUI dev checks/previews without claiming EC2 equivalence.
- Run GitHub Actions preflight/package and inspect the artifact.
- Fix a real stale/conflicting instruction that would misroute the autonomous session.

Disallowed loop work:

- Repeating first-lane proof without a changed lane/package/prompt/QA objective.
- Rebuilding indexes or handoffs repeatedly with the same result.
- Running Git LFS pulls on the EC2 clock unless a lane explicitly needs them.
- Updating this pursuing goal in a way that omits the required `Plan/Instructions` read order.

## Update Protocol
When this file is autonomously updated, preserve these sections and keep the required instruction read order. Updates should change only current status, last verified facts, next exact work, and hard blockers. Do not compress this file back into a short goal that omits `Plan/Instructions`.
