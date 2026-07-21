# Main Session Integration Handoff — 2026-07-20T22:44-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: RunPod `1q4ji0gg1fkhvt` mechanical smoke **PASS** (evidence-only landing)
- Agent subagent `663aa2a1` (parent transcript `485c50f8`) — all five SSH checks PASS; **no restart**
- No COMPLETE / CSV mutation / local ComfyUI / Row073 PCM touch / HOLD 090+

## RunPod mechanical smoke (agent-reported)

| # | Check | Verdict |
|---|--------|---------|
| 1 | `paths.env` | **PASS** — `WAVE64_ROOT=/workspace/wave64`, `COMFYUI_ROOT=/workspace/ComfyUI`, `SCENES_ROOT=/workspace/Characters/Scenes_xxx_001`, `COMFY_URL=http://127.0.0.1:8188` |
| 2 | ComfyUI `/system_stats` + `/queue` | **PASS** — v0.28.0; queue empty |
| 3 | `Plan` + `PromptProfiles` | **PASS** — dirs present under `$WAVE64_ROOT` |
| 4 | `Runtime_Data/models` symlink | **PASS** → `/workspace/ComfyUI/models` |
| 5 | `df /workspace` + `nvidia-smi -L` | **PASS** — ~129T avail (74% used); 1× RTX 6000 Ada |

**Restart action:** none

## This pass proof

- Evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/RUNPOD_1q4ji0gg1fkhvt_MECHANICAL_SMOKE_PASS_20260720T2244-0500.json`
- Evidence SHA256: `0144FF7DAD52058E021F29CD4FDF69DAA02506CEBEF29BF44D5C7D98747D033D`
- Proof tier: `MECHANICAL_SMOKE_PASS_BOUNDED`
- Runtime authority: RunPod remote; local git authority remains `C:\Comfy_UI_Main`

## Boundaries honored

- No local ComfyUI / :8188 start / Row073 PCM / shared CSV / COMPLETE / workspace wipe / bulk re-upload

## Exact next action

1. Route GPU-bound Wave64 generation/QA to RunPod `1q4ji0gg1fkhvt` via SSH tunnel to loopback `:8188`.
2. Leave Row073 alone; CSV via mutator only.
