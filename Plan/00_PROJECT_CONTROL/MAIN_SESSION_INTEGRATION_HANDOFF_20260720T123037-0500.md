# Main Session Integration Handoff — ComfyUI :8188 GPU serialize blocker

Updated: 2026-07-20T12:30:37-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: probe local ComfyUI `:8188` for highest-value real generation/proof
- Landing commit: `059ec8ad`
- Result: **blocked** — `:8188` DOWN; GPU not free (Masking gold tournament + SAM2); safe start script dry-run only; no Execute
- No COMPLETE / Status flip. CSV deferred to mutator.
- Row073 PID 27320 left alone.
- Note: `MAIN_SESSION_INTEGRATION_HANDOFF_20260720T1230-0500.md` was later reused by a concurrent post-073 ranking landing (`8c2ce364`); this uniquely stamped handoff preserves the :8188 probe evidence chain.

## This pass proof

- Blocker packet: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_LOCAL_COMFYUI_8188_HEALTH_GPU_SERIALIZE_BLOCKER_20260720T123037-0500.json`
- Blocker SHA256: `1c4fba8ce3c98ce7ed9dd20212b000e7846cfec60f34f6e9aad3ced6f5c2fcb9`
- Start dry-run: `runtime_artifacts/run_manifests/LOCAL_COMFY_DEV_START_DRYRUN_20260720T1228-0500.json`
- Dry-run SHA256: `5e8b02cf580fb902d6655ebf72eb24e5c6e583b1955e73f5430d534ab46ea6ae`
- Generation executed: **false**
- ComfyUI started: **false**

## Exclusive ownership

- Row073 full-library index-retained PCM (PID 27320) — do not kill/contend/restart this shift
- Foreign GPU: Masking `run_multiprovider_gold_tournament.py` + `run_sam2_server_wsl.py` — serialize; do not steal

## Exact next action

1. Wait until Masking GPU owners clear; then `Start-LocalComfyUIDev.ps1 -Execute -LowVram` and climb deferred prepared visual/character proof.
2. Leave Row073 alone; CSV via mutator only.
3. Do not thrash settled HOLD Rows084-089 or invent human media for Row010/109.
