# Main Session Integration Handoff — 20260721T000852-0500

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY**. Never EC2. Never local Comfy.
- Live probe pod `1q4ji0gg1fkhvt` hostname `82caae576b8a`: Wan TI2V **0/3 ABSENT**.
- Approved on-pod Wan fetch script: **NONE FOUND** under `tools/` (CSV mutators only).
- Tip evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-019_023_RUNPOD_WAN_TI2V_NO_APPROVED_FETCH_SCRIPT_BLOCKER_20260721T000852-0500.json`
- Evidence sha256: `e771cee999ad58e556c26a6fea028f7da75f34e1fb831abcad19eb4b5ffbfa9a`
- `row_complete=false`; no COMPLETE; Row074 untouched; EC2 untouched; no HF download.

## Blocker (exact paths needed)

1. Script (missing): `tools/Fetch-RunPodWan22Ti2V5B.ps1` (orchestrator) and optionally `/workspace/tools/fetch_wan22_ti2v_5b_on_pod.sh` (on-pod fetch).
2. HF URLs (reference; do not auto-download until script approved):
   - `https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/fb1388adc906ab39ffc26ee40e96b22886b56bc4/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors`
   - `https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/fb1388adc906ab39ffc26ee40e96b22886b56bc4/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors`
   - `https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/fb1388adc906ab39ffc26ee40e96b22886b56bc4/split_files/vae/wan2.2_vae.safetensors`
3. Install targets: `/workspace/ComfyUI/models/{diffusion_models,text_encoders,vae}/` with sha256 bind.

## Exact next action

1. Approve/land `tools/Fetch-RunPodWan22Ti2V5B.ps1` for pod-direct HF fetch + hash-verify (zero EC2).
2. Execute bounded fetch ON THE POD only; keep Class F until 3/3 hash-bound.
3. Leave Row074 alone. Do not start EC2. Do not claim COMPLETE.
