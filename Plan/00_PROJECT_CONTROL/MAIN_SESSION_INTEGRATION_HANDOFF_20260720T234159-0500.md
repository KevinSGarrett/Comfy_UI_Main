# Main Session Integration Handoff — 2026-07-20T23:41-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: TRK-W64-019/023 **Class F reaffirm** — Wan TI2V **3/3 ABSENT** local + pod + S3
- Historical EC2: `i-0560bf8d143f93bb1` `rw-wan22-install2-20260713T233137` **3/3 ASSET_PRESENT_OK** (Jul 13 install window)
- Live EC2 verify: command `24ef6be4-2ba3-4673-a387-34d2c0986ffe` status **Success** ratio **3/3 ASSET_PRESENT_OK**
- Tip evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-019_023_LOCAL_POD_S3_EC2_WAN_TI2V_RECOVERY_INVENTORY_20260720T234159-0500.json`
- Tip SHA256: `162C21D78CEC449FB98F04B1013D77C21A2DA72B1DB89567A44B5D891E9F404D`
- Local: **3/3 ABSENT**; Pod: **3/3 ABSENT**; S3: **3/3 ABSENT**
- `row_complete=false`; Class F retained; no HF scrape; no copy/scp this pass; no COMPLETE; Row074 untouched; CSV deferred

## Exact next action

1. Bounded copy EC2-verified payloads (3/3 live SHA OK) to `Runtime_Data/staging/wan_ti2v/models/` with hash bind.
2. Bounded scp staging → pod `/workspace/ComfyUI/models/{diffusion_models,text_encoders,vae}/`.
3. Keep Class F until 3/3 hash-bound on pod; leave Row074 alone; CSV via mutator only; no COMPLETE.
