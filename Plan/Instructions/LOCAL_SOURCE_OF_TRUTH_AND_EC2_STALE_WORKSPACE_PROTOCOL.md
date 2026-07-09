# Local Source Of Truth And EC2 Stale Workspace Protocol

Updated: 2026-07-09

This protocol prevents duplicate ComfyUI runtime work caused by stale project copies on the GPU EC2 host.

## Authority

The authoritative execution ledger is the local workspace:

```text
C:\Comfy_UI_Main
```

The EC2 workspace is runtime/cache state only:

```text
/home/ubuntu/Comfy_UI_Main
```

Do not use the EC2 copy of `Comfy_UI_Main` as the authority for current Items, Tracker, hydration, runtime-lane queue state, selected next action, or completed-work status. EC2 files may be used only as runtime evidence, pulled-back artifact source, model/input cache inspection, or troubleshooting context.

## Verified Boundary

On 2026-07-09, inspection of approved GPU instance `i-0560bf8d143f93bb1` found:

- the instance was started for inspection and stopped again;
- ComfyUI auto-started on boot but was idle;
- `queue_running=[]`, `queue_pending=[]`, and current history count was `0`;
- no generation was launched during the inspection;
- the latest relevant EC2 runtime artifacts were from 2026-07-07;
- EC2 `/home/ubuntu/Comfy_UI_Main` still had an older three-lane queue where Canny could appear queued;
- local `C:\Comfy_UI_Main` had newer 2026-07-09 selected-inpaint readiness/handoff evidence and the current nine-lane queue.

Therefore, the EC2 copy is stale for planning purposes. It must not resurrect completed Canny/base/fallback work.

## No-Rerun Rule

Before local runtime work, EC2 work, S3 publish, artifact pullback, QA rerun, Jira coordination, or Items/Tracker mutation, check the local ledger first:

```text
C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json
C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence
C:\Comfy_UI_Main\Plan\Tracker\Evidence
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration
```

Do not rerun work that local evidence already marks complete for the scoped gate. Completed EC2/local work that must not be repeated as new work includes:

- `sdxl_low_risk_fallback_lane` first runtime proof;
- `sdxl_realvisxl_base_lane` RealVisXL base smoke/proof and prior certification sample runs;
- `sdxl_realvisxl_controlnet_canny_lane` baseline/Canny v4 target-runtime smoke proof;
- 2026-07-09 local package smoke and visual QA matrix evidence for active base-generation lanes.

## Still-Open Work

The following selected-inpaint path work is not duplicate when it is intentionally selected and all live gates pass:

- clean deploy-bundle rebuild/revalidation from local source;
- selected S3 publish proof for deploy bundle, input assets, and model assets;
- EC2 install/hash proof for selected input/model assets;
- selected inpaint target-runtime proof;
- final certification.

## Required Classifications

Use these classifications in hydration, evidence, cron audits, and main-session steering:

- `LOCAL_SOURCE_OF_TRUTH_ACTIVE`
- `EC2_WORKSPACE_STALE_NOT_AUTHORITY`
- `NO_RERUN_COMPLETED_EC2_PROOF`
- `SELECTED_INPAINT_TARGET_RUNTIME_NOT_DUPLICATE`
- `BLOCKED_EC2_STALE_QUEUE_SOURCE`

## Cron And Main Session Rule

Scheduled cron jobs and main-session agents must treat local `C:\Comfy_UI_Main` as source of truth and must not steer from stale EC2 queue state. If EC2 and local disagree, write a blocker or warning using `EC2_WORKSPACE_STALE_NOT_AUTHORITY`, then continue from local hydration and local runtime-lane queue.

EC2 may be started only for explicitly authorized inspection or live-gated runtime work, and it must be stopped after inspection or after the bounded runtime window closes.
